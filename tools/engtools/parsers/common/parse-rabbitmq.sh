#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
OUTFILE=$1

FILES=$(ls *rabbitmq.bz2 | sort)

[ -e tmp.txt ] && rm tmp.txt

echo "Time/Date,Memory Total,Connection Readers,Connection Writers,Connection Channels,Connection Other,Queue Procs,Queue Slave Procs,Plugins,Other Proc,Mnesia,Mgmt DB,Msg Index,Other ETS,Binary,Code,Atom,Other System,VM Memory High Watermark,VM Memory Limit,Disk Free Limit,Disk Free,Descriptor Limit,Descriptors Used,Sockets Limit,Sockets Used,Processes Limit,Processes Used,Run Queue,Uptime" >${OUTFILE}

for FILE in ${FILES}; do
    bzcat $FILE | grep -E "time\:|\{memory\,\[\{total|\{connection_readers|\{connection_writers|\{connection_channels|\{connection_other|\{queue_procs|\{queue_slave_procs|\{plugins|\{other_proc|\{mnesia|\{mgmt_db|\{msg_index|\{other_ets|\{binary|\{code|\{atom|\{other_system|\{vm_memory_high_watermark|\{vm_memory_limit|\{disk_free_limit|\{disk_free|\{file_descriptors|\{total_used|\{sockets_limit|\{sockets_used|\{processes|\{run_queue|\{uptime" >>tmp.txt

    sed -i -e "s/  //g" tmp.txt
    sed -i -e "s/ {/{/g" tmp.txt
    sed -i -e "s/time:/time: /g" tmp.txt
    sed -i -e "s/}//g" tmp.txt
    sed -i -e "s/\[//g" tmp.txt
    sed -i -e "s/\]//g" tmp.txt
    sed -i -e 's/{used/,/g' tmp.txt
    sed -i -e 's/,/ /g' tmp.txt
done

while IFS='' read -r LINE || [[ -n "${LINE}" ]]; do
    TEST=$(echo ${LINE} | awk '{print $1}')
    if [[ "${TEST}" == "time:" ]]; then
        TIMEDATE=$(echo ${LINE} | awk '{print $3" "$4}')
        TOTAL=""
        CONNECTION_READERS=""
        CONNECTION_WRITERS=""
        CONNECTION_CHANNELS=""
        CONNECTION_OTHER=""
        QUEUE_PROCS=""
        QUEUE_SLAVE_PROCS=""
        PLUGINS=""
        OTHER_PROC=""
        MNESIA=""
        MGMT_DB=""
        MSG_INDEX=""
        OTHER_ETS=""
        BINARY=""
        CODE=""
        ATOM=""
        OTHER_SYSTEM=""
        VM_MEMORY_HIGH_WATERMARK=""
        VM_MEMORY_LIMIT=""
        DISK_FREE_LIMIT=""
        DISK_FREE=""
        TOTAL_LIMIT=""
        TOTAL_USED=""
        SOCKETS_LIMIT=""
        SOCKETS_USED=""
        LIMIT=""
        USED=""
        RUN_QUEUE=""
        UPTIME=""
    elif [[ "${TEST}" == "{memory{total" ]]; then
        TOTAL=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{memory" ]]; then
        TOTAL=$(echo ${LINE} | awk '{print $3}')
    elif [[ "${TEST}" == "{connection_readers" ]]; then
        CONNECTION_READERS=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{connection_writers" ]]; then
        CONNECTION_WRITERS=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{connection_channels" ]]; then
        CONNECTION_CHANNELS=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{connection_other" ]]; then
        CONNECTION_OTHER=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{queue_procs" ]]; then
        QUEUE_PROCS=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{queue_slave_procs" ]]; then
        QUEUE_SLAVE_PROCS=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{plugins" ]]; then
        PLUGINS=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{other_proc" ]]; then
        OTHER_PROC=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{mnesia" ]]; then
        MNESIA=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{mgmt_db" ]]; then
        MGMT_DB=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{msg_index" ]]; then
        MSG_INDEX=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{other_ets" ]]; then
        OTHER_ETS=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{binary" ]]; then
        BINARY=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{code" ]]; then
        CODE=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{atom" ]]; then
        ATOM=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{other_system" ]]; then
        OTHER_SYSTEM=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{vm_memory_high_watermark" ]]; then
        VM_MEMORY_HIGH_WATERMARK=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{vm_memory_limit" ]]; then
        VM_MEMORY_LIMIT=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{disk_free_limit" ]]; then
        DISK_FREE_LIMIT=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{disk_free" ]]; then
        DISK_FREE=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{file_descriptors{total_limit" ]]; then
        TOTAL_LIMIT=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{file_descriptors" ]]; then
        TOTAL_LIMIT=$(echo ${LINE} | awk '{print $3}')
    elif [[ "${TEST}" == "{total_used" ]]; then
        TOTAL_USED=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{sockets_limit" ]]; then
        SOCKETS_LIMIT=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{sockets_used" ]]; then
        SOCKETS_USED=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{processes{limit" ]]; then
        LIMIT=$(echo ${LINE} | awk '{print $2}')
        USED=$(echo ${LINE} | awk '{print $3}')
    elif [[ "${TEST}" == "{processes" ]]; then
        LIMIT=$(echo ${LINE} | awk '{print $3}')
        USED=$(echo ${LINE} | awk '{print $4}')
    elif [[ "${TEST}" == "{run_queue" ]]; then
        RUN_QUEUE=$(echo ${LINE} | awk '{print $2}')
    elif [[ "${TEST}" == "{uptime" ]]; then
        UPTIME=$(echo ${LINE} | awk '{print $2}')

        echo "${TIMEDATE},${TOTAL},${CONNECTION_READERS},${CONNECTION_WRITERS},${CONNECTION_CHANNELS},${CONNECTION_OTHER},${QUEUE_PROCS},${QUEUE_SLAVE_PROCS},${PLUGINS},${OTHER_PROC},${MNESIA},${MGMT_DB},${MSG_INDEX},${OTHER_ETS},${BINARY},${CODE},${ATOM},${OTHER_SYSTEM},${VM_MEMORY_HIGH_WATERMARK},${VM_MEMORY_LIMIT},${DISK_FREE_LIMIT},${DISK_FREE},${TOTAL_LIMIT},${TOTAL_USED},${SOCKETS_LIMIT},${SOCKETS_USED},${LIMIT},${USED},${RUN_QUEUE},${UPTIME}" >> ${OUTFILE}

        TIMEDATE=""
        TOTAL=""
        CONNECTION_READERS=""
        CONNECTION_WRITERS=""
        CONNECTION_CHANNELS=""
        CONNECTION_OTHER=""
        QUEUE_PROCS=""
        QUEUE_SLAVE_PROCS=""
        PLUGINS=""
        OTHER_PROC=""
        MNESIA=""
        MGMT_DB=""
        MSG_INDEX=""
        OTHER_ETS=""
        BINARY=""
        CODE=""
        ATOM=""
        OTHER_SYSTEM=""
        VM_MEMORY_HIGH_WATERMARK=""
        VM_MEMORY_LIMIT=""
        DISK_FREE_LIMIT=""
        DISK_FREE=""
        TOTAL_LIMIT=""
        TOTAL_USED=""
        SOCKETS_LIMIT=""
        SOCKETS_USED=""
        LIMIT=""
        USED=""
        RUN_QUEUE=""
        UPTIME=""
    fi
done < tmp.txt

rm tmp.txt
