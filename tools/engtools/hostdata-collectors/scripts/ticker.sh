#!/bin/bash
# Usage:  ticker.sh [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]
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

#-------------------------------------------------------------------------------
# MAIN Program:
#-------------------------------------------------------------------------------
# Parse input options
tools_parse_options "${@}"

# Set affinity of current script
CPULIST=""
set_affinity ${CPULIST}

# Calculate number of sample repeats based on overall interval and sampling interval
((REPEATS = PERIOD_MIN * 60 / INTERVAL_SEC))
((REP_LOG = 10 * 60 / INTERVAL_SEC))

LOG_NOCR "collecting "
t=0
for ((rep=1; rep <= REPEATS ; rep++))
do
    ((t++))
    sleep ${INTERVAL_SEC}
    if [ ${t} -ge ${REP_LOG} ]; then
        t=0
        echo "."
        LOG_NOCR "collecting "
    else
        echo -n "."
    fi
done
echo "."

LOG "done"

# normal program exit
tools_cleanup 0
exit 0
