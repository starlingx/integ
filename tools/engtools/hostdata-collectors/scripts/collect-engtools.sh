#!/bin/bash
# Usage:
#  collect-engtools.sh [-f] [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]

# Define common utility functions
TOOLBIN=$(dirname $0)
. ${TOOLBIN}/engtools_util.sh

# ENABLE DEBUG (0=disable, 1=enable)
OPT_DEBUG=0

# Set options for long soak (vs, shorter collection)
#OPT_SOAK=0 # long soak
OPT_SOAK=1 # few hour soak
#OPT_SOAK=2 # < hour soak

# Define command to set nice + ionice
CMD_IDLE=$( cmd_idle_priority )

# Purge configuration options
# - how much data may be created per cycle
PURGE_HEADROOM_MB=100
# - how much remaining space to leave
PURGE_HEADROOM_PERCENT=15
# - maximum size of data collection
PURGE_MAXUSAGE_MB=1000

# Affine to pinned cores
AFFINE_PINNED=1

# Line-buffer stream output (instead of buffered)
STDBUF="stdbuf -oL"

# Define some common durations
DUR_60MIN_IN_SEC=$[60*60]
DUR_30MIN_IN_SEC=$[30*60]
DUR_15MIN_IN_SEC=$[15*60]
DUR_10MIN_IN_SEC=$[10*60]
DUR_5MIN_IN_SEC=$[5*60]
DUR_1MIN_IN_SEC=$[1*60]

# Global variables
declare -a parallel_outfiles
declare df_size_bytes
declare df_avail_bytes
declare du_used_bytes
declare tgt_avail_bytes
declare tgt_used_bytes

# do_parallel_commands - launch parallel tools with separate output files
function do_parallel_commands()
{
    parallel_outfiles=()
    for elem in "${tlist[@]}"
    do
        tool=""; period=""; repeat=""; interval=""
        my_hash="elem[*]"
        local ${!my_hash}
        if [ ! -z "${name}" ]; then
            fname="${TOOL_DEST_DIR}/${HOSTNAME}_${timestamp}_${name}"
            parallel_outfiles+=( $fname )
            LOG "collecting ${tool}, ${interval} second intervals, to: ${fname}"
            if [ ! -z "${period}" ]; then
                ${STDBUF} ${tool} -p ${period} -i ${interval} > ${fname} 2>/dev/null &
            elif [ ! -z "${repeat}" ]; then
                ${STDBUF} ${tool} --repeat=${repeat} --delay=${interval} > ${fname} 2>/dev/null &
            fi
        else
          # run without file output (eg., ticker)
            ${STDBUF} ${tool} -p ${period} -i ${interval} 2>/dev/null &
        fi
    done
}

# get_current_avail_usage() - get output destination file-system usage and
#                             availability.
#                           - updates: df_size_bytes, df_avail_bytes, du_used_bytes
function get_current_avail_usage()
{
    local -a df_arr_bytes=( $(df -P --block-size=1 ${TOOL_DEST_DIR} | awk 'NR==2 {print $2, $4}') )
    df_size_bytes=${df_arr_bytes[0]}
    df_avail_bytes=${df_arr_bytes[1]}
    du_used_bytes=$(du --block-size=1 ${TOOL_DEST_DIR} | awk 'NR==1 {print $1}')
}

