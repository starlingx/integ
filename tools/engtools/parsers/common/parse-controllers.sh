#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#

# This script is used to parse stats data for controller/CPE hosts. For large office,
# it is called by parse-everything.sh. For CPE, it should be called on its own.
# File lab.conf must exist with CONTROLLER_LIST config parameter set for the script to run
# Usage: ./parse-controllers.sh

PARSERDIR=$(dirname $0)
. ${PARSERDIR}/parse-util.sh

if [ ! -f lab.conf ]; then
    echo "Lab configuration file is missing."
    echo "See http://wiki.wrs.com/PBUeng/TitaniumServerSysengToolsAndDataAnalysis for more info."
    exit 1
fi

source ./lab.conf

if [ -z "${CONTROLLER_LIST}" ]; then
    echo "ERROR: Controller list is not set in lab.conf file. Exiting..."
    exit 1
fi

for HOST in ${CONTROLLER_LIST}; do
    LOG "Parsing stats data for controller host ${HOST}"
    if [ -d ${HOST} ]; then
        cd ${HOST}
        bzip2 ${HOST}* > /dev/null 2>&1
        ../parse-all.sh ${HOST} > /dev/null 2>&1 &
        # Delay the next controller because they both write to /tmp
        sleep 120
        cd ..
    else
        ERRLOG "${HOST} does not exist. Parsing skipped."
    fi
done

# Parsing postgres connection stats is a time consuming step, run it in parallel with parse-all
# script.
for HOST in ${CONTROLLER_LIST}; do
    if [ -d ${HOST} ]; then
        LOG "Parsing postgres connection stats data for controller host ${HOST}"
        cd ${HOST}
        ../parse-postgres.sh *postgres.bz2 > /dev/null 2>&1 &
        cd ..
    fi
done
