#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
# This script is used to parse postgres bz2 files for postgres connection stats.
# It is called by parse-controllers.sh script for either large office or CPE.

source ../lab.conf

PARSERDIR=$(dirname $0)
. ${PARSERDIR}/parse-util.sh

if [ -z "${DATABASE_LIST}" ]; then
    WARNLOG "DATABASE_LIST is not set in the lab.conf file. Use default setting"
    DATABASE_LIST="cinder glance keystone nova neutron ceilometer heat sysinv aodh postgres nova_api"
fi

# Do all files if no files specified
if [ -z "${1}" ]; then
    FILES=$(ls controller*postgres.bz2)
else
    FILES=$(ls $@)
fi
LOG "Parsing postgres files ${FILES}"

function generate_header {
    local header="Date/Time,Total"
    for DB in ${DATABASE_LIST}; do
        if [ ${DB} == "nova_api" ]; then
            header="${header},Nova API"
        else
            header="${header},${DB^}"
        fi
    done
    for DB in ${DATABASE_LIST}; do
        if [ ${DB} == "nova_api" ]; then
            header="${header},Nova API Active"
        else
            header="${header},${DB^} Active"
        fi
    done
    for DB in ${DATABASE_LIST}; do
        if [ ${DB} == "nova_api" ]; then
            header="${header},Nova API Idle"
        else
            header="${header},${DB^} Idle"
        fi
    done
    for DB in ${DATABASE_LIST}; do
        if [ ${DB} == "nova_api" ]; then
            header="${header},Nova API Other"
        else
            header="${header},${DB^} Other"
        fi
    done
    echo $header
}

function generate_grep_str {
    local grepstr="time:"
    for DB in ${DATABASE_LIST}; do
        grepstr="${grepstr}|${DB}"
    done
    grepstr="${grepstr}|breakdown|connections total|rows"
    echo $grepstr
}

function init_variables {
    CONN_TOTAL="0"
    CONN_ACTIVE_TOTAL="0"
    CONN_IDLE_TOTAL="0"
    CONN_OTHER_TOTAL="0"
    FIRST_TIME="no"
    INIT_VAL="0"
    for DB in ${DATABASE_LIST}; do
        eval "CONN_${DB^^}=${INIT_VAL}"
        eval "CONN_ACTIVE_${DB^^}=${INIT_VAL}"
        eval "CONN_IDLE_${DB^^}=${INIT_VAL}"
        eval "CONN_OTHER_${DB^^}=${INIT_VAL}"
    done
}

function output_values {
    local result="${DATEVAL} ${TIMEVAL},${CONN_TOTAL}"
    for DB in ${DATABASE_LIST}; do
        val=$(eval echo \${CONN_${DB^^}})
        result=$result,$val
    done
    for DB in ${DATABASE_LIST}; do
        val=$(eval echo \${CONN_ACTIVE_${DB^^}})
        result=$result,$val
    done
    for DB in ${DATABASE_LIST}; do
        val=$(eval echo \${CONN_IDLE_${DB^^}})
        result=$result,$val
    done
    for DB in ${DATABASE_LIST}; do
        val=$(eval echo \${CONN_OTHER_${DB^^}})
        result=$result,$val
    done
    echo $result >> postgres-conns.csv
}

HEADER=$(generate_header)
echo ${HEADER} > postgres-conns.csv
GREPSTR=$(generate_grep_str)

[ -e postgres-tmp2.txt ] && rm postgres-tmp2.txt

for FILE in ${FILES}; do
    TEST=`echo ${FILE} | grep bz2`
    if [ ! -z "${TEST}" ]; then
        bzcat ${FILE} | grep -E "time:|active|idle|breakdown|total|rows" >> postgres-tmp2.txt
    fi
    cat postgres-tmp2.txt | grep -E "${GREPSTR}" > postgres-tmp.txt
done

# Start parsing

FIRST_TIME="yes"
PARSING_TABLE="no"

while IFS='' read -r LINE || [[ -n "${LINE}" ]]; do
    TEST=`echo ${LINE} | grep "time:" | awk '{print $4}'`
    if [ ! -z "${TEST}" ]; then
        DATEVAL=`echo ${LINE} | awk '{print $3}'`
        TIMEVAL=`echo ${LINE} | awk '{print $4}'`

        if [ "z${FIRST_TIME}" != "zyes" ]; then
            init_variables
            FIRST_TIME="no"
        fi
    fi

    TEST=`echo ${LINE} | grep "connections total =" | awk '{print $4}'`
    if [ ! -z "${TEST}" ]; then
        CONN_TOTAL=${TEST}
    fi

    TEST=`echo ${LINE} | grep "connections breakdown (query)"`
    if [ ! -z "${TEST}" ]; then
        PARSING_TABLE="yes"
    fi

    if [ "x${PARSING_TABLE}" == "xyes" ]; then
        TESTNAME=`echo ${LINE} | grep "|" | awk '{print $1}'`
        TESTVAL=`echo ${LINE} | grep "|" | awk '{print $5}'`
        CONNSTATE=`echo ${LINE} | grep "|" | awk '{print $3}'`

        # This gets last field regardless of number of preceding spaces
        FIELDS=(${LINE// / })
        for I in ${!FIELDS[@]}; do
            TESTVAL=${FIELDS[${I}]}
        done

        for DB in ${DATABASE_LIST}; do
            if [ "x${TESTNAME}" == "x${DB}" ]; then
                eval "CONN_${DB^^}=$((CONN_${DB^^} + ${TESTVAL}))"
                break
            fi
        done

        if [ "x${CONNSTATE}" == "xidle" ]; then
            for DB in ${DATABASE_LIST}; do
                if [ "x${TESTNAME}" == "x${DB}" ]; then
                    eval "CONN_IDLE_${DB^^}=$((CONN_IDLE_${DB^^} + ${TESTVAL}))"
                    break
                fi
            done
        elif [ "x${CONNSTATE}" == "xactive" ]; then
            for DB in ${DATABASE_LIST}; do
                if [ "x${TESTNAME}" == "x${DB}" ]; then
                    eval "CONN_ACTIVE_${DB^^}=$((CONN_ACTIVE_${DB^^} + ${TESTVAL}))"
                    break
                fi
            done
        else
            for DB in ${DATABASE_LIST}; do
                if [ "x${TESTNAME}" == "x${DB}" ]; then
                    eval "CONN_OTHER_${DB^^}=$((CONN_OTHER_${DB^^} + ${TESTVAL}))"
                    break
                fi
            done
        fi

        TEST=`echo ${LINE} | grep "rows"`
        if [ ! -z "${TEST}" ]; then
            PARSING_TABLE="no"
            output_values
            init_variables
        else
            TEST=`echo ${LINE} | grep "age:"`
            if [ ! -z "${TEST}" ]; then
                PARSING_TABLE="no"
                echo "${DATEVAL} ${TIMEVAL} - no data"
                init_variables
            fi
        fi
    fi
done < postgres-tmp.txt

rm postgres-tmp.txt postgres-tmp2.txt
LOG "Parsing postgres connection stats data completed!"
