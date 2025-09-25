#!/bin/bash
#
# Copyright (c) 2024-2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# This script monitors the Ceph network for carrier on an AIO-DX system.
# To prevent data corruption, when there is no carrier from the Ceph network,
# the floating monitor, the osds and the mds processes will be stopped.

source /etc/platform/platform.conf

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

save_state()
{
    [ ! -z "$1" ] && CURRENT_STATE="$1"
    echo ${CURRENT_STATE} > ${STATE_FILE}
}

RETVAL=0
STATE_FILE="/var/run/ceph/.sm-storage-networking-state"
STATE_RUNNING="Running"
STATE_STOPPED="Stopped"
CURRENT_STATE=$(cat ${STATE_FILE} 2>/dev/null)

# Sanity check for the CURRENT_STATE variable
if [ "${CURRENT_STATE}" != "${STATE_RUNNING}" ]; then
    save_state ${STATE_STOPPED}
fi

################################################################################
# Start Service
################################################################################

start()
{
    log INFO "Start ceph-storage-network service"
    [ "${CURRENT_STATE}" == "${STATE_RUNNING}" ] && return

    status
    STATUS_RETURN=$?
    if [ ${STATUS_RETURN} -eq 0 ]; then
        save_state ${STATE_RUNNING}
        RETVAL=0
    else
        save_state ${STATE_STOPPED}
    fi
}

################################################################################
# Stop Service
################################################################################

stop()
{
    log INFO "Stop ceph-storage-network service"

    local services="osd mds mon.controller"

    # sequentially stopping ceph-osd, ceph-mds, then the float monitor
    for service in ${services}; do
        log INFO "Force stopping ceph services"
        ${CEPH_SCRIPT} forcestop ${service}
    done

    [ "${CURRENT_STATE}" == "${STATE_RUNNING}" ] && save_state ${STATE_STOPPED}

    return
}

################################################################################
# Status Action
################################################################################

has_ceph_network_carrier()
{
    # Checks the carrier (cable connected) for Ceph network interface
    # If no-carrier is detected, then the interface has no physical link
    eval local INTERFACE=\$${ceph_network}_interface
    if [ -z "${INTERFACE}" ]; then
        log ERROR "Cannot detect Ceph network. Skipping network carrier detection"
        return 0
    fi

    ip link show "${INTERFACE}" | grep NO-CARRIER
    if [ $? -eq 0 ]; then
        log INFO "Ceph network '${INTERFACE}' has NO-CARRIER, cannot start ceph-mon"
        return 1
    fi
    return 0
}

# Verify if oam, cluster host and mgmt networks have carrier.
# This is a special condition for AIO-DX Direct setup.
# If all networks have no carrier, then the other host is down.
# When the other host is down, ceph must start on this host.
# Return 0 if no carrier is detected on all network interfaces.
# Return 1 of carrier has been detected in at lease one network interface.
has_all_network_no_carrier()
{
    ip link show "${oam_interface}" | grep NO-CARRIER
    local oam_carrier=$?
    ip link show "${cluster_host_interface}" | grep NO-CARRIER
    local cluster_host_carrier=$?
    ip link show "${management_interface}" | grep NO-CARRIER
    local mgmt_carrier=$?

    # Check if all networks have no carrier, meaning the other host is down
    if [ "${oam_carrier}" -eq 0 ] && [ "${cluster_host_carrier}" -eq 0 ] && [ "${mgmt_carrier}" -eq 0 ]; then
        log INFO "No carrier detected from all network interfaces"
        return 0
    fi
    return 1
}

status()
{
    has_ceph_network_carrier
    HAS_CARRIER=$?

    if [ "${CURRENT_STATE}" == "${STATE_RUNNING}" ] && [ ${HAS_CARRIER} -eq 0 ]; then
        # Service is "running" and has carrier.
        RETVAL=0
    else
        if [ ${HAS_CARRIER} -ne 0 ]; then
            if [ "${system_mode}" == "duplex-direct" ]; then
                has_all_network_no_carrier
                if [ $? -eq 0 ]; then
                    log INFO "All network interfaces are not functional, considering the other host is down. Keep Ceph running."
                    RETVAL=0
                else
                    log INFO "Ceph network interface is not functional in duplex-direct, stopping Ceph."
                    stop
                    RETVAL=1
                fi
            else
                log INFO "Ceph network interface is not functional, stopping Ceph."
                stop
                RETVAL=1
            fi
        else
            RETVAL=1
        fi
    fi

    # NOTE: The Status return is only used in the Start method to validate that there
    # is a carrier on the Ceph network before stating that the SM service is Running.
    return ${HAS_CARRIER}
}

################################################################################
# Main Entry
################################################################################

# This script should run only in AIO-DX called by sm
if [ "${system_type}" != "All-in-one" ] || [ "${system_mode}" == "simplex" ]; then
    log WARN "This script must be called only from All-in-one duplex."
    exit 0
fi

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    *)
        echo "usage: $0 { start | stop | status }"
        exit 1
        ;;
esac

exit ${RETVAL}
