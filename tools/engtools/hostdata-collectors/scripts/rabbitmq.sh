#!/bin/bash
# Usage:  rabbitmq.sh [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]
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
#Need this workaround
MQOPT="-n rabbit@localhost"
# Print key networking device statistics
function print_rabbitmq {
    print_separator
    TOOL_HIRES_TIME

  # IMPORTANT:
  # - Difficulty getting rabbitmqctl to work from init.d script;
  #   apparently it requires a psuedo-TTY, which is something you don't have
  #   until post-init.
  # - WORKAROUND: run command using 'sudo', even if you are 'root'

  # Dump various rabbitmq related stats
    MQ_STATUS="rabbitmqctl ${MQOPT} status"
    ${ECHO} "# ${MQ_STATUS}"
    sudo ${MQ_STATUS} | grep -e '{memory' -A30
    ${ECHO}

  # THe following is useful in diagnosing rabbit memory leaks
  # when end-users do not drain their queues (eg, due to RPC timeout issues, etc)
    MQ_QUEUES="rabbitmqctl ${MQOPT} list_queues messages name pid messages_ready messages_unacknowledged memory consumers"
    ${ECHO} "# ${MQ_QUEUES}"
    sudo ${MQ_QUEUES}
    ${ECHO}

    num_queues=$(sudo rabbitmqctl ${MQOPT} list_queues | wc -l); ((num_queues-=2))
    num_bindings=$(sudo rabbitmqctl ${MQOPT} list_bindings | wc -l); ((num_bindings-=2))
    num_exchanges=$(sudo rabbitmqctl ${MQOPT} list_exchanges | wc -l); ((num_exchanges-=2))
    num_connections=$(sudo rabbitmqctl ${MQOPT} list_connections | wc -l); ((num_connections-=2))
    num_channels=$(sudo rabbitmqctl ${MQOPT} list_channels | wc -l); ((num_channels-=2))
    arr=($(sudo rabbitmqctl ${MQOPT} list_queues messages consumers memory | \
            awk '/^[0-9]/ {a+=$1; b+=$2; c+=$3} END {print a, b, c}'))
    messages=${arr[0]}; consumers=${arr[1]}; memory=${arr[2]}
    printf "%6s %8s %9s %11s %8s %8s %9s %10s\n" \
    "queues" "bindings" "exchanges" "connections" "channels" "messages" "consumers" "memory"
    printf "%6d %8d %9d %11d %8d %8d %9d %10d\n" \
    $num_queues $num_bindings $num_exchanges $num_connections $num_channels $messages $consumers $memory
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

for ((rep=1; rep <= REPEATS ; rep++)); do
    print_rabbitmq
    sleep ${INTERVAL_SEC}
done
print_rabbitmq
LOG "done"

# normal program exit
tools_cleanup 0
exit 0
