#!/bin/bash
TOOLNAME=$(basename $0)
PIDFILE=/var/run/${TOOLNAME}.pid
TOOL_DEBUG=1
TOOL_EXIT_SIGNAL=0
TOOL_USR1_SIGNAL=0
TOOL_USR2_SIGNAL=0
TOOL_TTY=0
if tty 1>/dev/null ; then
    TOOL_TTY=1
fi

# [ JGAULD : SHOULD RENAME TO TOOL_X ]
OPT_USE_INTERVALS=0
OPT_FOREVER=0
PERIOD_MIN=5
INTERVAL_SEC=60
CPULIST=0

# Include lsb functions
if [ -d /lib/lsb ]; then
    . /lib/lsb/init-functions
else
    . /etc/init.d/functions
fi
# Lightweight replacement for pidofproc -p <pid>
function check_pidfile ()
{
    local pidfile pid

    OPTIND=1
    while getopts p: opt ; do
    case "$opt" in
    p)
        pidfile="$OPTARG"
        ;;
    esac
    done
    shift $(($OPTIND - 1))

    read pid < "${pidfile}"
    if [ -n "${pid:-}" ]; then
        if $(kill -0 "${pid:-}" 2> /dev/null); then
            echo "$pid"
            return 0
        elif ps "${pid:-}" >/dev/null 2>&1; then
            echo "$pid"
            return 0 # program is running, but not owned by this user
        else
            return 1 # program is dead and /var/run pid file exists
        fi
    fi
}

