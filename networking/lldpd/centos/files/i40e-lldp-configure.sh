#!/bin/bash
################################################################################
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################

# Certain i40e network devices (XL710 Fortville) have an internal firmware LLDP
# agent enabled by default. This can prevent LLDP PDUs from being processed by
# the driver and any upper layer agents.
#
# This script allows a user to enable and disable the internal LLDP agent.
#
# Note: debugfs must be enabled in the kernel
#
# To enable:
# ./i40e-lldp-configure.sh start
#
# To disable:
# ./i40e-lldp-configure.sh stop

PROGNAME=$(basename $0)
DEBUGFS_PATH=/sys/kernel/debug
DEBUGFS_I40_DEVICES_PATH=$DEBUGFS_PATH/i40e
LLDP_COMMAND=lldp

function log {
    local MSG="${PROGNAME}: $1"
    logger -p notice "${MSG}"
}

function err {
    local MSG="${PROGNAME}: $1"
    logger -p error "${MSG}"
}

function configure_device {
    local DEVICE=$1
    local ACTION=$2
    local DEVICE_PATH=${DEBUGFS_I40_DEVICES}/${DEVICE}

    if [ ! -d ${DEVICE_PATH} ]; then
        return 1
    fi

    echo "${LLDP_COMMAND} ${ACTION}" > ${DEVICE_PATH}/command
    RET=$?

    if [ ${RET} -ne 0 ]; then
        err "Failed to ${ACTION} internal LLDP agent for device ${DEVICE}"
        return ${RET}
    fi

    log "${ACTION} internal LLDP agent for device ${DEVICE}"
    return ${RET}
}

function is_debugfs_mounted {
    if grep -qs "${DEBUGFS_PATH}" /proc/mounts; then
    return 0
    fi
    return 1
}

function mount_debugfs {
    mount -t debugfs none ${DEBUGFS_PATH}
}

function unmount_debugfs {
    umount ${DEBUGFS_PATH}
}

function scan_devices {
    local ACTION=$1
    local DEBUGFS_MOUNTED="false"
    local DEVICES=${DEBUGFS_I40_DEVICES_PATH}/*

    if is_debugfs_mounted; then
        DEBUGFS_MOUNTED="true"
    fi

    if [ ${DEBUGFS_MOUNTED} = "false" ]; then
        mount_debugfs
        RET=$?
        if [ ${RET} -ne 0 ]; then
            err "Failed to mount debugfs"
            return ${RET}
        fi
        log "Mounted debugfs"
    fi

    for DEVICE in $DEVICES; do
        configure_device ${DEVICE} ${ACTION}
    done

    if [ ${DEBUGFS_MOUNTED} = "false" ]; then
        unmount_debugfs
        RET=$?
        if [ ${RET} -ne 0 ]; then
            err "Failed to unmount debugfs"
            return ${RET}
        fi
        log "Unmounted debugfs"
    fi

    return 0
}

function start {
    scan_devices start
    return $?
}

function stop {
    scan_devices stop
    return $?
}

function status {
    return 0
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac
