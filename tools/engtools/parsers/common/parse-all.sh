#!/bin/bash

#Copyright (c) 2016-2017 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#

# This script is used to parse all stats data. It is designed to be called by either
# parse-controllers.sh or parse-computes.sh and not used as a standalone script.
# If the input node is a controller, it will parse controller specific postgres &
# and rabbitmq stats first. If the input node is a compute, it will pars the compute
# specific vswitch stats first.
#
# The following parsing steps are common to all hosts and are executed in the specified order:
#     - Parse occtop
#     - Parse memtop
#     - Parse memstats (summary)
#     - Parse netstats
#     - Parse schedtop (summary)
#     - Parse iostats
#     - Parse diskstats
#     - Parse filestats (summary)
#     - Parse process level schedtop (optional step, configured in lab.conf)
#     - Generate tarball

if [[ $# != 1 ]]; then
    echo "ERROR: This script is meant to be called by either parse-controllers.sh or parse-computes.sh script."
    echo "To run it separately, copy the script to the host directory that contains *.bz2 files."
    echo "It takes a single argument - the name of the host directory (e.g. ./parse-all.sh controller-0)."
    exit 1
fi

source ../lab.conf
source ./host.conf

PARSERDIR=$(dirname $0)
. ${PARSERDIR}/parse-util.sh

NODE=$1

CURDATE=$(date)
DATESTAMP=$(date +%b-%d)

function sedit()
{
    local FILETOSED=$1
    sed -i -e "s/  */ /g" ${FILETOSED}
    sed -i -e "s/ /,/g" ${FILETOSED}
    # Remove any trailing comma
    sed -i "s/,$//" ${FILETOSED}
}

function get_filename_from_mountname()
{
    local name=$1
    local fname
    if test "${name#*"scratch"}" != "${name}"; then
        fname="scratch"
    elif test "${name#*"log"}" != "${name}"; then
        fname="log"
    elif test "${name#*"backup"}" != "${name}"; then
        fname="backup"
    elif test "${name#*"ceph/mon"}" != "${name}"; then
        fname="cephmon"
    elif test "${name#*"conversion"}" != "${name}"; then
        fname="img-conversion"
    elif test "${name#*"platform"}" != "${name}"; then
        fname="platform"
    elif test "${name#*"postgres"}" != "${name}"; then
        fname="postgres"
    elif test "${name#*"cgcs"}" != "${name}"; then
        fname="cgcs"
    elif test "${name#*"rabbitmq"}" != "${name}"; then
        fname="rabbitmq"
    elif test "${name#*"instances"}" != "${name}"; then
        fname="pv"
    elif test "${name#*"ceph/osd"}" != "${name}"; then
        # The ceph disk partition has the following mount name convention
        # /var/lib/ceph/osd/ceph-0
        fname=`basename ${name}`
    fi
    echo $fname
}

function parse_process_schedtop_data()
{
    # Logic has been moved to a separate script so that parsing process level schedtop
    # can be run either as part of parse-all.sh script or independently.
    LOG "Process level schedtop parsing is turned on in lab.conf. Parsing schedtop detail..."
    cd ..
    ./parse-schedtop.sh ${NODE}
    cd ${NODE}
}

function parse_controller_specific()
{
    # Parsing Postgres data, removing data from previous run if there are any. Generate summary
    # data for each database and detail data for specified tables
    LOG "Parsing postgres data for ${NODE}"
    if [ -z "${DATABASE_LIST}" ]; then
        WARNLOG "DATABASE_LIST is not set in the lab.conf file. Use default setting"
        DATABASE_LIST="cinder glance keystone nova neutron ceilometer heat sysinv aodh postgres nova_api"
    fi

    for DB in ${DATABASE_LIST}; do
        rm /tmp/${DB}*.csv
    done
    ../parse_postgres *postgres.bz2 >postgres-summary-${NODE}-${DATESTAMP}.txt
    for DB in ${DATABASE_LIST}; do
        cp /tmp/${DB}_size.csv postgres_${DB}_size.csv
    done
    for TABLE in ${TABLE_LIST}; do
        cp /tmp/${TABLE}.csv postgres_${TABLE}.csv
    done

    # Parsing RabbitMQ data
    LOG "Parsing rabbitmq data for ${NODE}"
    ../parse-rabbitmq.sh rabbitmq-${NODE}.csv

    for QUEUE in ${RABBITMQ_QUEUE_LIST}; do
        # If node is not a controller node then parse-rabbitmq-queue.sh should skip
        ../parse-rabbitmq-queue.sh rabbitmq-${QUEUE}-${NODE}.csv ${QUEUE}
    done
}

function parse_compute_specific()
{
    LOG "Parsing vswitch data for ${NODE}"
    ../parse-vswitch.sh ${NODE}
}

function parse_occtop_data()
{
    LOG "Parsing occtop data for ${NODE}"
    bzcat *occtop.bz2 >occtop-${NODE}-${DATESTAMP}.txt
    cp occtop-${NODE}-${DATESTAMP}.txt tmp.txt
    sedit tmp.txt
    # Get the highest column count
    column_count=$(awk -F "," '{print NF}' tmp.txt | sort -nu | tail -n 1)
    grep '^[0-9]' tmp.txt |cut -d, -f1,2 | awk -F "," '{print $1" "$2}' > tmpdate.txt
    grep '^[0-9]' tmp.txt |cut -d, -f3-$column_count > tmpcore.txt
    paste -d, tmpdate.txt tmpcore.txt > tmp2.txt
    # Generate header based on the number of columns. The Date/Time column consists of date and time fields
    header="Date/Time,Total"
    count=$(($column_count-3))
    for i in $(seq 0 $(($count-1))); do
        header="$header,$i"
    done

    # Generate detailed CSV with Date/Time, Total CPU occupancy and individual core occupancies e.g.
    # Date/Time,Total,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35
    # 2016-11-22 00:29:16.523,759.5,21.4,18.9,43.8,24.5,23.1,25.3,28.1,25.5,20.5,27.8,26.8,32.7,27.3,25.1,21.1,23.2,21.7,36.4,23.3,16.6,15.3,13.9,14.4,15.0,14.7,14.4,16.4,13.8,17.0,17.8,19.0,15.1,14.0,13.2,14.5,17.8
    echo "${header}" > occtop-${NODE}-detailed.csv
    cat tmp2.txt >> occtop-${NODE}-detailed.csv

    # Generate simple CSV file which is used to generate host CPU occupancy chart. Platform cores are
    # defined in the host.conf. The simple CSV contains only the Date/Time and Total platform CPU occupancy e.g.
    # Date/Time,Total
    # 2016-11-22 00:29:16.523,94.9
    # 2016-11-22 00:30:16.526,71.3

    if [ -z "${PLATFORM_CPU_LIST}" ]; then
        # A controller node in standard system. In this case, all cores are dedicated to platform use.
        # Simply extract the Date/Time and Total CPU occupancy
        cut -d, -f1,2 occtop-${NODE}-detailed.csv > occtop-${NODE}.csv
    else
        # A CPE, compute or storage node. The cores dedicated to platform use are specified in the config.
        echo "Date/Time,Total" > occtop-${NODE}.csv
        while read -r line || [[ -n "$line" ]]; do
            IFS="," read -r -a arr <<< "${line}"
            total=0
            for CORE in ${PLATFORM_CPU_LIST}; do
                # Add 2 to the index as occupancy of each individual core starts after Date/Time and Total
                idx=$(($CORE+2))
                total=`echo $total + ${arr[$idx]} | bc`
            done
            echo "${arr[0]},${total}" >> occtop-${NODE}.csv
        done < tmp2.txt
    fi
    # Remove temporary files
    rm tmp.txt tmp2.txt tmpdate.txt tmpcore.txt
}

function parse_memtop_data()
{
    LOG "Parsing memtop data for ${NODE}"
    bzcat *memtop.bz2 > memtop-${NODE}-${DATESTAMP}.txt
    cp memtop-${NODE}-${DATESTAMP}.txt tmp.txt
    sedit tmp.txt

    # After dumping all memtop bz2 output into one text file and in-place sed, grab only relevant data
    # for CSV output. Generate both detailed and simple CSV files. Simple output will be used to generate
    # chart.
    grep '^[0-9]' tmp.txt | awk -F "," '{print $1" "$2","$3","$4","$5","$6","$7","$8","$9","$10","$11","$12","$13","$14","$15","$16","$17","$18}' > tmp2.txt
    echo "Date/Time,Total,Used,Free,Cached,Buf,Slab,CAS,CLim,Dirty,WBack,Anon,Avail,0:Avail,0:HFree,1:Avail,1:HFree" > memtop-${NODE}-detailed.csv
    cat tmp2.txt >> memtop-${NODE}-detailed.csv
    echo "Date/Time,Total,Anon" > memtop-${NODE}.csv
    cut -d, -f1-2,12 tmp2.txt >> memtop-${NODE}.csv
    # Remove temporary files
    rm tmp.txt tmp2.txt
}

function parse_netstats_data()
{
    LOG "Parsing netstats data for ${NODE}"
    # First generate the summary data then detail data for specified interfaces
    ../parse_netstats *netstats.bz2 > netstats-summary-${NODE}-${DATESTAMP}.txt
    if [ -z "${NETSTATS_INTERFACE_LIST}" ]; then
        ERRLOG "NETSTATS_INTERFACE_LIST is not set in host.conf. Skipping detail netstats..."
    else
        for INTERFACE in ${NETSTATS_INTERFACE_LIST}; do
            echo "Date/Time,Interface,Rx PPS,Rx Mbps,Rx Packet Size,Tx PPS,Tx Mbps,Tx Packet Size" > netstats-${NODE}-${INTERFACE}.csv
            ../parse_netstats *netstats.bz2 | grep " ${INTERFACE} " > tmp.txt
            sed -i -e "s/|/ /g" tmp.txt
            sed -i -e "s/    */ /g;s/  */ /g" tmp.txt
            sed -i -e "s/ /,/g" tmp.txt
            # Remove the leading comma
            sed -i 's/,//' tmp.txt
            while read -r line || [[ -n "$line" ]]; do
                IFS="," read -r -a arr <<< "${line}"
                echo "${arr[8]} ${arr[9]},${arr[0]},${arr[2]},${arr[3]},${arr[4]},${arr[5]},${arr[6]},${arr[7]}" >> netstats-${NODE}-${INTERFACE}.csv
            done < tmp.txt
        done
        rm tmp.txt
    fi
}

function parse_iostats_data()
{
    LOG "Parsing iostat data for ${NODE}"
    if [ -z "${IOSTATS_DEVICE_LIST}" ]; then
        ERRLOG "IOSTAT_DEVICE_LIST is not set in host.conf. Skipping iostats..."
    else
        for DEVICE in ${IOSTATS_DEVICE_LIST}; do
            # Add header to output csv file
            echo "Date/Time,${DEVICE},rqm/s,wrqm/s,r/s,w/s,rkB/s,wkB/s,avgrq-sz,avgqu-sz,await,r_await,w_await,svctm,%util" > iostat-${NODE}-${DEVICE}.csv
            # Dumping iostat content to tmp file
            bzcat *iostat.bz2 | grep -E "/2015|/2016|/2017|${DEVICE}"   | awk '{print $1","$2","$3","$4","$5","$6","$7","$8","$9","$10","$11","$12","$13","$14}' > tmp.txt
            while IFS= read -r current
            do
                if test "${current#*Linux}" != "$current"
                then
           # Skip the line that contains the word "Linux"
                    continue
                else
                    if test "${current#*$DEVICE}" == "$current"
                    then
                        # It's a date entry, look ahead
                        read -r next
                        if test "${next#*$DEVICE}" != "${next}"
                        then
                            # This next line contains the device stats
                            # Combine date and time fields
                            current="${current//2016,/2016 }"
                            current="${current//2017,/2017 }"
                            # Combine time and AM/PM fields
                            current="${current//,AM/ AM}"
                            current="${current//,PM/ PM}"
                            # Write both lines to intermediate file
                            echo "${current}" >> tmp2.txt
                            echo "${next}" >> tmp2.txt
                        fi
                    fi
                fi
            done < tmp.txt
            mv tmp2.txt tmp.txt
            # Combine the time and stats data into one line
            # 11/22/2016 06:34:00 AM,,,,,,,,,,,
            # dm-0,0.00,0.00,0.00,1.07,0.00,38.00,71.25,0.00,0.19,0.00,0.19,0.03,0.00
            paste -d "" - - < tmp.txt > tmp2.txt
            # Remove empty fields, use "complement" option for contiguous fields/range
            cut -d, -f2-11 --complement tmp2.txt > tmp.txt
            # Write final content to output csv
            cat tmp.txt >> iostat-${NODE}-${DEVICE}.csv
        rm tmp.txt tmp2.txt
        done
    fi
}

function parse_diskstats_data()
{
    LOG "Parsing diskstats data for ${NODE}"

    if [ -z "${DISKSTATS_FILESYSTEM_LIST}" ]; then
        ERRLOG "DISKSTATS_FILESYSTEM_LIST is not set in host.conf. Skipping diskstats..."
    else
        for FS in ${DISKSTATS_FILESYSTEM_LIST}; do
            fspair=(${FS//|/ })
            fsname=${fspair[0]}
            mountname=${fspair[1]}
            if [ ${mountname} == "/" ]; then
                mountname=" /"
                echo "File system,Type,Size,Used,Avail,Used(%)" > diskstats-${NODE}-root.csv
                bzcat *diskstats.bz2 | grep $fsname | grep $mountname | grep G | awk '{print $1","$2","$3","$4","$5","$6}' >> diskstats-${NODE}-root.csv
            else
                fname=$(get_filename_from_mountname $mountname)
                echo "File system,Type,Size,Used,Avail,Used(%)" > diskstats-${NODE}-$fname.csv
                bzcat *diskstats.bz2 | grep $fsname | grep $mountname | grep G | awk '{print $1","$2","$3","$4","$5","$6}' >> diskstats-${NODE}-$fname.csv
            fi
        done
    fi
}

# Parsing starts here ...
LOG "Parsing ${NODE} files - ${CURDATE}"

# Let's get the host specific parsing out of the way
if test "${NODE#*"controller"}" != "${NODE}"; then
    parse_controller_specific
elif test "${NODE#*"compute"}" != "${NODE}"; then
    parse_compute_specific
fi

# Parsing CPU occtop data
parse_occtop_data

# Parsing memtop data
parse_memtop_data

# Parsing memstats data to generate the high level report. The most important piece of info is the list of
# hi-runners at the end of the file. If there is a leak, run parse-daily.sh script to generate the time
# series data for the offending processes only. Use process name, not PID as most Titanium Cloud processes have
# workers.
LOG "Parsing memstats summary for ${NODE}"
../parse_memstats --report *memstats.bz2 > memstats-summary-${NODE}-${DATESTAMP}.txt
#tar czf pidstats.tgz pid-*.csv
rm pid-*.csv


# Parsing netstats data
parse_netstats_data

# Parsing schedtop data to generate the high level report. Leave the process level schedtop parsing till
# the end as it is a long running task.
LOG "Parsing schedtop summary for ${NODE}"
FILES=$(ls *schedtop.bz2)
../parse_schedtop ${FILES} > schedtop-summary-${NODE}-${DATESTAMP}.txt

# Parsing iostats data
parse_iostats_data

# Parsing diskstats data
parse_diskstats_data

# Parsing filestats data to generate the high level report. If there is a file descriptor leak, run parse-daily.sh
# script to generate the time series data for the offending processes only. Use process name, not PID as most
# Titanium Cloud processes have workers.
LOG "Parsing filestats summary for ${NODE}"
../parse_filestats --all *filestats.bz2 > filestats-summary-${NODE}-${DATESTAMP}.txt

# Parsing process level schedtop data. This is a long running task. To skip this step or generate data for
# only specific processes, update the lab.conf and host.conf files.
[[ ${GENERATE_PROCESS_SCHEDTOP} == Y ]] && parse_process_schedtop_data || WARNLOG "Parsing process level schedtop is skipped."

# Done parsing for this host. If it's a controller host, check if the parsing of postgres connection stats which is run in
# parallel is done before creating a tar file.
if test "${NODE#*"controller"}" != "${NODE}"; then
    # If postgres-conns.csv file has not been created which is highly unlikely, wait a couple of minutes
    [ ! -e postgres-conns.csv ] && sleep 120

    # Now check the stats of this file every 5 seconds to see if it's still being updated. Another option
    # is to use inotify which requires another inotify-tools package.
    oldsize=0
    newsize=0
    while true
    do
        newsize=$(stat -c %s postgres-conns.csv)
        if [ "$oldsize" == "$newsize" ]; then
            break
        fi
        oldsize=$newsize
        sleep 5
    done
fi
tar czf syseng-data-${NODE}-${DATESTAMP}.tgz *.csv *.txt
LOG "Parsing stats data for ${NODE} completed!"
