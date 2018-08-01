#! /bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables

source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="coredump"
LOGFILE="${extradir}/${SERVICE}.info"


COREDUMPDIR="/var/lib/systemd/coredump"

echo    "${hostname}: Core Dump Info ....: ${LOGFILE}"

files=`ls ${COREDUMPDIR} | wc -l`
if [ "${files}" == "0" ] ; then
    echo "No core dumps" >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
else
    COMMAND="ls -lrtd ${COREDUMPDIR}/*"
    delimiter ${LOGFILE} "${COMMAND}"
    ${COMMAND} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

    COMMAND="md5sum ${COREDUMPDIR}/*"
    delimiter ${LOGFILE} "${COMMAND}"
    ${COMMAND} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
fi

exit 0
