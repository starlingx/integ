#!/bin/bash
# Purpose:
#  rsync data from all nodes to backup location.

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
declare -a CONTROLLER
declare -a STORAGE
declare -a COMPUTE
BLADES=( $(system host-list | awk '(/compute|controller|storage/) {print $4;}') )
CONTROLLER=( $(system host-list | awk '(/controller/) {print $4;}') )
COMPUTE=( $(system host-list | awk '(/compute/) {print $4;}') )
STORAGE=( $(system host-list | awk '(/storage/) {print $4;}') )

DEST=/opt/backups/syseng_data/
if [[ "${HOSTNAME}" =~ "controller-" ]]; then
    LOG "rsync DEST=${DEST}"
else
    LOG "*ERROR* only run this on controller"
    exit 1
fi
sudo mkdir -p ${DEST}

# rsync options
USER=wrsroot
RSYNC_OPT="-r -l --safe-links -h -P --stats --exclude=*.pyc"

# Rsync data from multiple locations
LOG "rsync engtools data from all blades:"

# controllers
SRC=/scratch/syseng_data/
DEST=/opt/backups/syseng_data/
for HOST in ${CONTROLLER[@]}
do
    ping -c1 ${HOST} 1>/dev/null 2>/dev/null
    if [ $? -eq 0 ]; then
        LOG "rsync ${RSYNC_OPT} ${USER}@${HOST}:${SRC} ${DEST}"
        sudo rsync ${RSYNC_OPT} ${USER}@${HOST}:${SRC} ${DEST}
    else
        WARNLOG "cannot ping: ${HOST}"
    fi
done

# computes & storage
SRC=/tmp/syseng_data/
DEST=/opt/backups/syseng_data/
for HOST in ${STORAGE[@]} ${COMPUTE[@]}
do
    ping -c1 ${HOST} 1>/dev/null 2>/dev/null
    if [ $? -eq 0 ]; then
        LOG "rsync ${RSYNC_OPT} ${USER}@${HOST}:${SRC} ${DEST}"
        sudo rsync ${RSYNC_OPT} ${USER}@${HOST}:${SRC} ${DEST}
    else
        WARNLOG "cannot ping: ${HOST}"
    fi
done
LOG 'done'

exit 0
