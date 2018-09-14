#!/bin/bash
# Purpose:
#  Remote stop engtools on all blades.

# Define common utility functions
TOOLBIN=$(dirname $0)
. ${TOOLBIN}/engtools_util.sh
if [ $UID -eq 0 ]; then
    ERRLOG "Do not start $0 using sudo/root access."
    exit 1
fi

# environment for system commands
source /etc/nova/openrc

declare -a BLADES
BLADES=( $(system host-list | awk '(/compute|controller|storage/) {print $4;}') )

LOG "Remote stop engtools on all blades:"
for blade in ${BLADES[@]}; do
    if [ "${blade}" == "${HOSTNAME}" ]; then
        LOG "stop on $blade:"
        sudo service collect-engtools.sh stop
    else
        ping -c1 ${blade} 1>/dev/null 2>/dev/null
        if [ $? -eq 0 ]; then
            LOG "stop on $blade:"
            ssh -q -t -o StrictHostKeyChecking=no \
            ${blade} sudo service collect-engtools.sh stop
        else
            WARNLOG "cannot ping: ${blade}"
        fi
    fi
done
LOG "done"

exit 0
