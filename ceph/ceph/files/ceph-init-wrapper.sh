#!/bin/bash
#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# This script is a helper wrapper for pmon monitoring of ceph
# processes. The "/etc/init.d/ceph" script does not know if ceph is
# running on the node. For example when the node is locked, ceph
# processes are not running. In that case we do not want pmond to
# monitor these processes.
#
# The script "/etc/services.d/<node>/ceph.sh" will create the file
# "/var/run/.ceph_started" when ceph is running and remove it when
# is not.
#
# The script also extracts  one or more ceph process names  that are
# reported as 'not running' or 'dead' or 'failed'  by '/etc/intit.d/ceph status'
# and writes the names to a text file: /tmp/ceph_status_failure.txt for
# pmond to access. The pmond adds the text to logs and alarms. Example of text
# samples written to file by this script are:
#   'osd.1'
#   'osd.1, osd.2'
#   'mon.storage-0'
#   'mon.storage-0, osd.2'
#
# Moreover, for processes that are reported as 'hung' by '/etc/intit.d/ceph status'
# the script will try increase their logging to 'debug' for a configurable interval.
# With logging increased it will outputs a few stack traces then, at the end of this
# interval, it dumps its stack core and kills it.
#
# Return values;
# zero -   /etc/init.d/ceph returned success or ceph is not running on the node
# non-zero /etc/init.d/ceph returned a failure or invalid syntax
#

source /usr/bin/tsconfig
source /etc/platform/platform.conf

CEPH_SCRIPT="/etc/init.d/ceph"
CEPH_FILE="$VOLATILE_PATH/.ceph_started"
CEPH_GET_MON_STATUS_FILE="$VOLATILE_PATH/.ceph_getting_mon_status"
CEPH_GET_OSD_STATUS_FILE="$VOLATILE_PATH/.ceph_getting_osd_status"
CEPH_STATUS_FAILURE_TEXT_FILE="/tmp/ceph_status_failure.txt"

BINDIR=/usr/bin
SBINDIR=/usr/sbin
LIBDIR=/usr/lib64/ceph
ETCDIR=/etc/ceph
source $LIBDIR/ceph_common.sh

LOG_PATH=/var/log/ceph
LOG_FILE=$LOG_PATH/ceph-process-states.log
LOG_LEVEL=NORMAL  # DEBUG
verbose=0

DATA_PATH=$VOLATILE_PATH/ceph_hang    # folder where we keep state information
mkdir -p $DATA_PATH                   # make sure folder exists

MONITORING_INTERVAL=15
TRACE_LOOP_INTERVAL=5
CEPH_STATUS_TIMEOUT=20

LOCK_CEPH_MON_SERVICE_FILE="$VOLATILE_PATH/.ceph_mon_status"
LOCK_CEPH_OSD_SERVICE_FILE="$VOLATILE_PATH/.ceph_osd_status"
LOCK_CEPH_MON_STATUS_FILE="$VOLATILE_PATH/.ceph_mon_service"
LOCK_CEPH_OSD_STATUS_FILE="$VOLATILE_PATH/.ceph_osd_service"

# Seconds to wait for ceph status to finish before
# continuing to execute a service action
MONITOR_STATUS_TIMEOUT=30
MAX_STATUS_TIMEOUT=120

RC=0

# SM can only pass arguments through environment variable
# when ARGS is not empty use it to extend command line arguments
args=("$@")
if [ ! -z $ARGS ]; then
    IFS=";" read -r -a new_args <<< "$ARGS"
    args+=("${new_args[@]}")
fi

with_service_lock ()
{
    local target="$1"; shift
    [ -z "${target}" ] && target="mon osd"

    # Run in sub-shell so we don't leak file descriptors
    # used for locking service actions
    (
        # Grab service locks
        wlog "-" INFO "Grab service locks"
        [[ "${target}" == *"mon"* ]] && flock ${LOCK_CEPH_MON_SERVICE_FD}
        [[ "${target}" == *"osd"* ]] && flock ${LOCK_CEPH_OSD_SERVICE_FD}

        # Try to lock status with a timeout in case status is stuck
        wlog "-" INFO "Lock service status"
        deadline=$((SECONDS + MAX_STATUS_TIMEOUT + 1))
        if [[ "${target}" == *"mon"* ]]; then
            flock --exclusive --timeout ${MONITOR_STATUS_TIMEOUT} ${LOCK_CEPH_MON_STATUS_FD}
        fi
        if [[ "${target}" == *"osd"* ]]; then
            timeout=$((deadline - SECONDS))
            if [[ $timeout -gt 0 ]]; then
                flock --exclusive --timeout ${timeout} ${LOCK_CEPH_OSD_STATUS_FD}
            fi
        fi

        # Close lock file descriptors so they are
        # not inherited by the spawned process then
        # run service action
        wlog "-" INFO "Run service action: $@"
        "$@" {LOCK_CEPH_MON_SERVICE_FD}>&- \
             {LOCK_CEPH_MON_STATUS_FD}>&- \
             {LOCK_CEPH_OSD_SERVICE_FD}>&- \
             {LOCK_CEPH_OSD_STATUS_FD}>&-

    ) {LOCK_CEPH_MON_SERVICE_FD}>${LOCK_CEPH_MON_SERVICE_FILE} \
      {LOCK_CEPH_MON_STATUS_FD}>${LOCK_CEPH_MON_STATUS_FILE} \
      {LOCK_CEPH_OSD_SERVICE_FD}>${LOCK_CEPH_OSD_SERVICE_FILE} \
      {LOCK_CEPH_OSD_STATUS_FD}>${LOCK_CEPH_OSD_STATUS_FILE}
    RC=$?
}

