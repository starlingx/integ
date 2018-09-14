#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
# This script removes uncompressed file. It can save a huge amount of disk space
# on the analysis server. Run this script after the very last time the data is parsed
# and BEFORE running parse-daily.sh script.
# If it is run after each intermediary parse, the download-data.sh script will download the
# uncompressed files again.

if [ ! -f lab.conf ]; then
    echo "Lab configuration file is missing."
    echo "See http://wiki.wrs.com/PBUeng/TitaniumServerSysengToolsAndDataAnalysis for more info."
    exit 1
fi

source ./lab.conf
YEAR=`date +'%Y'`

files="${FILE_LIST// /, }"
read -p "Are you sure you want to remove all uncompressed $files files? [Y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Y]$ ]]; then
    for FILE in ${FILE_LIST}; do
        rm -v */*_${YEAR}-*${FILE}
    done
else
    echo "Remove request cancelled."
fi

