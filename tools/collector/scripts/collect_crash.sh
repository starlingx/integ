#! /bin/bash
#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables

source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="crash"
LOGFILE="${extradir}/${SERVICE}.info"


CRASHDIR="/var/crash"

echo    "${hostname}: Kernel Crash Info .: ${LOGFILE}"

COMMAND="find ${CRASHDIR}"
delimiter ${LOGFILE} "${COMMAND}"
${COMMAND} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

COMMAND="rsync -a --include=*.txt --include=*/ --exclude=* ${CRASHDIR} ${basedir}/var/"
delimiter ${LOGFILE} "${COMMAND}"
${COMMAND} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

exit 0
