#! /bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables
source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

function is_service_active {
    active=`sm-query service rabbit-fs | grep "enabled-active"`
    if [ -z "$active" ] ; then
        return 0
    else
        return 1
    fi
}

SERVICE="openstack"
LOGFILE="${extradir}/${SERVICE}.info"
echo    "${hostname}: Openstack Info ....: ${LOGFILE}"

###############################################################################
# Only Controller
###############################################################################
if [ "$nodetype" = "controller" ] ; then

    is_service_active
    if [ "$?" = "0" ] ; then
        exit 0
    fi

delimiter ${LOGFILE} "openstack project list"
openstack project list >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "openstack user list"
openstack user list >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

MQ_STATUS="rabbitmqctl status"
delimiter ${LOGFILE} "${MQ_STATUS} | grep -e '{memory' -A30"
${MQ_STATUS} 2>/dev/null | grep -e '{memory' -A30 >> ${LOGFILE}

delimiter ${LOGFILE} "RabbitMQ Queue Info"
num_queues=$(rabbitmqctl list_queues | wc -l); ((num_queues-=2))
num_bindings=$(rabbitmqctl list_bindings | wc -l); ((num_bindings-=2))
num_exchanges=$(rabbitmqctl list_exchanges | wc -l); ((num_exchanges-=2))
num_connections=$(rabbitmqctl list_connections | wc -l); ((num_connections-=2))
num_channels=$(rabbitmqctl list_channels | wc -l); ((num_channels-=2))
arr=($(rabbitmqctl list_queues messages consumers memory | \
    awk '/^[0-9]/ {a+=$1; b+=$2; c+=$3} END {print a, b, c}'))
messages=${arr[0]}; consumers=${arr[1]}; memory=${arr[2]}
printf "%6s %8s %9s %11s %8s %8s %9s %10s\n" "queues" "bindings" "exchanges" "connections" "channels" "messages" "consumers" "memory" >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
printf "%6d %8d %9d %11d %8d %8d %9d %10d\n" $num_queues $num_bindings $num_exchanges $num_connections $num_channels $messages $consumers $memory >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

    if [ -e /opt/cgcs/ceilometer/pipeline.yaml ] ; then
        cp /opt/cgcs/ceilometer/pipeline.yaml ${extradir}/ceilometer_pipeline.yaml
    fi
fi



###############################################################################
# collect does not retrieve /etc/keystone dir
# Additional logic included to copy /etc/keystone directory
###############################################################################

mkdir -p  ${extradir}/../../etc/
cp -R /etc/keystone/ ${extradir}/../../etc
chmod -R 755 ${extradir}/../../etc/keystone

exit 0
