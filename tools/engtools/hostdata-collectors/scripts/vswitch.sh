#!/bin/bash
# Usage:  vswitch.sh [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]
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

# Print key networking device statistics
function print_vswitch()
{
    print_separator
    TOOL_HIRES_TIME

    cmd='vshell engine-list'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
    cmd='vshell engine-stats-list'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
    cmd='vshell port-list'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
    cmd='vshell port-stats-list'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
    cmd='vshell network-list'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
    cmd='vshell network-stats-list'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
    cmd='vshell interface-list'
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
    cmd='vshell interface-stats-list'
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
    print_vswitch
    sleep ${INTERVAL_SEC}
done
print_vswitch
LOG "done"

# normal program exit
tools_cleanup 0
exit 0
