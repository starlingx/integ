#! /bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables
source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="inventory"
LOGFILE="${extradir}/${SERVICE}.info"
RPMLOG="${extradir}/rpm.info"

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

    echo    "${hostname}: Software Config ...: ${RPMLOG}"
    # These go into the SERVICE.info file
    delimiter ${RPMLOG} "rpm -qa"
    rpm -qa >> ${RPMLOG}

    is_service_active
    if [ "$?" = "0" ] ; then
        exit 0
    fi

    echo    "${hostname}: System Inventory ..: ${LOGFILE}"

    # These go into the SERVICE.info file
    delimiter ${LOGFILE} "system host-list"
    system host-list 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}

    delimiter ${LOGFILE} "system service-list"
    system service-list 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}

    delimiter ${LOGFILE} "nova service-list"
    nova service-list 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}

    delimiter ${LOGFILE} "neutron host-list"
    neutron host-list 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}

    delimiter ${LOGFILE} "system host-port-list controller-0"
    system host-port-list controller-0 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}

    delimiter ${LOGFILE} "system host-port-list controller-1"
    system host-port-list controller-1 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}

    delimiter ${LOGFILE} "Dump all Instances"
    nova list --fields name,status,OS-EXT-SRV-ATTR:host --all-tenant 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}

    delimiter ${LOGFILE} "vm-topology"
    timeout 60 vm-topology --show all 2>>${COLLECT_ERROR_LOG} >> ${LOGFILE}

    cp -a /opt/platform ${extradir}
fi


exit 0
