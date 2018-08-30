#!/bin/bash
### BEGIN INIT INFO
# Provides:          collect-engtools
# Required-Start:    $local_fs $network $syslog postgresql
# Required-Stop:     $local_fs $network $syslog postgresql
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: initscript to launch engineering tools data collection daemon
# Description:       initscript to launch engineering tools data collection daemon
#                    Blah.
### END INIT INFO

PATH=/sbin:/usr/sbin:/bin:/usr/bin
DESC="collect engtools service"
NAME="collect-engtools.sh"
DAEMON=/usr/local/bin/${NAME}
DAEMON_ARGS="-f"
PIDFILE=/var/run/${NAME}.pid
SCRIPTNAME=/etc/init.d/${NAME}
DEFAULTFILE=/etc/default/${NAME}

# Exit if the package is not installed
[ -x "$DAEMON" ] || exit 0
. /etc/init.d/functions
# Read configuration variable file if it is present
[ -r $DEFAULTFILE ] && . $DEFAULTFILE

# Load the VERBOSE setting and other rcS variables
#. /lib/init/vars.sh

# Define lsb fallback versions of:
#   log_daemon_msg(), log_end_msg()
log_daemon_msg() { echo -n "${1:-}: ${2:-}"; }
log_end_msg() { echo "."; }

# Use lsb functions to perform the operations.
if [ -f /lib/lsb/init-functions ]; then
    . /lib/lsb/init-functions
fi

# Check for sufficient priviledges
# [ JGAULD : possibly provide user = 'operator' option instead... ]
if [ $UID -ne 0 ]; then
    log_daemon_msg "Starting ${NAME} requires sudo/root access."
    exit 1
fi

case $1 in
    start)
    if [ -e ${PIDFILE} ]; then
        pid=$(pidof -x ${NAME})
        if test "${pid}" != ""
        then
            echo_success "${NAME} already running"
        exit
        fi
    fi


    log_daemon_msg "Starting ${NAME}"
    if start-stop-daemon --start --background --quiet --oknodo --pidfile ${PIDFILE} \
                        --exec ${DAEMON} -- ${DAEMON_ARGS} ; then
        log_end_msg 0
    else
        log_end_msg 1
    fi
    ;;

    stop)
    if [ -e ${PIDFILE} ]; then
        pids=$(pidof -x ${NAME})
        if [[ ! -z "${pids}" ]]
        then
            echo_success "Stopping ${NAME} [$pid]"
            start-stop-daemon --stop --quiet --oknodo --pidfile ${PIDFILE} --retry=TERM/3/KILL/5
            # [ JGAULD: none of the following should be necessary ]
            /usr/local/bin/cleanup-engtools.sh
        else
            echo_failure "${NAME} is not running"
        fi
    else
        echo_failure "${PIDFILE} does not exist"
    fi
    ;;

    restart)
    $0 stop && sleep 2 && $0 start
    ;;

    status)
    if [ -e ${PIDFILE} ]; then
        pid=$(pidof -x ${NAME})
        if test "${pid}" != ""
        then
            echo_success "${NAME} is running"
        else
            echo_success "${NAME} is not running"
        fi
    else
        echo_success "${NAME} is not running"
    fi
    ;;

    reload)
    if [ -e ${PIDFILE} ]; then
        start-stop-daemon --stop --signal USR1 --quiet --pidfile ${PIDFILE} --name ${NAME}
        echo_success "${NAME} reloaded successfully"
    else
        echo_success "${PIDFILE} does not exist"
    fi
    ;;

    *)
    echo "Usage: $0 {start|stop|restart|reload|status}"
    exit 2
    ;;
esac

exit 0