# purge_oldest_files() - remove oldest files based on file-system available space,
#                        and maximum collection size
function purge_oldest_files()
{
  # get current file-system usage
    get_current_avail_usage
    msg=$(printf "avail %d MB, headroom %d MB;  used %d MB, max %d MB" \
        $[$df_avail_bytes/1024/1024] $[$tgt_avail_bytes/1024/1024] \
        $[$du_used_bytes/1024/1024]  $[$tgt_used_bytes/1024/1024])
    LOG "usage: ${msg}"

    if [[ $df_avail_bytes -lt $tgt_avail_bytes ]] || \
        [[ $du_used_bytes  -gt $tgt_used_bytes ]]; then
        # wait for compression to complete
        wait

        get_current_avail_usage
        if [[ $df_avail_bytes -lt $tgt_avail_bytes ]]; then
            msg=$(printf "purge: avail %d MB < target %d MB" \
                $[$df_avail_bytes/1024/1024] $[$tgt_avail_bytes/1024/1024] )
            LOG "purge: ${msg}"
        fi
        if [[ $du_used_bytes  -gt $tgt_used_bytes ]]; then
            msg=$(printf "purge: used %d MB > target %d MB" \
                $[$du_used_bytes/1024/1024] $[$tgt_used_bytes/1024/1024] )
            LOG "purge: ${msg}"
        fi
    else
        return
    fi

  # remove files in oldest time sorted order until we meet usage targets,
  # incrementally updating usage as we remve files
    for file in $( ls -rt ${TOOL_DEST_DIR}/${HOSTNAME}_* 2>/dev/null )
    do
        if [[ $df_avail_bytes -ge $tgt_avail_bytes ]] && \
            [[ $du_used_bytes  -le $tgt_used_bytes ]]; then
            break
        fi

        if [ ${OPT_DEBUG} -eq 1 ]; then
            msg="purge: file=$file"
            if [[ $df_avail_bytes -lt $tgt_avail_bytes ]]; then
                msg="${msg}, < AVAIL"
            fi
            if [[ $du_used_bytes  -gt $tgt_used_bytes ]]; then
                msg="${msg}, > MAXUSAGE"
            fi
            LOG "${msg}"
        fi

        sz_bytes=$(stat --printf="%s" $file)
        ((df_avail_bytes += sz_bytes))
        ((du_used_bytes -= sz_bytes))
        rm -fv ${file}
    done
}

#-------------------------------------------------------------------------------
# MAIN Program:
#-------------------------------------------------------------------------------
# Read configuration variable file if it is present
NAME=collect-engtools.sh
[ -r /etc/default/$NAME ] && . /etc/default/$NAME

# Initialize tool
tools_init

# Parse input options
tools_parse_options "${@}"

# Set affinity of current script
CPULIST=""

# Affine tools to NOVA pinned cores (i.e., non-cpu 0)
# - remove interference with cpu 0
if [ "${AFFINE_PINNED}" -eq 1 ]; then
    NOVA_CONF=/etc/nova/compute_extend.conf
    if [ -f "${NOVA_CONF}" ]; then
    source "${NOVA_CONF}"
    CPULIST=${compute_pinned_cpulist}
    else
    CPULIST=""
    fi
fi
set_affinity ${CPULIST}

# Define output directory
if [[ "${HOSTNAME}" =~ "controller-" ]]; then
    TOOL_DEST_DIR=/scratch/syseng_data/${HOSTNAME}
elif [[ "${HOSTNAME}" =~ "compute-" ]]; then
    TOOL_DEST_DIR=/tmp/syseng_data/${HOSTNAME}
else
    TOOL_DEST_DIR=/tmp/syseng_data/${HOSTNAME}
fi
mkdir -p ${TOOL_DEST_DIR}

# Define daemon log output
timestamp=$( date +"%Y-%0m-%0e_%H%M" )
DAEMON_OUT="${TOOL_DEST_DIR}/${HOSTNAME}_${timestamp}_${TOOLNAME}.log"

# Redirect stdout and append to log if not connected to TTY
if test ! -t 1 ; then
    exec 1>> ${DAEMON_OUT}
fi

# Get current availability and usage
get_current_avail_usage

# Calculate disk usage and availability purge targets
df_offset_bytes=$[$PURGE_HEADROOM_MB*1024*1024]
tgt_used_bytes=$[$PURGE_MAXUSAGE_MB*1024*1024]
((tgt_avail_bytes = df_size_bytes/100*PURGE_HEADROOM_PERCENT + df_offset_bytes))

