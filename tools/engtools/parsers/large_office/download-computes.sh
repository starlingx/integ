#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
# Create /opt/backups/tmp/syseng-data directory on controller 0, change mode of this
# directory to 777 and place this script and the lab.conf files there. It is recommended
# to set up password-less login from the controller to all storage and compute hosts
# before running the script.
#

if [ ! -f lab.conf ]; then
    echo "Lab configuration file is missing."
    echo "See http://wiki.wrs.com/PBUeng/TitaniumServerSysengToolsAndDataAnalysis for more info."
    exit 1
fi

source ./lab.conf

HOST_LIST="${STORAGE_LIST} ${COMPUTE_LIST}"

for HOST in ${HOST_LIST}; do
    rsync -azvh ${HOST}:/tmp/syseng_data/* .
done
