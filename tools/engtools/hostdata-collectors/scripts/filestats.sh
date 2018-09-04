#!/bin/bash
# Usage:  filestats.sh [-p <period_mins>] [-i <interval_seconds>] [-c <cpulist>] [-h]
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


function print_files {
    print_separator
    TOOL_HIRES_TIME

    ${ECHO} "# ls -l /proc/*/fd"
    sudo ls -l /proc/*/fd 2>/dev/null | awk \
        '$11 ~ /socket/ {a += 1} ; \
        $11 ~ /null/ {b += 1} ; \
        {c += 1} \
        END {\
            {printf "%-10s %-10s %-10s %-10s\n", "TOTAL", "FILES", "SOCKETS", "NULL PIPES"} \
            {printf "%-10s %-10s %-10s %-10s\n", c, c-(a+b) , a, b}}'

    ${ECHO}

    ${ECHO} "# lsof"
    printf "%-7s %-7s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %s\n" "PID" "TOTAL" "FD" "U" "W" "R" "CWD" "RTD" "TXT" "MEM" "DEL" "TCP" "CMD"
    sudo lsof +c 15| awk '$3 !~ /^[0-9]+/{ {pids[$2]["COMMAND"]=$1}\
                {pids[$2]["PID"]=$2}\
                {pids[$2]["TOTAL"]+=1}\
                {pids[$2]["TCP"]+=($8=="TCP")? 1 : 0}\
                {($4 ~ /^[0-9][0-9]*[urw]/ )? \
                    pids[$2][substr($4, length($4),1)]+=1 : pids[$2][$4]+=1} }
                END {
                    { for (i in pids)  \
                        if(pids[i]["PID"]!="PID") {
                            {printf "%-7s %-7s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %s\n", \
                                pids[i]["PID"], \
                                pids[i]["TOTAL"],\
                                ((pids[i]["u"]!="")? pids[i]["u"] : 0) +  ((pids[i]["w"]!="")? pids[i]["w"] : 0 )+ ((pids[i]["r"]!="")? pids[i]["r"] : 0),\
                                (pids[i]["u"]!="")? pids[i]["u"] : 0,\
                                (pids[i]["w"]!="")? pids[i]["w"] : 0,\
                                (pids[i]["r"]!="")? pids[i]["r"] : 0,\
                                (pids[i]["cwd"]!="")? pids[i]["cwd"] : 0,\
                                (pids[i]["rtd"]!="")? pids[i]["rtd"] : 0,\
                                (pids[i]["txt"]!="")? pids[i]["txt"] : 0,\
                                (pids[i]["mem"]!="")? pids[i]["mem"] : 0,\
                                (pids[i]["DEL"]!="")?  pids[i]["DEL"] : 0,\
                                (pids[i]["TCP"]!="")?  pids[i]["TCP"] : 0,\
                                pids[i]["COMMAND"]} }}}' | sort -n -r -k3

    ${ECHO}

    ${ECHO} "# lsof -nP +L1"
    sudo lsof -nP +L1
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
    print_files
    sleep ${INTERVAL_SEC}
done
print_files
LOG "done"

# normal program exit
tools_cleanup 0
exit 0
