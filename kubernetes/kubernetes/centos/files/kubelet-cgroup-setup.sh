#!/bin/bash
#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# This script does minimal cgroup setup for kubelet. This creates k8s-infra
# cgroup for a minimal set of resource controllers, and configures cpuset
# attributes to span all online cpus and nodes. This will do nothing if
# the k8s-infra cgroup already exists (i.e., assume already configured).
# NOTE: The creation of directories under /sys/fs/cgroup is volatile, and
# does not persist reboots. The cpuset.mems and cpuset.cpus is later updated
# by puppet kubernetes.pp manifest.
#

# Define minimal path
PATH=/bin:/usr/bin:/usr/local/bin

# Log info message to /var/log/daemon.log
function LOG {
    logger -p daemon.info "$0($$): $@"
}

# Log error message to /var/log/daemon.log
function ERROR {
    logger -s -p daemon.error "$0($$): ERROR: $@"
}

# Create minimal cgroup directories and configure cpuset attributes
function create_cgroup {
    local cg_name=$1
    local cg_nodeset=$2
    local cg_cpuset=$3

    local CGROUP=/sys/fs/cgroup
    local CONTROLLERS=("cpuset" "memory" "cpu,cpuacct" "systemd")
    local cnt=''
    local CGDIR=''
    local RC=0

    # Create the cgroup for required controllers
    for cnt in ${CONTROLLERS[@]}; do
        CGDIR=${CGROUP}/${cnt}/${cg_name}
        if [ -d ${CGDIR} ]; then
            LOG "Nothing to do, already configured: ${CGDIR}."
            exit ${RC}
        fi
        LOG "Creating: ${CGDIR}"
        mkdir -p ${CGDIR}
        RC=$?
        if [ ${RC} -ne 0 ]; then
            ERROR "Creating: ${CGDIR}, rc=${RC}"
            exit ${RC}
        fi
    done

    # Customize cpuset attributes
    LOG "Configuring cgroup: ${cg_name}, nodeset: ${cg_nodeset}, cpuset: ${cg_cpuset}"
    CGDIR=${CGROUP}/cpuset/${cg_name}
    local CGMEMS=${CGDIR}/cpuset.mems
    local CGCPUS=${CGDIR}/cpuset.cpus
    local CGTASKS=${CGDIR}/tasks

    # Assign cgroup memory nodeset
    LOG "Assign nodeset ${cg_nodeset} to ${CGMEMS}"
    /bin/echo ${cg_nodeset} > ${CGMEMS}
    RC=$?
    if [ ${RC} -ne 0 ]; then
        ERROR "Unable to write to: ${CGMEMS}, rc=${RC}"
        exit ${RC}
    fi

    # Assign cgroup cpus
    LOG "Assign cpuset ${cg_cpuset} to ${CGCPUS}"
    /bin/echo ${cg_cpuset} > ${CGCPUS}
    RC=$?
    if [ ${RC} -ne 0 ]; then
        ERROR "Assigning: ${cg_cpuset} to ${CGCPUS}, rc=${RC}"
        exit ${RC}
    fi

    # Set file ownership
    chown root:root ${CGMEMS} ${CGCPUS} ${CGTASKS}
    RC=$?
    if [ ${RC} -ne 0 ]; then
        ERROR "Setting owner for: ${CGMEMS}, ${CGCPUS}, ${CGTASKS}, rc=${RC}"
        exit ${RC}
    fi

    # Set file mode permissions
    chmod 644 ${CGMEMS} ${CGCPUS} ${CGTASKS}
    RC=$?
    if [ ${RC} -ne 0 ]; then
        ERROR "Setting mode for: ${CGMEMS}, ${CGCPUS}, ${CGTASKS}, rc=${RC}"
        exit ${RC}
    fi

    return ${RC}
}

if [ $UID -ne 0 ]; then
    ERROR "Require sudo/root."
    exit 1
fi

# Configure default kubepods cpuset to span all online cpus and nodes.
ONLINE_NODESET=$(/bin/cat /sys/devices/system/node/online)
ONLINE_CPUSET=$(/bin/cat /sys/devices/system/cpu/online)

# Configure kubelet cgroup to match cgroupRoot.
create_cgroup 'k8s-infra' ${ONLINE_NODESET} ${ONLINE_CPUSET}

exit $?

