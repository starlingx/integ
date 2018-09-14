#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
# This script is used to download syseng data from all hosts to the analysis server
# for post processing.
# Syseng data are stored under /scratch/syseng_data on the controllers. Syseng data
# for storage and compute hosts, which are stored under /tmp/syseng_data, are pulled
# to the controllers via the script download-computes.sh and stored under
# /opt/backups/tmp/syseng-data.
#
# This script is to be run after running download-computes.sh on one of the controllers.

if [ ! -f lab.conf ]; then
    echo "Lab configuration file is missing."
    echo "See http://wiki.wrs.com/PBUeng/TitaniumServerSysengToolsAndDataAnalysis for more info."
    exit 1
fi

source ./lab.conf

rsync -azvh wrsroot@${CONTROLLER0_IP}:/scratch/syseng_data/* .
rsync -azvh wrsroot@${CONTROLLER1_IP}:/scratch/syseng_data/* .

rsync -azvh wrsroot@${CONTROLLER0_IP}:/opt/backups/tmp/syseng-data/* .
rsync -azvh wrsroot@${CONTROLLER1_IP}:/opt/backups/tmp/syseng-data/* .

# Compress the newly download data files if they have not been compressed
CURDIR=$(pwd)
ALL_HOSTS="${CONTROLLER_LIST} ${STORAGE_LIST} ${COMPUTE_LIST}"

for HOST in ${ALL_HOSTS}; do
    if [ -e ${HOST} ]; then
        echo "Compressing ${HOST}"
        cd ${CURDIR}/${HOST}
        bzip2 ${HOST}*
        cd ${CURDIR}
    else
        echo "${HOST} not found"
    fi
done
