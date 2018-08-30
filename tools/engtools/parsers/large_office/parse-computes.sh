#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#

# This script is used to parse stats data for storage and compute hosts. It is not
# relevant for CPE. For large office, it is called by parse-everything.sh script.
# File lab.conf must exist for the script to run. The STORAGE_LIST and COMPUTE_LIST
# config parameters can be set to suit the parsing needs.

PARSERDIR=$(dirname $0)
. ${PARSERDIR}/parse-util.sh

if [ ! -f lab.conf ]; then
    echo "Lab configuration file is missing."
    echo "See http://wiki.wrs.com/PBUeng/TitaniumServerSysengToolsAndDataAnalysis for more info."
    exit 1
fi

source ./lab.conf

if [ -z "${STORAGE_LIST}" ]; then
    # This script could be invoked from another script or run separately so write to both
    # console and log file.
    echo "STORAGE_LIST is not set in lab.conf file. Skipping stats parsing for all storage."
    WARNLOG "STORAGE_LIST is not set in lab.conf file. Skipping stats parsing for all storage."
else
    for HOST in ${STORAGE_LIST}; do
        LOG "Parsing stats data for storage host ${HOST}"
        if [ -d ${HOST} ]; then
            cd ${HOST}
            bzip2 ${HOST}*  > /dev/null 2>&1
            ../parse-all.sh ${HOST} > /dev/null 2>&1 &
            cd ..
        else
            ERRLOG "${HOST} does not exist. Parsing skipped."
        fi
    done
fi

if [ -z "${COMPUTE_LIST}" ]; then
    echo "COMPUTE_LIST is not set in lab.conf file. Skipping stats parsing for all computes."
    WARNLOG "COMPUTE_LIST is not set in lab.conf file. Skipping stats parsing for all computes."
    exit 1
else
    # If there is a large number of computes, they need to be parsed one batch at a time,
    # otherwise, the analysis server will be brought down to a crawl. Set the number of
    # computes to process in parallel as batches of 25 if it's not set in lab.conf
    BATCH_SIZE=${BATCH_SIZE:-25}

    count=0
    for HOST in ${COMPUTE_LIST}; do
        LOG "Parsing stats data for compute host ${HOST}"
        if [ -d ${HOST} ]; then
            cd ${HOST}
            bzip2 ${HOST}*  > /dev/null 2>&1
            ../parse-all.sh ${HOST} > /dev/null 2>&1 &
            cd ..
            ((count++))
            if [ $count == ${BATCH_SIZE} ]; then
                # Wait for this batch to finish before starting a new one
                wait
                count=0
            fi
        else
            ERRLOG "${HOST} does not exist. Parsing skipped."
        fi
    done
fi
