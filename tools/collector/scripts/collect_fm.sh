#! /bin/bash
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables

source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="alarms"
LOGFILE="${extradir}/${SERVICE}.info"

function is_service_active {
    active=`sm-query service management-ip | grep "enabled-active"`
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

    echo    "${hostname}: System Alarm List .: ${LOGFILE}"

    # These go into the SERVICE.info file
    delimiter ${LOGFILE} "fm alarm-list"
    fm alarm-list 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}
fi

exit 0
