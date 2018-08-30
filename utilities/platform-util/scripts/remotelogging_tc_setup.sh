#!/bin/sh

#
# Copyright (c) 2017 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# $1 - listening port of remote log server
PORT=$1

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

function log
{
    # It seems that syslog isn't yet running, so append directly to the syslog file
    echo `date +%FT%T.%3N` `hostname` CGCS_TC_SETUP: $@ >> /var/log/platform.log
}

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

if [ -f /etc/platform/platform.conf ]
then
    source /etc/platform/platform.conf
else
    exit 0
fi

# bandwitdh percentages, in case of over-percentage, bandwidth is divided based
# on bandwidth ratios
DEFAULT_BW=10
LOG_BW=9

# bandwitdh ceiling percentages, for borrowing bandwidth
DEFAULT_CBW=20
LOG_CBW=20

# 1:40 = default class from cgcs_tc_setup.sh
# 1:60 = LOG class

if [ $nodetype == "controller" ]
then
    # Add class and filters to the oam interface
    DEV=$oam_interface
    SPEED=$(get_dev_speed $DEV)

    # delete existing qdiscs
    tc qdisc del dev $DEV root > /dev/null 2>&1

    # create new qdiscs, classes and LOG filters
    tc qdisc add dev $DEV root handle 1: htb default 40
    tc class add dev $DEV parent 1: classid 1:1 htb rate ${SPEED}mbit burst 15k quantum 60000

    AC="tc class add dev $DEV parent 1:1 classid"
    $AC 1:40 htb rate $((${DEFAULT_BW}*${SPEED}/100))mbit burst 15k ceil $((${DEFAULT_CBW}*${SPEED}/100))mbit quantum 60000
    $AC 1:60 htb rate $((${LOG_BW}*${SPEED}/100))mbit burst 15k ceil $((${LOG_CBW}*${SPEED}/100))mbit quantum 60000

    tc qdisc add dev $DEV parent 1:40 handle 40: sfq perturb 10
    tc qdisc add dev $DEV parent 1:60 handle 60: sfq perturb 10

    tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip dport ${PORT} 0xffff flowid 1:60
    tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip sport ${PORT} 0xffff flowid 1:60

fi

# On all node types, add LOG class 1:60 and filters to the mgmt interface
DEV=$management_interface

if is_loopback
then
    # mgmt/infra uses the loopback for CPE simplex
    exit 0
fi

SPEED=$(get_dev_speed $DEV)

AC="tc class add dev $DEV parent 1:1 classid"
$AC 1:60 htb rate $((${LOG_BW}*${SPEED}/100))mbit burst 15k ceil $((${LOG_CBW}*${SPEED}/100))mbit quantum 60000

tc qdisc add dev $DEV parent 1:60 handle 60: sfq perturb 10

tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip dport ${PORT} 0xffff flowid 1:60
tc filter add dev $DEV protocol ip parent 1:0 prio 1 u32 match ip sport ${PORT} 0xffff flowid 1:60
