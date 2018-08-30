#!/bin/bash
# Purpose:
#   Some of the engtools scripts are not shutting down gracefully.

# Define common utility functions
TOOLBIN=$(dirname $0)
. ${TOOLBIN}/engtools_util.sh
if [ $UID -ne 0 ]; then
    ERRLOG "Require sudo/root access."
    exit 1
fi

declare -a TOOLS
TOOLS=()
TOOLS+=('collect-engtools.sh')
TOOLS+=('ceph.sh')
TOOLS+=('diskstats.sh')
TOOLS+=('iostat.sh')
TOOLS+=('rabbitmq.sh')
TOOLS+=('ticker.sh')
TOOLS+=('top.sh')
TOOLS+=('memstats.sh')
TOOLS+=('netstats.sh')
TOOLS+=('postgres.sh')
TOOLS+=('vswitch.sh')
TOOLS+=('filestats.sh')
TOOLS+=('live_stream.py')

LOG "Cleanup engtools:"

# Brute force methods (assume trouble with: service collect-engtools.sh stop)
# ( be sure not to clobber /etc/init.d/collect-engtools.sh )
LOG "kill processes brute force"
pids=( $(pidof -x /usr/local/bin/collect-engtools.sh) )
if [ ${#pids[@]} -ne 0 ]
then
    LOG "killing: ${pids[@]}"
    for pid in ${pids[@]}
    do
    LOG "kill: [ ${pid} ] "
    pkill -KILL -P ${pid}
    kill -9 ${pid}
    done
    pkill -KILL iostat
    pkill -KILL top
else
    LOG "no pids found"
fi

LOG "remove pidfiles"
for TOOL in "${TOOLS[@]}"
do
    rm -f -v /var/run/${TOOL}.pid
done
LOG "done"

exit 0
