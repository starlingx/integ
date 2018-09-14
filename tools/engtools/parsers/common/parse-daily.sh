#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
# The following script is used when either memstats or filestats summary reports
# a possible memory or file leak respectively. It can be run for a particular host or
# for all hosts as configured in the lab.conf.
# Make sure to run cleanup-uncompressed.sh script before running this script to remove
# any uncompressed files as memstats/filestats parser can produce erronous result if
# there are both uncompressed and compressed version of the same file.
#
# Usage:
# ./parse-daily.sh <parser-name> <process-name> to generate daily stats for all hosts
# ./parse-daily.sh <host-name> <parser-name> <process-name> to generate daily stats for
# specified host.
#
# e.g. >./parse-daily.sh memstats sm-eru
#      >./parse-daily.sh controller-0 filestats postgress

function print_usage {
    echo "Usage: ./parse-daily.sh <parser-name> <process-name> will parse daily data for all hosts."
    echo "Usage: ./parse-daily.sh <host-name> <parser-name> <process-name> will parse daily data for specified host."
    echo "Valid parsers for daily stats are: memstats & filestats."
    exit 1
}

function parse_daily_stats {
    local PARSER_NAME=$1
    local PROCESS_NAME=$2
    local TMPFILE="tmp.txt"
    # Inserting the header in the summary csv file. The summary file is a concatenation
    # of the daily file. If there is a large number of files, the parser may not have
    # enough memory to process them all. The safest way is to parse one day at a time.
    if [ ${PARSER_NAME} == "memstats" ]; then
        local SUMMARYFILE=memstats-summary-${PROCESS_NAME}.csv
        echo "Date,RSS,VSZ" > ${SUMMARYFILE}
    else
        local SUMMARYFILE=filestats-summary-${PROCESS_NAME}.csv
        echo "Date,Read/Write,Write,Read" > ${SUMMARYFILE}
    fi
    # Get the list of dates for memstats/filestats bz2 files in this directory.
    # The filename convention is : <hostname>_YYYY-MM-DD_<time>_memstats.bz2
    # e.g. storage-0_2016-11-23_1211_memstats.bz2
    DATE_LIST=$(ls -1|awk -F "_" '{print $2}'| grep 20|uniq)
    for DATE in ${DATE_LIST}; do
        local YEAR=$(echo ${DATE}|awk -F "-" '{print $1}')
        if [ ${PARSER_NAME} == "memstats" ]; then
            local DAILYFILE=memstats-${PROCESS_NAME}-${DATE}.csv
            ../parse_memstats --name ${DATE} --cmd ${PROCESS_NAME} --detail > ${TMPFILE}
            # Time series data for memstats would look something like this
            #       DATE     TIME    AVAIL    SLAB  | NLWP      RSS      VSZ
            # 2016-11-18 00:42:50 123735.29 4831.39 |    2   602208  1292348
            grep "^${YEAR}-" ${TMPFILE} |awk '{print $1" "$2","$7","$8}' > ${DAILYFILE}
            # TO-DO: There is a bug somehwere in parse_memstats script which produces
            # --reboot detected ------------------ entries when the directory has more files
            # than the those that match the specific date. This is a workaround for this
            # bug.
            sed -i '/,0,0/d' ${DAILYFILE}
        else
            local DAILYFILE=filestats-${PROCESS_NAME}-${DATE}.csv
            ../parse_filestats --name ${DATE} --cmd ${PROCESS_NAME} --detail > ${TMPFILE}
            grep "^${YEAR}-" ${TMPFILE} |awk '{print $1" "$2","$8","$9","$10}' > ${DAILYFILE}
        fi
        cat ${DAILYFILE} >> ${SUMMARYFILE}
    done
    rm ${TMPFILE}
}

if [[ $# -eq 0 ]]; then
    echo "ERROR: No arguments provided."
    print_usage
fi

CURDIR=$(pwd)
if [[ $# -eq 2 ]]; then
    if [[ $1 == "memstats" ]] || [[ $1 == "filestats" ]]; then
        if [ ! -f lab.conf ]; then
            echo "Lab configuration file is missing."
            echo "See http://wiki.wrs.com/PBUeng/TitaniumServerSysengToolsAndDataAnalysis for more info."
            exit 1
        fi

        source ./lab.conf

        ALL_HOSTS="${CONTROLLER_LIST} ${STORAGE_LIST} ${COMPUTE_LIST}"
        for HOST in ${ALL_HOSTS}; do
            cd ${HOST}
            parse_daily_stats $1 $2
            cd ${CURDIR}
        done
    else
        echo "Specified parser $1 is not a valid parser."
        print_usage
    fi
elif [[ $# -eq 3 ]]; then
    if [[ $2 == "memstats" ]] || [[ $2 == "filestats" ]]; then
        if [ -d "$1" ]; then
            cd $1
            parse_daily_stats $2 $3
        else
            echo "ERROR: Specified host $1 does not exist."
            exit 1
        fi
    else
        echo "Specified parser $2 is not a valid parser."
        print_usage
    fi
else
    print_usage
fi

