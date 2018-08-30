#!/bin/bash
# Purpose:
#  bzip2 compress engtools data on all nodes.

# Define common utility functions
TOOLBIN=$(dirname $0)
. ${TOOLBIN}/engtools_util.sh
if [ $UID -eq 0 ]; then
    ERRLOG "Do not start $0 using sudo/root access."
    exit 1
fi

# environment for system commands
source /etc/nova/openrc

declare -a CONTROLLER
declare -a COMPUTE
declare -a STORAGE
CONTROLLER=( $(system host-list | awk '(/controller/) {print $4;}') )
COMPUTE=( $(system host-list | awk '(/compute/) {print $4;}') )
STORAGE=( $(system host-list | awk '(/storage/) {print $4;}') )

LOG "Remote bzip2 engtools data on all blades:"
for blade in ${CONTROLLER[@]}; do
    ping -c1 ${blade} 1>/dev/null 2>/dev/null
    if [ $? -eq 0 ]; then
        LOG "bzip2 on $blade:"
        ssh -q -t -o StrictHostKeyChecking=no \
        ${blade} sudo bzip2 /scratch/syseng_data/${blade}/*
    else
        WARNLOG "cannot ping: ${blade}"
    fi
done
for blade in ${STORAGE[@]} ${COMPUTE[@]} ; do
    ping -c1 ${blade} 1>/dev/null 2>/dev/null
    if [ $? -eq 0 ]; then
        LOG "bzip2 on $blade:"
        ssh -q -t -o StrictHostKeyChecking=no \
        ${blade} sudo bzip2 /tmp/syseng_data/${blade}/*
    else
        WARNLOG "cannot ping: ${blade}"
    fi
done
LOG "done"

exit 0
