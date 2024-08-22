#!/bin/bash
#
# Copyright (c) 2023-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0

INITDIR=/etc/init.d
LOGFILE=/var/log/ceph/ceph-init.log
CEPH_FILE=/var/run/.ceph_started

# Get our nodetype
. /etc/platform/platform.conf

# Exit immediately if ceph not configured (i.e. no mon in the config file)
if ! grep -q "mon\." /etc/ceph/ceph.conf
then
    exit 0
fi

logecho ()
{
    echo $1
    date >> ${LOGFILE}
    echo $1 >> ${LOGFILE}
}

start ()
{
    # Defer ceph initialization to avoid race conditions. Let SM and Pmon to start the
    # processes in the appropriate time.
    # Set the flag to let ceph start later.
    logecho "Setting flag to enable ceph processes to start."
    if [ ! -f ${CEPH_FILE} ]; then
        touch ${CEPH_FILE}
    fi
}

stop ()
{
    if [ "${system_type}" == "All-in-one" ] && [ "${system_mode}" == "simplex" ]; then
        # AIO-SX
        logecho "Ceph services will continue to run on node"
        RC=0
    elif [ "$system_type" == "All-in-one" ] && [ "${system_mode}" != "simplex" ]; then
        # AIO-DX and AIO-DX+
        # Will stop OSDs and MDS processes only.
        # mon.controller will be already stopped on standby controllers.
        # mon.${hostname} must be running.
        logecho "Ceph services will be stopped, except local ceph monitor"

        if [ -f ${CEPH_FILE} ]; then
            rm -f ${CEPH_FILE}
        fi

        ${INITDIR}/ceph-init-wrapper stop osd >> ${LOGFILE} 2>&1
        local rc_osd=$?
        logecho "rc_osd=${rc_osd}"

        ${INITDIR}/ceph-init-wrapper stop mds >> ${LOGFILE} 2>&1
        local rc_mds=$?
        logecho "rc_mds=${rc_mds}"

        RC=0
        [ ${rc_osd} -ne 0 ] || [ ${rc_mds} -ne 0 ] && RC=1
    else
        # Standard and Standard Dedicated Storage
        logecho "Stopping ceph services..."

        if [ -f ${CEPH_FILE} ]; then
            rm -f ${CEPH_FILE}
        fi

        ${INITDIR}/ceph-init-wrapper stop >> ${LOGFILE} 2>&1
        RC=$?
    fi
}

# If system is an AIO the mtcClient will run this script twice
# from 2 locations and this generates some errors.
# So we have to exit the script if is called
# from /etc/services.d/worker in order to be executed once
if [[ "$system_type" == "All-in-one" ]]; then
    dir_path=$(dirname "$(realpath $0)")
    if [[ "$dir_path" == "/etc/services.d/worker" ]]; then
        exit 0
    fi
fi

RC=0

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

logecho "RC was: $RC"
exit $RC
