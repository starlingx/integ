#!/bin/sh

### BEGIN INIT INFO
# Provides:          HA-Proxy
# Required-Start:    networking
# Required-Stop:     networking
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: HA-Proxy TCP/HTTP reverse proxy
# Description:       HA-Proxy is a TCP/HTTP reverse proxy
### END INIT INFO

PATH=/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/usr/sbin/haproxy
NAME=haproxy
DESC="HA-Proxy TCP/HTTP reverse proxy"
PIDFILE="/var/run/$NAME.pid"
TPM_DATA_DIR="/var/run/TPM_haproxy/"
OPTS="-D -f /etc/haproxy/haproxy.cfg -p $PIDFILE"
RETVAL=0

# This is only needed till TPM In-Kernel
# ResourceMgr comes in
remove_TPM_transients () {
    _HANDLES=`find $TPM_DATA_DIR -type f -name "hp*.bin" -printf "%f "`
    for handle in $_HANDLES; do
        handle_addr=`echo $handle | sed 's/hp\([0-9]*\)\.bin/\1/g'`
        tss2_flushcontext -ha $handle_addr &> /dev/null
    done
    rm -f $TPM_DATA_DIR/*
}

start() {
    if [ -e $PIDFILE ]; then
        PIDDIR=/proc/$(cat $PIDFILE)
        if [ -d $PIDDIR ]; then
            echo "$DESC already running."
            return
        else
            echo "Removing stale PID file $PIDFILE"
            rm -f $PIDFILE
        fi
    fi

    # TODO: This is a temporary workaround till
    # we eventually add a resource manager for TPM
    mkdir -p $TPM_DATA_DIR

    echo -n "Starting $NAME: "

    TPM_DATA_DIR=$TPM_DATA_DIR start-stop-daemon --start --pidfile $PIDFILE -x "$DAEMON" -- $OPTS
    RETVAL=$?
    if [ $RETVAL -eq 0 ]; then
        echo "done."
    else
        remove_TPM_transients
        echo "failed."
    fi
}

stop() {
    if [ ! -e $PIDFILE ]; then
        return
    fi

    echo -n "Stopping $DESC..."

    start-stop-daemon --stop --quiet --retry 3 --oknodo --pidfile $PIDFILE -x "$DAEMON"
    if [ -n "`pidof $DAEMON`" ] ; then
        pkill -KILL -f $DAEMON
    fi
    echo "done."
    rm -f $PIDFILE
    rm -f /var/lock/subsys/$NAME
    remove_TPM_transients
}

status() {
    pid=`cat $PIDFILE 2>/dev/null`
    if [ -n "$pid" ]; then
        if ps -p $pid &>/dev/null ; then
            echo "$DESC is running"
            RETVAL=0
            return
        else
            RETVAL=1
        fi
    fi
    echo "$DESC is not running"
    RETVAL=1
}

check() {
    /usr/sbin/$NAME -c -q -V -f /etc/$NAME/$NAME.cfg
}

# See how we were called.
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart|force-reload|reload)
        stop
        start
        ;;
    status)
        status
        ;;
    check)
        check
        ;;
    *)
        echo "Usage: $0 {start|stop|force-reload|restart|reload|status|check}"
        RETVAL=1
        ;;
esac

exit $RETVAL
