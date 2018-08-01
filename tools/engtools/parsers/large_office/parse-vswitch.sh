#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
NODE=$1

if [ `ls vswitch*.csv 2>/dev/null | wc -l` -gt 0 ]; then
    rm vswitch*.csv
fi

[ -e tmp.txt ] && rm tmp.txt

FILES=$(ls *vswitch.bz2 | sort)

for FILE in ${FILES}; do
    bzcat ${FILE} | grep -E "time\:|vshell|\||" >> tmp.txt
done

    while IFS='' read -r LINE || [[ -n "${LINE}" ]]; do
        if [[ "${LINE}" == "# vshell engine-list" ]]; then
            CURTABLE="engine"
        elif [[ "${LINE}" == "# vshell engine-list" ]]; then
            CURTABLE="engine"
        elif [[ "${LINE}" == "# vshell engine-stats-list" ]]; then
            CURTABLE="engine-stats"
        elif [[ "${LINE}" == "# vshell port-list" ]]; then
            CURTABLE="ports"
        elif [[ "${LINE}" == "# vshell port-stats-list" ]]; then
            CURTABLE="port-stats"
        elif [[ "${LINE}" == "# vshell network-list" ]]; then
            CURTABLE="networks"
        elif [[ "${LINE}" == "# vshell network-stats-list" ]]; then
            CURTABLE="network-stats"
        elif [[ "${LINE}" == "# vshell interface-list" ]]; then
            CURTABLE="interfaces"
        elif [[ "${LINE}" == "# vshell interface-stats-list" ]]; then
            CURTABLE="interface-stats"
        else
            TEST=$(echo ${LINE} | awk '{print $1}')
            if [[ "${TEST}" == "time:" ]]; then
                TIMESTAMP=$(echo ${LINE} | awk '{print $3" "$4}')
            elif [[ "${CURTABLE}" == "engine-stats" ]]; then
                ENGINE=$(echo ${LINE} | awk '{print $4}')
                if [[ "${ENGINE}" == "0" ]] || [[ "${ENGINE}" == "1" ]]; then
                    PARAMS=$(echo ${LINE} | awk '{print $4","$6","$8","$10","$12","$14","$16","$18","$20}')
                    echo "${TIMESTAMP},${PARAMS}" >>vswitch-engine-${ENGINE}-${NODE}.csv
                fi
            elif [[ "${CURTABLE}" == "port-stats" ]]; then
                PORTTYPE=$(echo ${LINE} | awk '{print $6}')
                if [[ "${PORTTYPE}" == "physical" ]]; then
                    PORTNUM=$(echo ${LINE} | awk '{print $4}')
                    PARAMS=$(echo ${LINE} | awk '{print $8","$10","$12","$14","$16","$18","$20}')
                    echo "${TIMESTAMP},${PARAMS}" >>vswitch-port-${PORTNUM}-${NODE}.csv
                fi
            elif [[ "${CURTABLE}" == "interface-stats" ]]; then
                IFNAME=$(echo ${LINE} | awk '{print $8}')
                if [[ "${IFNAME}" == "eth0" ]] || [[ "${IFNAME}" == "eth1" ]]; then
                    PARAMS=$(echo ${LINE} | awk '{print $10","$12","$14","$16","$18","$20","$22","$24","$26","$28}')
                    echo "${TIMESTAMP},${PARAMS}" >>vswitch-interface-${IFNAME}-${NODE}.csv
                fi
            fi
        fi
    done < tmp.txt

rm tmp.txt

