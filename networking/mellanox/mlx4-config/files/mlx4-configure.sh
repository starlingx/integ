#!/bin/bash
################################################################################
# Copyright (c) 2015 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################

PROGNAME=$(basename $0)
VENDOR_MLX4="0x15b3"
SYSFS_PCI_DEVICES=/sys/bus/pci/devices
DEBUG=${DEBUG:-0}

# enable complex pattern matching so that in "configure_device()" we can get
# all files beginning in "mlx4_port" and ending in one or more digits.
shopt -s extglob

function log {
    local MSG="${PROGNAME}: $1"
    if [ ${DEBUG} -ne 0 ]; then
        echo "${MSG}"
    fi
    echo "${MSG}" >> /var/log/mlx4-configure.log
}

function configure_device {
    local DEVICE=$1
    local DEVICE_PATH=${SYSFS_PCI_DEVICES}/${DEVICE}

    if [ ! -d ${DEVICE_PATH} ]; then
        log "device path ${DEVICE_PATH} not present for ${DEVICE}"
        return 1
    fi

    local PORTS=$(ls -v1 ${DEVICE_PATH}/mlx4_port+([0-9]))

    local RESULT=0
    for PORT in ${PORTS}; do
        local PORT_NAME=$(basename ${PORT})
        local PORT_TYPE=$(cat ${PORT})

        if [ "${PORT_TYPE}" != "eth" ]; then
            echo "eth" > ${PORT}
            if [ $? -ne 0 ]; then
                log "failed to change ${DEVICE}/${PORT_NAME} port type from \"${PORT_TYPE}\" to \"eth\""
                RESULT=1
            else
                log "successfully changed ${DEVICE}/${PORT_NAME} port type from \"${PORT_TYPE}\" to \"eth\""
            fi
        else
            log "port type already set to \"eth\" for ${DEVICE}/${PORT_NAME}"
        fi
    done

    return ${RESULT}
}


function scan_devices {
    local DEVICES=$(ls -1 ${SYSFS_PCI_DEVICES})

    for DEVICE in ${DEVICES}; do
        local VENDOR=$(cat ${SYSFS_PCI_DEVICES}/${DEVICE}/vendor)
        local CLASS=$(cat ${SYSFS_PCI_DEVICES}/${DEVICE}/class)

        if ((((${CLASS} & 0xff0000)) != 0x020000)); then
            ## Not a networking controller
            continue
        fi

        if [ "${VENDOR}" != "${VENDOR_MLX4}" ]; then
            ## Not a Mellanox device
            continue
        fi

        configure_device ${DEVICE}
    done

    return 0
}


function start {
    scan_devices
    return $?
}

function stop {
    return 0
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
