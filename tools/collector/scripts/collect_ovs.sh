#! /bin/bash
########################################################################
#
# Copyright (c) 2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
########################################################################

# Loads Up Utilities and Commands Variables

source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="ovs"
LOGFILE="${extradir}/${SERVICE}.info"


###############################################################################
# Only Compute Nodes
###############################################################################
if [[ "$nodetype" == "compute" || "$subfunction" == *"compute"* ]] ; then

    if [[ "$vswitch_type" == *ovs* ]]; then
        echo    "${hostname}: OVS Info ..........: ${LOGFILE}"

        delimiter ${LOGFILE} "ovsdb-client dump"
        ovsdb-client dump >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

        delimiter ${LOGFILE} "ovs-vsctl show"
        ovs-vsctl --timeout 10 show >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    fi
fi

exit 0
