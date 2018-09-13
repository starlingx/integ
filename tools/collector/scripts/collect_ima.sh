#! /bin/bash
#
# Copyright (c) 2017 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Loads Up Utilities and Commands Variables
source /usr/local/sbin/collect_parms
source /usr/local/sbin/collect_utils

function is_extended_profile {
    if [ ! -n "${security_profile}" ] || [ "${security_profile}" != "extended" ]; then
        return 0
    else
        return 1
    fi
}

SERVICE="ima"
LOGFILE="${extradir}/${SERVICE}.info"

###############################################################################
# All Node Types
###############################################################################

is_extended_profile
if [ "$?" = "0" ] ; then
    exit 0
fi

echo "${hostname}: IMA Info ..........: ${LOGFILE}"

delimiter ${LOGFILE} "IMA Kernel Modules"
lsmod | grep ima  >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "Auditd status"
service auditd status >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
ps -aux | grep audit >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}

mkdir -p ${extradir}/integrity 2>>${COLLECT_ERROR_LOG}

delimiter ${LOGFILE} "IMA Runtime Measurement and Violations cache"
if [ -d "/sys/kernel/security/ima" ]; then
    ls /sys/kernel/security/ima >> ${LOGFILE} 2>>${COLLECT_ERROR_LOG}
    cp -rf /sys/kernel/security/ima ${extradir}/integrity 2>>${COLLECT_ERROR_LOG}
else
    echo "ERROR: IMA Securityfs directory does not exist!" >> ${LOGFILE}
fi

cp -rf /etc/modprobe.d/ima.conf ${extradir}/integrity 2>>${COLLECT_ERROR_LOG}
cp -rf /etc/modprobe.d/integrity.conf ${extradir}/integrity 2>>${COLLECT_ERROR_LOG}
cp -rf /etc/ima.policy ${extradir}/integrity 2>>${COLLECT_ERROR_LOG}

# make sure all these collected files are world readible
chmod -R 755 ${extradir}/integrity

exit 0