start ()
{
    if [ ! -f ${CEPH_FILE} ]; then
        # Ceph is not running on this node, return success
        exit 0
    fi
    wlog "-" INFO "Ceph START $1 command received"
    with_service_lock "$1" ${CEPH_SCRIPT} start $1
    wlog "-" INFO "Ceph START $1 command finished."
}

stop ()
{
    wlog "-" INFO "Ceph STOP $1 command received."
    with_service_lock "$1" ${CEPH_SCRIPT} stop $1
    wlog "-" INFO "Ceph STOP $1 command finished."
}

restart ()
{
    if [ ! -f ${CEPH_FILE} ]; then
        # Ceph is not running on this node, return success
        exit 0
    fi
    wlog "-" INFO "Ceph RESTART $1 command received."
    with_service_lock "$1" ${CEPH_SCRIPT} restart $1
    wlog "-" INFO "Ceph RESTART $1 command finished."
}

log_and_restart_blocked_osds ()
{
    # Log info about the blocked osd daemons and then restart it
    local names=$1
    local message=$2
    for name in $names; do
        wlog $name "INFO" "$message"
        ${CEPH_SCRIPT} restart $name
    done
}

log_and_kill_hung_procs ()
{
    # Log info about the hung processes and then kill them; later on pmon will restart them
    local names=$1
    for name in $names; do
        type=`echo $name | cut -c 1-3`   # e.g. 'mon', if $item is 'mon1'
        id=`echo $name | cut -c 4- | sed 's/^\\.//'`
        get_conf run_dir "/var/run/ceph" "run dir"
        get_conf pid_file "$run_dir/$type.$id.pid" "pid file"
        pid=$(cat $pid_file)
        wlog $name "INFO" "Dealing with hung process (pid:$pid)"

        # monitoring interval
        wlog $name "INFO" "Increasing log level"
        execute_ceph_cmd ret $name "ceph daemon $name config set debug_$type 20/20"
        monitoring=$MONITORING_INTERVAL
        while [ $monitoring -gt 0 ]; do
            if [ $(($monitoring % $TRACE_LOOP_INTERVAL)) -eq 0 ]; then
                date=$(date "+%Y-%m-%d_%H-%M-%S")
                log_file="$LOG_PATH/hang_trace_${name}_${pid}_${date}.log"
                wlog $name "INFO" "Dumping stack trace to: $log_file"
                $(pstack $pid >$log_file) &
            fi
            let monitoring-=1
            sleep 1
        done
        wlog $name "INFO" "Trigger core dump"
        kill -ABRT $pid &>/dev/null
        rm -f $pid_file # process is dead, core dump is archiving, preparing for restart
        # Wait for pending systemd core dumps
        sleep 2 # hope systemd_coredump has started meanwhile
        deadline=$(( $(date '+%s') + 300 ))
        while [[ $(date '+%s') -lt "${deadline}" ]]; do
            systemd_coredump_pid=$(pgrep -f "systemd-coredump.*${pid}.*ceph-${type}")
            [[ -z "${systemd_coredump_pid}" ]] && break
            wlog $name "INFO" "systemd-coredump ceph-${type} in progress: pid ${systemd_coredump_pid}"
            sleep 2
        done
        kill -KILL $pid &>/dev/null
    done
}

