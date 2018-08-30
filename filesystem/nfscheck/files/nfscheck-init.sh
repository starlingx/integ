#!/bin/sh
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# chkconfig: 345 99 10

### BEGIN INIT INFO
# Provides:          nfscheck
# Required-Start:    $syslog
# Required-Stop:     $syslog
# Default-Start:     2 3 5
# Default-Stop:      0 1 6
# Short-Description: nfscheck
# Description:       NFS Audit
### END INIT INFO

DESC="nfscheck"
DAEMON="/usr/bin/nfscheck"
PIDFILE="/var/run/nfscheck.pid"

start()
{
    if [ -e $PIDFILE ]; then
        PIDDIR=/proc/$(cat $PIDFILE)
        if [ -d ${PIDDIR} ]; then
            echo "$DESC already running."
            exit 1
        else
            echo "Removing stale PID file $PIDFILE"
            rm -f $PIDFILE
        fi
    fi

    echo -n "Starting $DESC..."

    start-stop-daemon --start --quiet --background \
        --pidfile ${PIDFILE} --make-pidfile --exec ${DAEMON}

    if [ $? -eq 0 ]; then
        echo "done."
    else
        echo "failed."
    fi
}

stop()
{
    echo -n "Stopping $DESC..."
    start-stop-daemon --stop --quiet --pidfile $PIDFILE
    if [ $? -eq 0 ]; then
        echo "done."
    else
        echo "failed."
    fi
    rm -f $PIDFILE
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart|force-reload)
        stop
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|force-reload|restart}"
        exit 1
        ;;
esac

exit 0
