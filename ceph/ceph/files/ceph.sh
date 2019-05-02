#!/bin/bash

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
    logecho "Starting ceph services..."
    ${INITDIR}/ceph start >> ${LOGFILE} 2>&1
    RC=$?

    if [ ! -f ${CEPH_FILE} ]; then
        touch ${CEPH_FILE}
    fi
}

stop ()
{
    if [[ "$system_type" == "All-in-one" ]] && [[ "$system_mode" == "simplex" ]]; then
        logecho "Ceph services will continue to run on node"
        exit 0
    fi

    logecho "Stopping ceph services..."

    if [ -f ${CEPH_FILE} ]; then
        rm -f ${CEPH_FILE}
    fi

    ${INITDIR}/ceph stop >> ${LOGFILE} 2>&1
    RC=$?
}

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
