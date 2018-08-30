#!/bin/bash
# Usage:  memstats.sh [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]
TOOLBIN=$(dirname $0)

# Initialize tools environment variables, and define common utility functions
. ${TOOLBIN}/engtools_util.sh
tools_init
if [ $? -ne 0 ]; then
    echo "FATAL, tools_init - could not setup environment"
    exit $?
fi

PAGE_SIZE=$(getconf PAGE_SIZE)

# Enable use of INTERVAL_SEC sample interval
OPT_USE_INTERVALS=1

# Print key networking device statistics
function print_memory()
{
  # Configuration for netcmds
    MEMINFO=/proc/meminfo
    NODEINFO=/sys/devices/system/node/node?/meminfo
    BUDDYINFO=/proc/buddyinfo
    SLABINFO=/proc/slabinfo

    print_separator
    TOOL_HIRES_TIME

    ${ECHO} "# ${MEMINFO}"
    ${CAT} ${MEMINFO}
    ${ECHO}

    ${ECHO} "# ${NODEINFO}"
    ${CAT} ${NODEINFO}
    ${ECHO}

    ${ECHO} "# ${BUDDYINFO}"
    ${CAT} ${BUDDYINFO}
    ${ECHO}

    ${ECHO} "# PSS"
    cat /proc/*/smaps 2>/dev/null | \
    awk '/^Pss:/ {a += $2;} END {printf "%d MiB\n", a/1024.0;}'
    ${ECHO}

  # use old slabinfo format (i.e. slub not enabled in kernel)
    ${ECHO} "# ${SLABINFO}"
    ${CAT} ${SLABINFO} | \
    awk -v page_size_B=${PAGE_SIZE} '
BEGIN {page_KiB = page_size_B/1024; TOT_KiB = 0;}
(NF == 17) {
    gsub(/[<>]/, "");
    printf("%-22s %11s %8s %8s %10s %12s %1s %5s %10s %12s %1s %12s %9s %11s %8s\n",
    $2, $3, $4, $5, $6, $7, $8, $10, $11, $12, $13, $15, $16, $17, "KiB");
}
(NF == 16) {
    num_objs=$3; obj_per_slab=$5; pages_per_slab=$6;
    KiB = (obj_per_slab > 0) ? page_KiB*num_objs/obj_per_slab*pages_per_slab : 0;
    TOT_KiB += KiB;
    printf("%-22s %11d %8d %8d %10d %12d %1s %5d %10d %12d %1s %12d %9d %11d %8d\n",
    $1, $2, $3, $4, $5, $6, $7, $9, $10, $11, $12, $14, $15, $16, KiB);
}
END {
    printf("%-22s %11s %8s %8s %10s %12s %1s %5s %10s %12s %1s %12s %9s %11s %8d\n",
    "TOTAL", "-", "-", "-", "-", "-", ":", "-", "-", "-", ":", "-", "-", "-", TOT_KiB);
}
' 2>/dev/null
    ${ECHO}

    ${ECHO} "# disk usage: rootfs, tmpfs"
    cmd='df -h -H -T --local -t rootfs -t tmpfs'
    ${ECHO} "Disk space usage rootfs,tmpfs (SI):"
    ${ECHO} "${cmd}"
    ${cmd}
    ${ECHO}

    CMD='ps -e -o ppid,pid,nlwp,rss:10,vsz:10,cmd --sort=-rss'
    ${ECHO} "# ${CMD}"
    ${CMD}
    ${ECHO}
}

#-------------------------------------------------------------------------------
# MAIN Program:
#-------------------------------------------------------------------------------
# Parse input options
tools_parse_options "${@}"

# Set affinity of current script
CPULIST=""
set_affinity ${CPULIST}

LOG "collecting ${TOOLNAME} for ${PERIOD_MIN} minutes, with ${INTERVAL_SEC} second sample intervals."

# Print tools generic tools header
tools_header

# Calculate number of sample repeats based on overall interval and sampling interval
((REPEATS = PERIOD_MIN * 60 / INTERVAL_SEC))

for ((rep=1; rep <= REPEATS ; rep++))
do
    print_memory
    sleep ${INTERVAL_SEC}
done
print_memory
LOG "done"

# normal program exit
tools_cleanup 0
exit 0
