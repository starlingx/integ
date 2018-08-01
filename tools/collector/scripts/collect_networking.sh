#! /bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables

source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="networking"
LOGFILE="${extradir}/${SERVICE}.info"
echo    "${hostname}: Networking Info ...: ${LOGFILE}"

###############################################################################
# All nodes
###############################################################################
delimiter ${LOGFILE} "ip -s link"
ip -s link >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "ip -s addr"
ip -s addr >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "ip -s neigh"
ip -s neigh >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "ip rule"
ip rule >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "ip route"
ip route >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "iptables -L -v -x -n"
iptables -L -v -x -n >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "iptables -L -v -x -n -t nat"
iptables -L -v -x -n -t nat >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "iptables -L -v -x -n -t mangle"
iptables -L -v -x -n -t mangle >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}


###############################################################################
# Only Compute
###############################################################################
if [[ "$nodetype" = "compute" || "$subfunction" == *"compute"* ]] ; then
    NAMESPACES=($(ip netns))
    for NS in ${NAMESPACES[@]}; do
        delimiter ${LOGFILE} "${NS}"
        ip netns exec ${NS} ip -s link
        ip netns exec ${NS} ip -s addr
        ip netns exec ${NS} ip -s neigh
        ip netns exec ${NS} ip route
        ip netns exec ${NS} ip rule
    done >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
fi

exit 0