# Set granularity based on duration
if [ $PERIOD_MIN -le 30 ]; then
    GRAN_MIN=5
else
    GRAN_MIN=60
fi

# Adjust repeats and intervals based on GRAN_MIN granularity
PERIOD_MIN=$[($PERIOD_MIN+(GRAN_MIN-1))/GRAN_MIN*GRAN_MIN]
((REPEATS = PERIOD_MIN/GRAN_MIN))
GRAN_MIN_IN_SEC=$[$GRAN_MIN*60]
if [ ${INTERVAL_SEC} -gt ${GRAN_MIN_IN_SEC} ]; then
    INTERVAL_SEC=${GRAN_MIN_IN_SEC}
fi

# Define tools and options
# [ JGAULD - need config file for customization; long soak vs specific tools ]
# [ Ideally sample < 5 second granularity, but files get big, and tool has cpu overhead ]
# [ Need < 5 second granularity to see cache pressure/flush issues ]
# [ Desire 60 sec interval for soak ]
if [ ${OPT_SOAK} -eq 1 ]; then
    # Desire 60 second or greater interval for longer term data collections,
    # otherwise collection files get too big.
    schedtop_interval=20
    occtop_interval=60
    memtop_interval=60
    netstats_interval=60
    # JGAULD: temporarily increase frequency to 1 min
    postgres_interval=${DUR_1MIN_IN_SEC}
    #postgres_interval=${DUR_15MIN_IN_SEC}
    rabbitmq_interval=${DUR_15MIN_IN_SEC}
    ceph_interval=${DUR_15MIN_IN_SEC}
    diskstats_interval=${DUR_15MIN_IN_SEC}
    memstats_interval=${DUR_15MIN_IN_SEC}
    filestats_interval=${DUR_15MIN_IN_SEC}
elif [ ${OPT_SOAK} -eq 2 ]; then
    # Assume much shorter collection (eg, < hours)
    schedtop_interval=2  # i.e., 2 second interval
    occtop_interval=2    # i.e., 2 second interval
    memtop_interval=1    # i.e., 1 second interval
    netstats_interval=30 # i.e., 30 second interval
    postgres_interval=${DUR_5MIN_IN_SEC}
    rabbitmq_interval=${DUR_5MIN_IN_SEC}
    ceph_interval=${DUR_5MIN_IN_SEC}
    diskstats_interval=${DUR_5MIN_IN_SEC}
    memstats_interval=${DUR_5MIN_IN_SEC}
    filestats_interval=${DUR_5MIN_IN_SEC}
else
    # Assume shorter collection (eg, < a few hours)
    schedtop_interval=5  # i.e., 5 second interval
    occtop_interval=5    # i.e., 5 second interval
    memtop_interval=5    # i.e., 5 second interval
    netstats_interval=30 # i.e., 30 second interval
    postgres_interval=${DUR_5MIN_IN_SEC}
    rabbitmq_interval=${DUR_5MIN_IN_SEC}
    ceph_interval=${DUR_5MIN_IN_SEC}
    diskstats_interval=${DUR_5MIN_IN_SEC}
    memstats_interval=${DUR_5MIN_IN_SEC}
    filestats_interval=${DUR_5MIN_IN_SEC}
fi
schedtop_repeat=$[ $PERIOD_MIN * 60 / $schedtop_interval ]
occtop_repeat=$[ $PERIOD_MIN * 60 / $occtop_interval ]
memtop_repeat=$[ $PERIOD_MIN * 60 / $memtop_interval ]
netstats_repeat=$[ $PERIOD_MIN * 60 / $netstats_interval ]

# Disable use of INTERVAL_SEC sample interval
OPT_USE_INTERVALS=0

# Define parallel engtools configuration
# - tool name, filename, and collection interval attributes
BINDIR=/usr/bin
LBINDIR=/usr/local/bin

. /etc/engtools/engtools.conf

