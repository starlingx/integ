#!/bin/sh

#
# Copyright (c) 2017 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# $1 - interface
# $2 - interface type [mgmt, infra]
# $3 - dummy used to determine if we're backgrounded or not

DEV=$1
NETWORKTYPE=$2
NETWORKSPEED=$3

if [ ${NETWORKTYPE} != "mgmt" -a ${NETWORKTYPE} != "infra" ]; then
    exit 0
fi

# We want to be able to wait some time (typically <10 sec) for the
# network link to autonegotiate link speed.  Re-run the script in
# the background so the parent can return right away and init can
# continue.
if [ $# -eq 3 ]
then
    $0 $DEV $NETWORKTYPE $NETWORKSPEED dummy &
    disown
    exit 0
fi

function test_valid_speed
{
    # After the link is enabled but before the autonegotiation is complete
    # the link speed may be read as either -1 or as 4294967295 (which is
    # uint(-1) in twos-complement) depending on the kernel.  Neither one is valid.
    if (( $1 > 0 )) && (( $1 != 4294967295 ))
    then
        return 0
    else
        return 1
    fi
}

function log
{
    # It seems that syslog isn't yet running, so append directly to the syslog file
    echo `date +%FT%T.%3N` `hostname` CGCS_TC_SETUP: $@ >> /var/log/platform.log
}

function infra_exists
{
    if [ -z "$infrastructure_interface" ]
    then
        return 1
    else
        return 0
    fi
}

function is_consolidated
{
    if ! infra_exists
    then
        return 1
    else
       # determine whether the management interface is a parent of the
       # infrastructure interface based on name.
       # eg. this matches enp0s8 to enp0s8.10 but not enp0s88
        if [[ $infrastructure_interface =~ $management_interface[\.][0-9]+$ ]]
        then
            return 0
        fi
        return 1
    fi
}

function is_vlan
{
    if [ -f /proc/net/vlan/$DEV ]
    then
        return 0
    else
        return 1
    fi
}

function is_loopback
{
    # (from include/uapi/linux/if.h)
    IFF_LOOPBACK=$((1<<3))

    # get the interface flags
    FLAGS=`cat /sys/class/net/$DEV/flags`

    if ((($IFF_LOOPBACK & $FLAGS) == 0))
    then
        return 1
    else
        return 0
    fi
}

function setup_tc_port_filter
{
    local PORT=$1
    local PORTMASK=$2
    local FLOWID=$3
    local PROTOCOL=$4

    if [ -z $PROTOCOL ]
    then
        # Apply to TCP and UDP
        tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip dport $PORT $PORTMASK flowid $FLOWID
        tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip sport $PORT $PORTMASK flowid $FLOWID
    else
        # Apply to specific protocol only
        tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip protocol 6 0xff match ip dport $PORT $PORTMASK flowid $FLOWID
        tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip protocol 6 0xff match ip sport $PORT $PORTMASK flowid $FLOWID
    fi
}

function setup_tc_tos_filter
{
    local TOS=$1
    local TOSMASK=$2
    local FLOWID=$3

    tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip tos $TOS $TOSMASK flowid $FLOWID
}

function setup_root_tc
{
    # create new qdiscs, classes and queues
    tc qdisc add dev $DEV root handle 1: htb default 40
    tc class add dev $DEV parent 1: classid 1:1 htb rate ${SPEED}mbit burst 15k quantum 60000
}

function setup_default_tc
{
    local RATE=$1
    local CEIL=$2

    local FLOWQ=40
    local CLASSID=1:$FLOWQ
    local FLOWID=$CLASSID

    # create default qdiscs, classes
    $AC $CLASSID htb rate $((${RATE}*${SPEED}/100))mbit burst 15k ceil $((${CEIL}*${SPEED}/100))mbit prio 4 quantum 60000
    tc qdisc add dev $DEV parent $CLASSID handle $FLOWQ: sfq perturb 10
}

function setup_hiprio_tc
{
    local RATE=$1
    local CEIL=$2

    local FLOWQ=10
    local CLASSID=1:$FLOWQ
    local FLOWID=$CLASSID

    # create high priority qdiscs, classes, and queues
    $AC $CLASSID htb rate $((${RATE}*${SPEED}/100))mbit burst 15k ceil $((${CEIL}*${SPEED}/100))mbit prio 3 quantum 60000
    tc qdisc add dev $DEV parent $CLASSID handle $FLOWQ: sfq perturb 10

    # filter for high priority traffic
    setup_tc_tos_filter 0x10 0xf8 $FLOWID
}

function setup_migration_tc
{
    local RATE=$1
    local CEIL=$2

    local FLOWQ=30
    local CLASSID=1:$FLOWQ
    local FLOWID=$CLASSID

    # create migration qdiscs, classes, and queues
    $AC $CLASSID htb rate $((${RATE}*${SPEED}/100))mbit burst 15k ceil $((${CEIL}*${SPEED}/100))mbit prio 2 quantum 60000
    tc qdisc add dev $DEV parent $CLASSID handle $FLOWQ: sfq perturb 10

    # Migration (TCP, ports 49152-49215)
    setup_tc_port_filter 49152 0xffc0 $FLOWID $TCP

    # Migration via libvirt tunnel (TCP, port 16509)
    setup_tc_port_filter 16509 0xffff $FLOWID $TCP
}

function setup_storage_tc
{
    local RATE=$1
    local CEIL=$2

    local FLOWQ=20
    local CLASSID=1:$FLOWQ
    local FLOWID=$CLASSID

    # create storage qdiscs, classes, and queues
    $AC $CLASSID htb rate $((${RATE}*${SPEED}/100))mbit burst 15k ceil $((${CEIL}*${SPEED}/100))mbit prio 1 quantum 60000
    tc qdisc add dev $DEV parent $CLASSID handle $FLOWQ: sfq perturb 10

    # Storage, NFS (UDP/TCP, port 2049)
    setup_tc_port_filter 2049 0xffff $FLOWID

    # Storage, iSCSI (UDP/TCP, port 3260)
    setup_tc_port_filter 3260 0xffff $FLOWID

    # Storage, CEPH (TCP, ports 6789,6800-7100)
    PORTS=( 6789 6800 6816 6912 7040 7072 7088 )
    PORTMASKS=( 0xffff 0xfff0 0xffa0 0xff80 0xffa0 0xfff0 0xfffa )
    for idx in "${!PORTS[@]}"; do
        PORT=${PORTS[$idx]}
        MASK=${PORTMASKS[$idx]}
        setup_tc_port_filter $PORT $MASK $FLOWID $TCP
    done
}

function setup_drbd_tc
{
    local RATE=$1
    local CEIL=$2

    local FLOWQ=50
    local CLASSID=1:$FLOWQ
    local FLOWID=$CLASSID

    # create DRBD qdiscs, classes and queues
    $AC $CLASSID htb rate $((${RATE}*${SPEED}/100))mbit burst 15k ceil $((${CEIL}*${SPEED}/100))mbit quantum 60000

    tc qdisc add dev $DEV parent $CLASSID handle $FLOWQ: sfq perturb 10

    # DRDB (TCP, ports 7789,7790,7791,7799)
    # port 7793 is used with drdb-extension
    PORTS=( 7789 7790 7791 7792 7799 7793 )
    PORTMASKS=( 0xffff 0xffff 0xffff 0xffff 0xffff )
    for idx in "${!PORTS[@]}"; do
        PORT=${PORTS[$idx]}
        MASK=${PORTMASKS[$idx]}
        setup_tc_port_filter $PORT $MASK $FLOWID $TCP
    done
}

function setup_mgmt_tc_individual
{
    # Configure high priority and default traffic classes.

    setup_root_tc

    # bandwidth percentages
    local HIPRIO_BW=10
    local DEFAULT_BW=10

    # bandwidth ceiling percentages, for borrowing bandwidth.
    # the management interface is not consolidated, so set the ceiling to the
    # maximum rate.
    local HIPRIO_CBW=100
    local DEFAULT_CBW=100

    setup_hiprio_tc $HIPRIO_BW $HIPRIO_CBW
    setup_default_tc $DEFAULT_BW $DEFAULT_CBW
}


function setup_mgmt_tc_vlan
{
    # Configure high priority and default traffic classes.

    setup_root_tc

    # bandwidth percentages
    local HIPRIO_BW=10
    local DEFAULT_BW=10

    # bandwidth ceiling percentages, for borrowing bandwidth.
    # The management interface is a vlan, so reserve bandwidth
    # for sibling infra vlan interfaces.
    local HIPRIO_CBW=20
    local DEFAULT_CBW=20

    setup_hiprio_tc $HIPRIO_BW $HIPRIO_CBW
    setup_default_tc $DEFAULT_BW $DEFAULT_CBW
}

function setup_mgmt_tc_consolidated
{
    # Configure management classes.
    # All traffic coming from the infra will get treated again by the
    # management traffic classes. We need to apply the same TCs as the
    # infra to prevent a management application from starving the
    # upper interface.
    setup_root_tc
    setup_tc_all
}

function setup_mgmt_tc_infra_exists
{
    if is_consolidated
    then
        # Infra over mgmt.  In this case we want to reserve
        # a small portion of the link for management.
        setup_mgmt_tc_consolidated
    else
        # Only setup hiprio and default classes.
        # The infra will handle storage, migration, DRBD.
        if is_vlan
        then
            setup_mgmt_tc_vlan
        else
            setup_mgmt_tc_individual
        fi
    fi
}

function setup_mgmt_tc_no_infra
{
    # Configure traffic classes for a management interface when
    # no infrastructure interface exists.  Configure the full
    # set of TCs.

    setup_root_tc
    setup_tc_all
}

function setup_infra_tc_consolidated
{
    # Configure the full set of traffic classes, but leave a small
    # portion of bandwidth for the management interface.

    # reserve 1% BW for management
    local RESERVED=$((1*${SPEED}/100))
    SPEED=$((${SPEED}-${RESERVED}))

    setup_root_tc
    setup_tc_all
}

function setup_infra_tc_individual
{
    # Configure the full set of traffic classes.

    setup_root_tc
    if is_vlan
    then
        # reserve 1% BW for sibling vlan interfaces
        local RESERVED=$((1*${SPEED}/100))
        SPEED=$((${SPEED}-${RESERVED}))
    fi
    setup_tc_all
}

function setup_tc_all
{
    # bandwidth percentages, in case of over-percentage, bandwidth is divided based
    # on bandwidth ratios
    local MIG_BW=30
    local STOR_BW=50
    local DRBD_BW=80
    local HIPRIO_BW=10
    local DEFAULT_BW=10

    # bandwidth ceiling percentages, for borrowing bandwidth
    local MIG_CBW=100
    local STOR_CBW=100
    local DRBD_CBW=100
    local HIPRIO_CBW=20
    local DEFAULT_CBW=20

    setup_hiprio_tc $HIPRIO_BW $HIPRIO_CBW
    setup_storage_tc $STOR_BW $STOR_CBW
    setup_migration_tc $MIG_BW $MIG_CBW
    setup_default_tc $DEFAULT_BW $DEFAULT_CBW
    if [ $nodetype == "controller" ]
    then
        setup_drbd_tc $DRBD_BW $DRBD_CBW
    fi
}

function get_dev_speed
{
    # If the link doesn't come up we won't go enabled, so here we can
    # afford to wait forever for the link.
    while true
    do
        if [ -e /sys/class/net/$1/bonding ]
        then
            for VAL in `cat /sys/class/net/$1/lower_*/speed`
            do
                if test_valid_speed $VAL
                then
                    log slave for bond link $1 reported speed $VAL
                    echo $VAL
                    return 0
                else
                    log slave for bond link $1 reported invalid speed $VAL
                fi
            done
            log all slaves for bond link $1 reported invalid speeds, will sleep 30 sec and try again
        else
            VAL=`cat /sys/class/net/$1/speed`
            if test_valid_speed $VAL
            then
                log link $1 reported speed $VAL
                echo $VAL
                return 0
            else
                log link $1 returned invalid speed $VAL, will sleep 30 sec and try again
            fi
        fi
        sleep 30
    done
}

function get_speed
{
    local dev=$1
    local networktype=$2
    local net_speed=$NETWORKSPEED
    local dev_speed=$(get_dev_speed $DEV)
    local speed=$dev_speed
    if [ $net_speed != $dev_speed ]
    then
        log WARNING: $dev has a different operational speed [$dev_speed] \
            than configured speed [$net_speed] for network type $networktype
        if test_valid_speed $net_speed
        then
            # Use greater of configured net speed / recorded dev speed
            if [ $net_speed -gt $dev_speed ]
            then
                speed=$net_speed
            fi
        fi
    fi
    log using speed $speed for tc filtering on $dev
    echo $speed
}


if is_loopback
then
    # mgmt/infra uses the loopback for CPE simplex
    exit 0
fi

log running tc setup script for $DEV $NETWORKTYPE in background

if [ -f /etc/platform/platform.conf ]
then
    source /etc/platform/platform.conf
fi

SPEED=$(get_speed $DEV $NETWORKTYPE)

# 1:10 = high priority class
# 1:20 = storage class
# 1:30 = migration class
# 1:40 = default class
# 1:50 = DRBD class

# generic class add preamble
AC="tc class add dev $DEV parent 1:1 classid"

# protocol numbers
TCP=6
UDP=17

# delete existing qdiscs
tc qdisc del dev $DEV root > /dev/null 2>&1

if [ ${NETWORKTYPE} = "mgmt" ]
then
    if infra_exists
    then
        setup_mgmt_tc_infra_exists
    else
        setup_mgmt_tc_no_infra
    fi
else
    if is_consolidated
    then
        setup_infra_tc_consolidated
    else
        setup_infra_tc_individual
    fi
fi