status ()
{
    local target="$1"  # no shift here
    [ -z "${target}" ] && target="mon osd"

    if [ ! -f ${CEPH_FILE} ]; then
        # Ceph is not running on this node, return success
        exit 0
    fi

    if [[ "$system_type" == "All-in-one" ]] && [[ "$system_mode" != "simplex" ]] && [[ "$1" == "osd" ]]; then
        timeout $CEPH_STATUS_TIMEOUT ceph -s
        if [ "$?" -ne 0 ]; then
            # Ceph cluster is not accessible. Don't panic, controller swact
            # may be in progress.
            wlog "-" INFO "Ceph is down, ignoring OSD status."
            exit 0
        fi
    fi

    # Report success while ceph mon is running a service action
    # otherwise mark ceph mon status is in progress
    exec {LOCK_CEPH_MON_STATUS_FD}>${LOCK_CEPH_MON_STATUS_FILE}
    if [[ "${target}" == *"mon"* ]]; then
        flock --shared --nonblock ${LOCK_CEPH_MON_SERVICE_FILE} true
        if [[ $? -ne 0 ]]; then
            exit 0
        fi
        # Lock will be released when script exits
        flock --shared ${LOCK_CEPH_MON_STATUS_FD}
    fi
    # Report success while ceph mon is running a service action
    # otherwise mark ceph osd status is in progress
    exec {LOCK_CEPH_OSD_STATUS_FD}>${LOCK_CEPH_OSD_STATUS_FILE}
    if [[ "${target}" == *"osd"* ]]; then
        flock --shared --nonblock ${LOCK_CEPH_OSD_SERVICE_FILE} true
        if [[ $? -ne 0 ]]; then
            exit 0
        fi
        # Lock will be released when script exits
        flock --shared ${LOCK_CEPH_OSD_STATUS_FD}
    fi

    result=`${CEPH_SCRIPT} status $1 {LOCK_CEPH_MON_STATUS_FD}>&- {LOCK_CEPH_OSD_STATUS_FD}>&-`
    RC=$?
    if [ "$RC" -ne 0 ]; then
        erred_procs=`echo "$result" | sort | uniq | awk ' /not running|dead|failed/ {printf "%s ", $1}' | sed 's/://g' | sed 's/, $//g'`
        hung_procs=`echo "$result" | sort | uniq | awk ' /hung/ {printf "%s ", $1}' | sed 's/://g' | sed 's/, $//g'`
        blocked_ops_procs=`echo "$result" | sort | uniq | awk ' /blocked ops/ {printf "%s ", $1}' | sed 's/://g' | sed 's/, $//g'`
        stuck_peering_procs=`echo "$result" | sort | uniq | awk ' /stuck peering/ {printf "%s ", $1}' | sed 's/://g' | sed 's/, $//g'`
        invalid=0
        host=`hostname`
        if [[ "$system_type" == "All-in-one" ]] && [[ "$system_mode" != "simplex" ]]; then
            # On 2 node configuration we have a floating monitor
            host="controller"
        fi
        for i in $(echo $erred_procs $hung_procs); do
            if [[ "$i" =~ osd.?[0-9]?[0-9]|mon.$host ]]; then
                continue
            else
                invalid=1
            fi
        done

        log_and_restart_blocked_osds "$blocked_ops_procs"\
            "Restarting OSD with blocked operations"
        log_and_restart_blocked_osds "$stuck_peering_procs"\
            "Restarting OSD stuck peering"
        log_and_kill_hung_procs $hung_procs

        rm -f $CEPH_STATUS_FAILURE_TEXT_FILE
        if [ $invalid -eq 0 ]; then
            text=""
            for i in $erred_procs; do
                text+="$i, "
            done
            for i in $hung_procs; do
                text+="$i (process hang), "
            done
            echo "$text" | tr -d '\n' > $CEPH_STATUS_FAILURE_TEXT_FILE
        else
            echo "$host: '${CEPH_SCRIPT} status $1' result contains invalid process names: $erred_procs"
            echo "Undetermined osd or monitor id" > $CEPH_STATUS_FAILURE_TEXT_FILE
        fi
    fi

    if [[ $RC == 0 ]] && [[ "$1" == "mon" ]] && [[ "$system_type" == "All-in-one" ]] && [[ "$system_mode" != "simplex" ]]; then
        # SM needs exit code != 0 from 'status mon' argument of the init script on
        # standby controller otherwise it thinks that the monitor is running and
        # tries to stop it.
        # '/etc/init.d/ceph status mon' checks the status of monitors configured in
        # /etc/ceph/ceph.conf and if it should be running on current host.
        # If it should not be running it just exits with code 0. This is what
        # happens on the standby controller.
        # When floating monitor is running on active controller /var/lib/ceph/mon of
        # standby is not mounted (Ceph monitor partition is DRBD synced).
        test -e "/var/lib/ceph/mon/ceph-controller"
        if [ "$?" -ne 0 ]; then
            exit 3
        fi
    fi
}


case "${args[0]}" in
    start)
        start ${args[1]}
        ;;
    stop)
        stop ${args[1]}
        ;;
    restart)
        restart ${args[1]}
        ;;
    status)
        status ${args[1]}
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status} [{mon|osd|osd.<number>|mon.<hostname>}]"
        exit 1
        ;;
esac

exit $RC
