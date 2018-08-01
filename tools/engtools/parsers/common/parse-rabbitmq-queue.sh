#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
OUTFILE=$1
QUEUENAME=$2

FILES=$(ls *rabbitmq.bz2 | sort)

[ -e tmp.txt ] && rm tmp.txt

echo "Time/Date,Name,Pid,Messages,Messages Ready,Messages Unacknowledged,Memory,Consumers" >${OUTFILE}

for FILE in ${FILES}; do
    bzcat $FILE | grep -E "time\:|${QUEUENAME}" >>tmp.txt

    sed -i -e "s/\t/ /g" tmp.txt
done

while IFS='' read -r LINE || [[ -n "${LINE}" ]]; do
    TEST=$(echo ${LINE} | awk '{print $1}')
    TEST2=$(echo ${LINE} | awk '{print $2}')
    if [[ "${TEST}" == "time:" ]]; then
        TIMEDATE=$(echo ${LINE} | awk '{print $3" "$4}')
        MESSAGES=""
        NAME=""
        PID=""
        MESSAGES_READY=""
        MESSAGES_UNACKNOWLEDGED=""
        MEMORY=""
        CONSUMERS=""
    elif [[ "${TEST2}" == "${QUEUENAME}" ]]; then
        MESSAGES=$(echo ${LINE} | awk '{print $1}')
        NAME=$(echo ${LINE} | awk '{print $2}')
        PID=$(echo ${LINE} | awk '{print $3}')
        MESSAGES_READY=$(echo ${LINE} | awk '{print $4}')
        MESSAGES_UNACKNOWLEDGED=$(echo ${LINE} | awk '{print $5}')
        MEMORY=$(echo ${LINE} | awk '{print $6}')
        CONSUMERS=$(echo ${LINE} | awk '{print $7}')

        echo "${TIMEDATE},${NAME},${PID},${MESSAGES},${MESSAGES_READY},${MESSAGES_UNACKNOWLEDGED},${MEMORY},${CONSUMERS}" >> ${OUTFILE}

        TIMEDATE=""
        MESSAGES=""
        NAME=""
        PID=""
        MESSAGES_READY=""
        MESSAGES_UNACKNOWLEDGED=""
        MEMORY=""
        CONSUMERS=""
    fi
done < tmp.txt

rm tmp.txt

