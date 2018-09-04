#! /bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables
source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="ceph"
LOGFILE="${extradir}/ceph.info"
echo    "${hostname}: Ceph Info .........: ${LOGFILE}"

function is_service_active {
    active=`sm-query service management-ip | grep "enabled-active"`
    if [ -z "$active" ] ; then
        return 0
    else
        return 1
    fi
}

function exit_if_timeout {
    if [ "$?" = "124" ] ; then
        echo "Exiting due to ceph command timeout" >> ${LOGFILE}
        exit 0
    fi
}

###############################################################################
# Only Controller
###############################################################################
if [ "$nodetype" = "controller" ] ; then

    # Using timeout with all ceph commands because commands can hang for
    # minutes if the ceph cluster is down. If ceph is not configured, the
    # commands return immediately.

    delimiter ${LOGFILE} "ceph status"
    timeout 30 ceph status >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    exit_if_timeout

    delimiter ${LOGFILE} "ceph mon dump"
    timeout 30 ceph mon dump >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    exit_if_timeout

    delimiter ${LOGFILE} "ceph osd dump"
    timeout 30 ceph osd dump >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    exit_if_timeout

    delimiter ${LOGFILE} "ceph osd tree"
    timeout 30 ceph osd tree >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    exit_if_timeout

    delimiter ${LOGFILE} "ceph osd crush dump"
    timeout 30 ceph osd crush dump >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    exit_if_timeout

    is_service_active
    if [ "$?" = "0" ] ; then
        exit 0
    fi

    delimiter ${LOGFILE} "ceph df"
    timeout 30 ceph df >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    exit_if_timeout

    delimiter ${LOGFILE} "ceph osd df tree"
    timeout 30 ceph osd df tree >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    exit_if_timeout

    delimiter ${LOGFILE} "ceph health detail"
    timeout 30 ceph health detail >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    exit_if_timeout

fi

exit 0
