#! /bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables
source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

SERVICE="tc"
LOGFILE="${extradir}/tc.info"
echo    "${hostname}: Traffic Controls . : ${LOGFILE}"

###############################################################################
# Interface Info
###############################################################################
delimiter ${LOGFILE} "cat /etc/network/interfaces"
if [ -f /etc/network/interfaces ]; then
    cat /etc/network/interfaces >> ${LOGFILE}
else
    echo "/etc/network/interfaces NOT FOUND" >> ${LOGFILE}
fi

delimiter ${LOGFILE} "ip link"
ip link >> ${LOGFILE}

for i in $(ip link | grep mtu | grep eth |awk '{print $2}' | sed 's#:##g'); do

    delimiter ${LOGFILE} "ethtool ${i}"
    ethtool ${i} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

    delimiter ${LOGFILE} "cat /sys/class/net/${i}/speed"
    cat /sys/class/net/${i}/speed >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

    delimiter ${LOGFILE} "ethtool -S ${i}"
    ethtool -S ${i} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
done

###############################################################################
# TC Configuration Script (/usr/local/bin/cgcs_tc_setup.sh)
###############################################################################
delimiter ${LOGFILE} "cat /usr/local/bin/cgcs_tc_setup.sh"
if [ -f /usr/local/bin/cgcs_tc_setup.sh ]; then
    cat /usr/local/bin/cgcs_tc_setup.sh >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
else
    echo "/usr/local/bin/cgcs_tc_setup.sh NOT FOUND" >> ${LOGFILE}
fi

###############################################################################
# TC Configuration
###############################################################################
delimiter ${LOGFILE} "tc qdisc show"
tc qdisc show >> ${LOGFILE}

for i in $(ip link | grep htb | awk '{print $2}' | sed 's#:##g'); do

    delimiter ${LOGFILE} "tc class show dev ${i}"
    tc class show dev ${i} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

    delimiter ${LOGFILE} "tc filter show dev ${i}"
    tc filter show dev ${i} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
done

###############################################################################
# TC Statistics
###############################################################################
delimiter ${LOGFILE} "tc -s qdisc show"
tc -s qdisc show >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

for i in $(ip link | grep htb | awk '{print $2}' | sed 's#:##g'); do

    delimiter ${LOGFILE} "tc -s class show dev ${i}"
    tc -s class show dev ${i} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

    delimiter ${LOGFILE} "tc -s filter show dev ${i}"
    tc -s filter show dev ${i} >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
done

exit 0
