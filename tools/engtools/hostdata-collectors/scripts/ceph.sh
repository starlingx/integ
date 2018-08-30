#!/bin/bash
# Usage:  ceph.sh [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]
TOOLBIN=$(dirname $0)

# Initialize tools environment variables, and define common utility functions
. ${TOOLBIN}/engtools_util.sh
tools_init
if [ $? -ne 0 ]; then
    echo "FATAL, tools_init - could not setup environment"
    exit $?
fi

# Enable use of INTERVAL_SEC sample interval
OPT_USE_INTERVALS=1

# Print key ceph statistics
function print_ceph()
{
    print_separator
    TOOL_HIRES_TIME

    cmd='ceph -s'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}

    cmd='ceph osd tree'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}

    cmd='ceph df detail'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
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
    print_ceph
    sleep ${INTERVAL_SEC}
done
print_ceph
LOG "done"

# normal program exit
tools_cleanup 0
exit 0