declare -a tlist
if [[ ${ENABLE_STATIC_COLLECTION} == "Y" ]] || [[ ${ENABLE_STATIC_COLLECTION} == "y" ]]; then
    tlist+=( "tool=${LBINDIR}/top.sh name=top period=${PERIOD_MIN} interval=${DUR_1MIN_IN_SEC}" )
    tlist+=( "tool=${LBINDIR}/iostat.sh name=iostat period=${PERIOD_MIN} interval=${DUR_1MIN_IN_SEC}" )
    tlist+=( "tool=${LBINDIR}/netstats.sh name=netstats period=${PERIOD_MIN} interval=${netstats_interval}" )
    tlist+=( "tool=${BINDIR}/occtop name=occtop repeat=${occtop_repeat} interval=${occtop_interval}" )
    tlist+=( "tool=${BINDIR}/memtop name=memtop repeat=${memtop_repeat} interval=${memtop_interval}" )
    tlist+=( "tool=${BINDIR}/schedtop name=schedtop repeat=${schedtop_repeat} interval=${schedtop_interval}" )
    tlist+=( "tool=${LBINDIR}/diskstats.sh name=diskstats period=${PERIOD_MIN} interval=${diskstats_interval}" )
    tlist+=( "tool=${LBINDIR}/memstats.sh name=memstats period=${PERIOD_MIN} interval=${memstats_interval}" )
    tlist+=( "tool=${LBINDIR}/filestats.sh name=filestats period=${PERIOD_MIN} interval=${filestats_interval}" )
    if [[ "${HOSTNAME}" =~ "controller-" ]]; then
        tlist+=( "tool=${LBINDIR}/ceph.sh name=ceph period=${PERIOD_MIN} interval=${ceph_interval}" )
        tlist+=( "tool=${LBINDIR}/postgres.sh name=postgres period=${PERIOD_MIN} interval=${postgres_interval}" )
        tlist+=( "tool=${LBINDIR}/rabbitmq.sh name=rabbitmq period=${PERIOD_MIN} interval=${rabbitmq_interval}" )
    elif [[ "${HOSTNAME}" =~ "compute-" ]]; then
        tlist+=( "tool=${LBINDIR}/vswitch.sh name=vswitch period=${PERIOD_MIN} interval=${DUR_1MIN_IN_SEC}" )
    fi

  # ticker - shows progress on the screen
    tlist+=( "tool=${LBINDIR}/ticker.sh name= period=${PERIOD_MIN} interval=${DUR_1MIN_IN_SEC}" )
fi

if [[ ${ENABLE_LIVE_STREAM} == "Y" ]] || [[ ${ENABLE_LIVE_STREAM} == "y" ]]; then
    ${TOOLBIN}/live_stream.py &
fi

#-------------------------------------------------------------------------------
# Main loop
#-------------------------------------------------------------------------------
OPT_DEBUG=0
REP=0

if [ ${#tlist[@]} -ne 0 ]; then
  # Static stats collection is turned on
    while [[ ${TOOL_USR1_SIGNAL} -eq 0 ]] &&
        [[ ${OPT_FOREVER} -eq 1 || ${REP} -lt ${REPEATS} ]]
    do
        # increment loop counter
        ((REP++))

        # purge oldest files
        purge_oldest_files

        # define filename timestamp
        timestamp=$( date +"%Y-%0m-%0e_%H%M" )

        # collect tools in parallel to separate output files
        LOG "collecting ${TOOLNAME} at ${timestamp} for ${PERIOD_MIN} mins, repeat=${REP}"
        do_parallel_commands
        wait

        # Compress latest increment
        LOG "compressing: ${parallel_outfiles[@]}"
        ${CMD_IDLE} bzip2 -q -f ${parallel_outfiles[@]} 2>/dev/null &
    done

  # Wait for the compression to complete
    wait
    tools_cleanup 0
fi

# Should wait here in case live stats streaming is turned on.
wait

exit 0
