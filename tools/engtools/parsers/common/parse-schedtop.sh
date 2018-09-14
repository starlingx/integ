#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#

# When occtop stats (occtop-xxx.csv) and schedtop summary (schedtop-summary-xxx.txt)
# show high CPU occupancy and a list of high runners for a particular host, this script can
# be used to generate detail stats for the offending service(s). The command line only takes
# one service name. To specify more than one service, update the SERVICE_LIST in host.conf file.
#
# Usage:
# ./parse-schedtop.sh <host-name>
# ./parse-schedtop.sh <host-name> <service-name>

PARSERDIR=$(dirname $0)
. ${PARSERDIR}/parse-util.sh

function print_usage {
    echo "Usage: ./parse-schedtop.sh <host-name>"
    echo "       ./parse-schedtop.sh <host-name> <service-name>"
    echo "e.g. >./parse-schedtop.sh controller-0 nova-conductor"
    exit 1
}

function sedit {
    local FILETOSED=$1
    sed -i -e "s/  */ /g" ${FILETOSED}
    sed -i -e "s/ /,/2g" ${FILETOSED}
    # Remove any trailing comma
    sed -i "s/,$//" ${FILETOSED}
}

function parse_schedtop_data {
    HOST=$1
    SERVICE=$2
    LOG "Parsing ${SERVICE} schedtop for host ${HOST}"
    ../parse_schedtop --detail --field=occ --sum=${SERVICE} *schedtop.bz2 > tmp.txt
    sedit tmp.txt
    grep '^[0-9]' tmp.txt > tmp2.txt
    echo "Date/Time,dt(s),occ(%)" > schedtop-${SERVICE}-${HOST}.csv
    cat tmp2.txt >> schedtop-${SERVICE}-${HOST}.csv
}

if [[ $# -eq 0 ]]; then
    # Parsing detail schedtop stats for all services configured in host.conf for all hosts would
    # take a very long time and is often unnecessary. Until the performance issue with parse_schedtop
    # is addressed, this is not supported.
    print_usage
else
    if [ ! -d "$1" ]; then
        echo "ERROR: Specified host $1 does not exist."
        exit 1
    fi
    if [[ $# -eq 1 ]]; then
        cd $1
        if [ ! -f host.conf ]; then
            echo "Host configuration file is missing."
            echo "See http://wiki.wrs.com/PBUeng/TitaniumServerSysengToolsAndDataAnalysis for more info."
            exit 1
        fi
        source ./host.conf
        if [ -z "${SERVICE_LIST}" ]; then
            # This script could be invoked from parse-all script or executed independently so display the
            # error on the console and as well as log it to file.
            echo "ERROR: The SERVICE_LIST config parameter is not set in host.conf file."
            ERRLOG "SERVICE_LIST config parameter is not set in host.conf file. Detail schedtop parsing skipped for $1."
            exit 1
        fi
        for SERVICE in ${SERVICE_LIST}; do
            # This could be the most time consuming step. Jim G.'s suggestion:
            #
            # We could rewrite some of the pattern matching outputs to use 'tab' for separate columns of
            # occupancy output, to make that 1-pass instead of multi-pass per variable we are after.
            # Should monitory loadavg and per-cpu usage and iowait and memory usage of the parsers – if
            # we are idel and can handle more load, we should do more of these in parallel, and just call
            # 'wait' at the end.
            #
            # May also consider using "GNU parallel" package to parallel the entire function, e.g.
            # function do_parallel_work() { do_command }
            # do_parallel_work arg1 arg2 &
            # do parallel_work arg3 arg4 &
            # wait
            #
            # Can also export function "export -f func_name" and run that function in another bash command
            parse_schedtop_data $1 ${SERVICE}
        done
    elif [[ $# -eq 2 ]]; then
        cd $1
        parse_schedtop_data $1 $2
    else
        print_usage
    fi
    [ -e tmp.txt ] && rm tmp.txt tmp2.txt
fi