# tools_init - initialize tool resources
function tools_init ()
{
    local rc=0
    local error=0
    TOOLNAME=$(basename $0)

  # Check for sufficient priviledges
    if [ $UID -ne 0 ]; then
        ERRLOG "${NAME} requires sudo/root access."
        return 1
    fi

  # Check for essential binaries
    ECHO=$(which echo 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ECHO=echo   # use bash built-in echo
        ${ECHO} "FATAL, 'echo' not found, rc=$rc";
        error=$rc
    fi
    DATE=$(which date 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ${ECHO} "FATAL, 'date' not found, rc=$rc";
        error=$rc
    fi

  # Check for standard linux binaries, at least can use LOG functions now
  # - these are used in tools_header
    CAT=$(which cat 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'cat' not found, rc=$rc";
        error=$rc
    fi

    ARCH=$(which arch 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'arch' not found, rc=$rc";
        error=$rc
    fi

    SED=$(which sed 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'sed' not found, rc=$rc";
        error=$rc
    fi

    GREP=$(which grep 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'grep' not found, rc=$rc";
        error=$rc
    fi

    WC=$(which wc 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'wc' not found, rc=$rc";
        error=$rc
    fi

    UNAME=$(which uname 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'uname' not found, rc=$rc";
        error=$rc
    fi

    SORT=$(which sort 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'sort' not found, rc=$rc";
        error=$rc
    fi

    TR=$(which tr 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'tr' not found, rc=$rc";
        error=$rc
    fi

    AWK=$(which awk 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'awk' not found, rc=$rc";
        error=$rc
    fi

    PKILL=$(which pkill 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'pkill' not found, rc=$rc";
        error=$rc
    fi

    LS=$(which ls 2>/dev/null)
    rc=$?
    if [ $rc -ne 0 ]; then
        ERRLOG "'ls' not found, rc=$rc";
        error=$rc
    fi

  # The following block is needed for LSB systems such as Windriver Linux.
  # The utility is not available on CentOS so comment it out.
  # Generic utility, but may not be available
  # LSB=$(which lsb_release 2>/dev/null)
  # rc=$?
  # if [ $rc -ne 0 ]; then
  #   WARNLOG "'lsb_release' not found, rc=$rc";
  # fi

  # Let parent program decide what to do with the errors,
  # give ominous warning
    if [ $error -eq 1 ]; then
        WARNLOG "possibly cannot continue, missing linux binaries"
    fi

  # Check if tool was previously running
    if [ -e ${PIDFILE} ]; then
    # [ JGAULD - remove pidofproc() / LSB compatibility issue ]
    if check_pidfile -p "${PIDFILE}" >/dev/null; then
        ERRLOG "${PIDFILE} exists and ${TOOLNAME} is running"
        return 1
    else
      # remove pid file
        WARNLOG "${PIDFILE} exists but ${TOOLNAME} is not running; cleaning up"
        rm -f ${PIDFILE}
    fi
    fi

  # Create pid file
    echo $$ > ${PIDFILE}

  # Setup trap handler - these signals trigger child shutdown and cleanup
    trap tools_exit_handler INT HUP TERM EXIT
    trap tools_usr1_handler USR1
    trap tools_usr2_handler USR2

    return ${rc}
}

# tools_cleanup() - terminate child processes
function tools_cleanup() {
  # restore signal handling to default behaviour
    trap - INT HUP TERM EXIT
    trap - USR1 USR2

    local VERBOSE_OPT=''
    if [ "$1" -ne "0" ]; then
        LOG "cleanup invoked with code: $1"
        if [ ${TOOL_DEBUG} -ne 0 ]; then
            VERBOSE_OPT='-v'
        fi
    fi


  # stop all processes launched from this process
    pkill -TERM -P $$
    if [ "$1" -ne "0" ]; then
        sleep 1
    fi

  # OK, if the above didn't work, use force
    pkill -KILL -P $$

  # remove pid file
    if [ -e ${PIDFILE} ]; then
        rm -f ${VERBOSE_OPT} ${PIDFILE}
    fi
    exit $1
}

# tools_exit_handler() - exit handler routine
function tools_exit_handler() {
    TOOL_EXIT_SIGNAL=1
    tools_cleanup 128
}
# tools_usr1_handler() - USR1 handler routine
function tools_usr1_handler() {
    TOOL_USR1_SIGNAL=1
    LOG "caught USR1"
}
# tools_usr2_handler() - USR2 handler routine
function tools_usr2_handler() {
    TOOL_USR2_SIGNAL=1
    LOG "caught USR1"
}

# LOG(), WARNLOG(), ERRLOG() - simple print log functions (not logger)
function LOG ()
{
    local tstamp_H=$( date +"%Y-%0m-%0e %H:%M:%S" )
    echo "${tstamp_H} ${HOSTNAME} $0($$): $@";
}
function LOG_NOCR ()
{
    local tstamp_H=$( date +"%Y-%0m-%0e %H:%M:%S" )
    echo -n "${tstamp_H} ${HOSTNAME} $0($$): $@";
}
function WARNLOG () { LOG "WARN $@"; }
function ERRLOG ()  { LOG "ERROR $@"; }

# TOOL_HIRES_TIME() - easily parsed date/timestamp and hi-resolution uptime
function TOOL_HIRES_TIME()
{
    echo "time: " $( ${DATE} +"%a %F %H:%M:%S.%N %Z %z" ) "uptime: " $( cat /proc/uptime )
}

# set_affinity() - set affinity for current script if a a CPULIST is defined
function set_affinity() {
    local CPULIST=$1
    if [ -z "${CPULIST}" ]; then
        return
    fi

  # Set cpu affinity for current program
    local TASKSET=$(which taskset 2>/dev/null)
    if [ -x "${TASKSET}" ]; then
        ${TASKSET} -pc ${CPULIST} $$ 2>/dev/null
    fi
}

# cmd_idle_priority() - command to set nice + ionice
function cmd_idle_priority() {
    local NICE=""
    local IONICE=""

    NICE=$( which nice 2>/dev/null )
    if [ $? -eq 0 ]; then
        NICE="${NICE} -n 19"
    else
        NICE=""
    fi
    IONICE=$( which ionice 2>/dev/null )
    if [ $? -eq 0 ]; then
        IONICE="${IONICE} -c 3"
    else
        IONICE=""
    fi
    echo "${NICE} ${IONICE}"
}


# print_separator() - print a horizontal separation line '\u002d' is '-'
function print_separator () {
    printf '\u002d%.s' {1..80}
    printf '\n'
}

# tools_header() - print out common GenWare tools header
function tools_header() {
    local TOOLNAME=$(basename $0)

  # Get timestamp
  #local tstamp=$( date +"%Y-%0m-%0e %H:%M:%S" 2>/dev/null )
    local tstamp=$( date --rfc-3339=ns | cut -c1-23 2>/dev/null )

  # Linux Generic
    local UPTIME=/proc/uptime

  # Get number of online cpus
    local CPUINFO=/proc/cpuinfo
    local online_cpus=$( cat ${CPUINFO} | grep -i ^processor | wc -l 2>/dev/null )

  # Get load average, run-queue size, and number of threads
    local LOADAVG=/proc/loadavg
    local LDAVG=( `cat ${LOADAVG} | sed -e 's#[/]# #g' 2>/dev/null` )

  # Get current architecture
    local arch=$( uname -m )

  # Determine processor name (there are many different formats... *sigh* )
  # - build up info from multiple lines
    local processor='unk'
    local NAME=$( cat ${CPUINFO} | grep \
    -e '^cpu\W\W:' \
    -e ^'cpu model' \
    -e ^'model name' \
    -e ^'system type' \
    -e ^Processor \
    -e ^[Mm]achine | \
    sort -u | awk 'BEGIN{FS=":";} {print $2;}' | \
    tr '\n' ' ' | tr -s [:blank:] 2>/dev/null )
    if [ ! -z "${NAME}" ]; then
        processor=${NAME}
    fi

  # Determine processor speed (abort grep after first match)
    local speed='unk'
    local BOGO=$( cat ${CPUINFO} | grep -m1 -e ^BogoMIPS -e ^bogomips | \
    awk 'BEGIN{FS=":";} {printf "%.1f", $2;}' 2>/dev/null )
    local MHZ=$( cat  ${CPUINFO} | grep -m1 -e ^'cpu MHz' -e ^clock | \
    awk 'BEGIN{FS=":";} {printf "%.1f", $2;}' 2>/dev/null )
    local MHZ2=$( cat ${CPUINFO} | grep -m1 -e ^Cpu0ClkTck -e ^'cycle frequency' | \
    awk 'BEGIN{FS=":";} {printf "%.1f", $2/1.0E6;}' 2>/dev/null )
    if [ ! -z "${MHZ}" ]; then
        speed=${MHZ}
    elif [ ! -z "${MHZ2}" ]; then
        speed=${MHZ2}
    elif [ ! -z ${BOGO} ]; then
        speed=${BOGO}
    fi

  # Determine OS and kernel version
    local os_name=$( uname -s 2>/dev/null )
    local os_release=$( uname -r 2>/dev/null )

    declare -a arr

    local dist_id=""
  # Determine OS distribution ID
    if [ lsb_pres == "yes" ]; then
        arr=( $( lsb_release -i 2>/dev/null ) )
        dist_id=${arr[2]}
    else
        local dist_id=$(cat /etc/centos-release | awk '{print $1}' 2>/dev/null)
    fi

    local dist_rel=""
    if [ lsb_pres == "yes" ]; then
  # Determine OS distribution release
        arr=( $( cat /proc/version | awk '{print $3}' 2>/dev/null ) )
        local dist_rel=${arr[1]}
    else
        local dist_rel=$(cat /etc/centos-release | awk '{print $4}' 2>/dev/null)
    fi
  # Print generic header
    echo "${TOOLNAME} -- ${tstamp}  load average:${LDAVG[0]}, ${LDAVG[1]}, ${LDAVG[2]}  runq:${LDAVG[3]}  nproc:${LDAVG[4]}"
    echo " host:${HOSTNAME}  Distribution:${dist_id} ${dist_rel}  ${os_name} ${os_release}"
    echo " arch:${arch}  processor:${processor} speed:${speed} MHz  CPUs:${online_cpus}"
}




# tools_usage() - show generic tools tool usage
function tools_usage() {
    if [  ${OPT_USE_INTERVALS} -eq 1 ]; then
        echo "usage: ${TOOLNAME} [-f] [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]"
    else
        echo "Usage: ${TOOLNAME} [-f] [-p <period_mins>] [-c <cpulist>] [-h]"
    fi
}

# tools_print_help() - print generic tool help
function tools_print_help() {
    tools_usage
    echo
    echo "Options:";
    echo " -f                    : collect forever                        : default: none"
    echo " -p <period_minutes>   : overall collection period (minutes)    : default: ${DEFAULT_PERIOD_MIN}"
    if [  ${OPT_USE_INTERVALS} -eq 1 ]; then
        echo " -i <interval_seconds> : sample interval (seconds)              : default: ${DEFAULT_INTERVAL_SEC}"
    fi
    echo " -c <cpulist>          : cpu list where tool runs (e.g., 0-1,8) : default: none"
    echo
    if [  ${OPT_USE_INTERVALS} -eq 1 ]; then
        echo "Example: collect 5 minute period, sample every 30 seconds interval"
        echo " ${TOOLNAME} -p 5 -i 30"
    else
        echo "Example: collect 5 minute period"
        echo " ${TOOLNAME} -p 5"
    fi
}

# tools_parse_options() -- parse common options for tools scripts
function tools_parse_options() {
  # check for no arguments, print usage
    if [ $# -eq "0" ]; then
        tools_usage
        tools_cleanup 0
        exit 0
    fi

  # parse the input arguments
    while getopts "fp:i:c:h" Option
    do
    case $Option in
    f)
        OPT_FOREVER=1
        PERIOD_MIN=60
        ;;
    p) PERIOD_MIN=$OPTARG ;;
    i)
        OPT_USE_INTERVALS=1
        INTERVAL_SEC=$OPTARG
        ;;
    c) CPULIST=$OPTARG ;;
    h)
        tools_print_help
        tools_cleanup 0
        exit 0
        ;;
    *)
        tools_usage
        tools_cleanup 0
        exit 0
        ;;
    esac
    done

  # validate input arguments
    PERIOD_MAX=$[4*24*60]
    INTERVAL_MAX=$[60*60]

    error=0
    if [[ ${PERIOD_MIN} -lt 1 || ${PERIOD_MIN} -gt ${PERIOD_MAX} ]]; then
        echo "-p <period_mid> must be > 0 and <= ${PERIOD_MAX}."
        error=1
    fi
    if [[ ${INTERVAL_SEC} -lt 1 || ${INTERVAL_SEC} -gt ${INTERVAL_MAX} ]]; then
        echo "-i <interval> must be > 0 and <= ${INTERVAL_MAX}."
        error=1
    fi
    if [ ${error} -eq 1 ]; then
        tools_cleanup 0
        exit 1
    fi
}
