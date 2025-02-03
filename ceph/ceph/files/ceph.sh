#!/bin/bash
#
# Copyright (c) 2023-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0

INITDIR=/etc/init.d
LOGFILE=/var/log/ceph/ceph-init.log
CEPH_STARTED_FLAG=/var/run/.ceph_started
CEPH_CONFIGURED_FLAG=/etc/platform/.node_ceph_configured

# Call ceph-init-wrapper script with systemd-run to avoid inheriting any
# unwanted file descriptor.
CEPH_INIT="systemd-run --pipe --wait ${INITDIR}/ceph-init-wrapper"

# Get system/node configuration
. /etc/platform/platform.conf

logecho ()
{
    local head="$(date "+%Y-%m-%d %H:%M:%S.%3N")"
    echo "$head ${BASHPID}: $@" >> ${LOGFILE}
    echo "$@"
}

# Exit immediately if ceph not configured
if [ ! -f "${CEPH_CONFIGURED_FLAG}" ]; then
    logecho "Ceph is not configured in this node. Exiting."
    exit 0
fi

# If system is an AIO the mtcClient will run this script twice
# from 2 locations on controllers.
# If this is a AIO DX+ it will also be called on compute nodes
# and it should be avoided since there is nothing to do.
# So exit the script if it is called from /etc//services.d/worker
if [[ "$system_type" == "All-in-one" ]]; then
    dir_path=$(dirname "$(realpath $0)")
    if [[ "$dir_path" == "/etc/services.d/worker" ]]; then
        logecho "Calling from '${dir_path}' and this is ${system_type^}. Exiting."
        exit 0
    fi
fi

start ()
{
    # Start Ceph processes according to the system_type and system_mode.
    # Set the flag CEPH_STARTED_FLAG to let ceph to be monitored by Pmon and SM.
    # The forcestart action is used to bypass the CEPH_STARTED_FLAG flag check
    # that is created only after all processes are running to prevent
    # Pmon and SM detecting process failure when monitoring the processes

    logecho "Starting Ceph processes on ${system_type^} ${system_mode^}"

    if [ "${system_type}" == "All-in-one" ] && [ "${system_mode}" == "simplex" ]; then
        ${CEPH_INIT} forcestart mon
        local rc_mon=$?
        logecho "RC mon: ${rc_mon}"

        ${CEPH_INIT} forcestart mds
        local rc_mds=$?
        logecho "RC mds: ${rc_mds}"

        ${CEPH_INIT} forcestart osd
        local rc_osd=$?
        logecho "RC osd: ${rc_osd}"
    fi

    if [ "${system_type}" == "All-in-one" ] && [ "${system_mode}" != "simplex" ]; then
        ${CEPH_INIT} forcestart mon.${HOSTNAME}
        local rc_mon=$?
        logecho "RC mon.${HOSTNAME}: ${rc_mon}"

        ${CEPH_INIT} forcestart mds
        local rc_mds=$?
        logecho "RC mds: ${rc_mds}"
    fi

    if [ "${system_type}" == "Standard" ]; then
        ${CEPH_INIT} forcestart
        local rc_all=$?
        logecho "RC all: ${rc_all}"

        ${CEPH_INIT} forcestart mds
        local rc_mds=$?
        logecho "RC mds: ${rc_mds}"
    fi

    logecho "Setting flag to enable ceph processes monitoring"
    if [ ! -f ${CEPH_STARTED_FLAG} ]; then
        touch ${CEPH_STARTED_FLAG}
    fi

    #restrict log file access
    chmod 0640 ${LOGFILE}
}

stop ()
{
    logecho "Stopping Ceph processes on ${system_type^} ${system_mode^}"
    if [ "${system_type}" == "All-in-one" ] && [ "${system_mode}" == "simplex" ]; then
        # AIO-SX do not stop services
        logecho "Ceph services will continue to run"

    elif [ "$system_type" == "All-in-one" ] && [ "${system_mode}" != "simplex" ]; then
        # AIO-DX and AIO-DX+
        # Will stop OSDs and MDS processes only.
        # mon.controller will be already stopped on standby controllers.
        # mon.${hostname} must be running.
        logecho "Ceph services will be stopped, except local ceph monitor"

        if [ -f ${CEPH_STARTED_FLAG} ]; then
            rm -f ${CEPH_STARTED_FLAG}
        fi

        ${CEPH_INIT} stop osd >> ${LOGFILE} 2>&1
        local rc_osd=$?
        logecho "RC osd: ${rc_osd}"

        ${CEPH_INIT} stop mds >> ${LOGFILE} 2>&1
        local rc_mds=$?
        logecho "RC mds: ${rc_mds}"

    else
        # Standard and Standard Dedicated Storage
        logecho "Stopping ceph services..."

        if [ -f ${CEPH_STARTED_FLAG} ]; then
            rm -f ${CEPH_STARTED_FLAG}
        fi

        ${CEPH_INIT} stop >> ${LOGFILE} 2>&1
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac

exit 0
