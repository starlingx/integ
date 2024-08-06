#!/bin/bash
#
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# This script monitors the Ceph network for carrier on an AIO-DX system.
# To prevent data corruption, when there is no carrier from the Ceph network,
# the floating monitor, the osds and the mds processes will be stopped.

source /etc/platform/platform.conf

CEPH_FILE="/var/run/.ceph_started"
CEPH_SCRIPT="/etc/init.d/ceph-init-wrapper"

source /usr/lib/ceph/ceph_common.sh
LOG_PATH=/var/log/ceph
LOG_FILE=$LOG_PATH/ceph-process-states.log
LOG_LEVEL=NORMAL  # DEBUG

# Log Management
# Adding PID and PPID informations
log () {
    local name=""
    local log_level="$1"
    # Checking if the first parameter is not a log level
    if grep -q -v ${log_level} <<< "INFO DEBUG WARN ERROR"; then
        name=" ($1)";
        log_level="$2"
        shift
    fi

    shift

    local message="$@"
    # prefix = <pid_subshell> <ppid_name>[<ppid>] <name|optional>
    local prefix="${BASHPID} $(cat /proc/${PPID}/comm)[${PPID}]${name}"
    # yyyy-MM-dd HH:mm:ss.SSSSSS /etc/init.d/ceph-storage-network <prefix> <log_level>: <message>
    wlog "${prefix}" "${log_level}" "${message}"
    return 0
}

identify_ceph_network_interface() {
    if [ "${ceph_network}" == "mgmt" ]; then
        ceph_network_interface="${management_interface}"
        return 0
    fi

    if [ "${ceph_network}" == "cluster-host" ]; then
        ceph_network_interface="${cluster_host_interface}"
        return 0
    fi

    return 1
}

RETVAL=0

################################################################################
# Stop Ceph Services
################################################################################

stop()
{
    # This script should run only in AIO-DX called by sm. Double check it.
    if [ "${system_type}" == "All-in-one" ] && [ "${system_mode}" != "simplex" ]; then
        services="osd mds mon.controller"
    else
        services="osd mds mon"
    fi

    # sequentially stopping ceph-osd, ceph-mds, then ceph-mon
    for service in $services; do
        ${CEPH_SCRIPT} forcestop ${service}
    done

    return
}

################################################################################
# Status Action
################################################################################

has_ceph_network_carrier()
{
    # Checks the carrier (cable connected) for Ceph network interface
    # If no-carrier is detected, then the interface has no physical link
    eval local interface=\$${ceph_network}_interface
    if [ -z ${interface} ]; then
        log ERROR "Cannot detect Ceph network. Skipping network carrier detection"
        return 0
    fi

    ip link show "${interface}" | grep NO-CARRIER
    if [ $? -eq 0 ]; then
        log INFO "Ceph network '${interface}' has NO-CARRIER, cannot start ceph-mon"
        return 1
    fi
    return 0
}

status()
{
    if [ ! -f ${CEPH_FILE} ]; then
        # Ceph is not running on this node, return success
        return
    fi

    has_ceph_network_carrier
    if [ $? -ne 0 ]; then
        # communication failure detected
        # stopping ceph services to avoid data corruption
        stop
        RETVAL=1
    fi

    return
}

################################################################################

# Main Entry

################################################################################

case "$1" in
    start)
        status
        ;;
    stop)
        RETVAL=0
        ;;
    status)
        status
        ;;
    *)
        echo "usage: $0 { start | stop | status }"
        exit 1
        ;;
esac

exit $RETVAL

