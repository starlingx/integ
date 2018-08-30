#! /bin/bash
#
# Copyright (c) 2013-2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# Loads Up Utilities and Commands Variables
source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

LOGFILE="${extradir}/nfv-vim.info"
echo    "${hostname}: NFV-Vim Info ......: ${LOGFILE}"

function is_service_active()
{
    active=`sm-query service vim | grep "enabled-active"`
    if [ -z "$active" ] ; then
        return 0
    else
        return 1
    fi
}

###############################################################################
# Only Controller
###############################################################################

if [ "$nodetype" = "controller" ] ; then
    is_service_active
    if [ "$?" = "0" ] ; then
        exit 0
    fi

    # Assumes that database_dir is unique in /etc/nfv/vim/config.ini
    DATABASE_DIR=$(awk -F "=" '/database_dir/ {print $2}' /etc/nfv/vim/config.ini)

    SQLITE_DUMP="/usr/bin/sqlite3 ${DATABASE_DIR}/vim_db_v1 .dump"

    delimiter ${LOGFILE} "dump database"
    timeout 30 ${SQLITE_DUMP} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
fi

exit 0

