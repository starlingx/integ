#! /bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables

source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="vswitch"
LOGFILE="${extradir}/${SERVICE}.info"

LIST_COMMANDS=(
    # keep items sorted alphabetically
    "address-list"
    "dvr-mac-list"
    "dvr-subnet-list"
    "engine-list"
    "engine-queue-list"
    "filter-bindings-list"
    "filter-rule-list"
    "flow-group-list"
    "flow-rule-list"
    "igmp-group-list"
    "igmp-interface-list"
    "interface-list"
    "lacp-interface-list"
    "lacp-neighbour-list"
    "lldp-agent-list"
    "lldp-neighbour-list"
    "mld-group-list"
    "mld-interface-list"
    "nat-list"
    "neighbour-list"
    "network-list"
    "network-table-list"
    "openflow-controller-list"
    "openflow-errors-list"
    "ovsdb-manager-list"
    "ovsdb-monitor-list"
    "port-list"
    "route-list"
    "router-list"
    "router-list"
    "snat-list"
    "stream-list"
    "vxlan-endpoint-list"
    "vxlan-ip-endpoint-list"
    "vxlan-peer-list")

STATS_COMMANDS=(
    # keep below items sorted alphabetically
    "arp-stats-list"
    "dvr-stats-list"
    "engine-stats-list"
    "filter-stats-list"
    "flow-cache-stats-list"
    "flow-event-stats-list"
    "flow-switch-stats-list"
    "flow-table-stats-list"
    "icmp-stats-list"
    "igmp-stats-list"
    "interface-stats-list"
    "ip-stats-list"
    "ip-stats-list-errors"
    "lacp-stats-list"
    "lldp-stats-list"
    "memory-stats-list"
    "mld-stats-list"
    "nat-stats-list"
    "ndp-stats-list"
    "network-stats-list"
    "openflow-stats-list"
    "port-queue-stats-list"
    "port-rate-list"
    "port-stats-list"
    "snat-stats-list"
    "udp-stats-list"
    "vxlan-endpoint-stats-list")

###############################################################################
# Only Compute Nodes
###############################################################################
if [[ "$nodetype" == "compute" || "$subfunction" == *"compute"* ]] ; then

    echo    "${hostname}: AVS Info ..........: ${LOGFILE}"

    for COMMAND in ${LIST_COMMANDS[@]}; do
        delimiter ${LOGFILE} "vshell ${COMMAND}"
        vshell ${COMMAND} --expanded >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    done

    for COMMAND in ${STATS_COMMANDS[@]}; do
        delimiter ${LOGFILE} "vshell ${COMMAND}"
        vshell ${COMMAND} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    done

    if [[ "$sdn_enabled" == "yes" ]] ; then
        delimiter ${LOGFILE} "ovsdb-client dump"
        ovsdb-client dump >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    fi
fi

exit 0
