#!/bin/bash
#
# Copyright (c) 2024-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Minimal cgroup setup for kubelet. Detects cgroup v1 or v2 and
# configures the k8sinfra cgroup hierarchy accordingly.
#
# - v1: Creates k8sinfra directories under each controller mount
# - v2: Creates k8sinfra.slice systemd slice and delegates controllers
#
# NOTE: Cgroup directories are volatile and do not persist reboots.
# Cpuset values are later updated by puppet kubernetes.pp manifest.
#
# Define minimal path
PATH=/bin:/usr/bin:/usr/local/bin

# Log info message to /var/log/daemon.log
function LOG {
    logger -p daemon.info "$0($$): $@"
}

# Log warning message to /var/log/daemon.log
function WARN {
    logger -s -p daemon.warning "$0($$): WARN: $@"
}

# Log error message to /var/log/daemon.log
function ERROR {
    logger -s -p daemon.error "$0($$): ERROR: $@"
}

if [ ${UID} -ne 0 ]; then
    ERROR "Require sudo/root."
    exit 1
fi

# Detect cgroup version
is_cgroup_v2() {
    [ "$(stat -fc %T /sys/fs/cgroup 2>/dev/null)" = "cgroup2fs" ]
}

########################################################################
# CGROUP V2 SETUP
########################################################################

setup_cgroup_v2() {
    local CGROUP_NAME="k8sinfra.slice"
    local CGROUP_PATH="/sys/fs/cgroup/${CGROUP_NAME}"
    local SUBTREE_CONTROL="${CGROUP_PATH}/cgroup.subtree_control"
    local CONTROLLERS="+cpuset +cpu +io +memory +hugetlb +pids"
    local ROOT_SUBTREE="/sys/fs/cgroup/cgroup.subtree_control"
    local RC=0

    sed -i 's|cgroupDriver:.*|cgroupDriver: systemd|' /var/lib/kubelet/config.yaml 2>/dev/null

    # Enable hugetlb in root subtree control before delegating
    if ! grep -q hugetlb "${ROOT_SUBTREE}" 2>/dev/null; then
        LOG "Enabling hugetlb in root subtree control"
        echo "+hugetlb" > "${ROOT_SUBTREE}" 2>/dev/null
        RC=$?
        if [ ${RC} -ne 0 ]; then
            WARN "Failed to enable hugetlb in ${ROOT_SUBTREE}, rc=${RC}"
        fi
    fi

    # Enable cpuset in root subtree control if not already
    if ! grep -q cpuset "${ROOT_SUBTREE}" 2>/dev/null; then
        LOG "Enabling cpuset in root subtree control"
        echo "+cpuset" > "${ROOT_SUBTREE}" 2>/dev/null
    fi

    # Create the k8sinfra cgroup directory if not present.
    if [ ! -d "${CGROUP_PATH}" ]; then
        LOG "Creating cgroup directory: ${CGROUP_PATH}"
        mkdir -p "${CGROUP_PATH}"
        RC=$?
        if [ ${RC} -ne 0 ]; then
            ERROR "Failed to create ${CGROUP_PATH}, rc=${RC}"
            exit ${RC}
        fi
    else
        LOG "Cgroup dir already exists: ${CGROUP_PATH}"
    fi

    # Delegate controllers
    if ! grep -q cpuset "${SUBTREE_CONTROL}" 2>/dev/null; then
        LOG "Delegating controllers to ${CGROUP_NAME}: ${CONTROLLERS}"
        echo "${CONTROLLERS}" > "${SUBTREE_CONTROL}" 2>/dev/null
        RC=$?
        if [ ${RC} -ne 0 ]; then
            ERROR "Failed to delegate controllers to ${SUBTREE_CONTROL}, rc=${RC}"
            exit ${RC}
        fi
    else
        LOG "Controllers already delegated in ${SUBTREE_CONTROL}"
    fi

    LOG "cgroup v2 setup complete for ${CGROUP_NAME}"
    return ${RC}
}

########################################################################
# CGROUP V1 SETUP
########################################################################

create_cgroup_v1() {
    local cg_name=$1
    local cg_nodeset=$2
    local cg_cpuset=$3

    local CGROUP=/sys/fs/cgroup
    local CONTROLLERS_AUTO_DELETED=("pids" "hugetlb")
    local CONTROLLERS_PRESERVED=("cpuset" "memory" "cpu,cpuacct" "systemd")
    local RC=0

    # Ensure auto-deleted cgroups are created every time
    for cnt in ${CONTROLLERS_AUTO_DELETED[@]}; do
        local CGDIR=${CGROUP}/${cnt}/${cg_name}
        if [ -d ${CGDIR} ]; then
            LOG "Nothing to do, already configured: ${CGDIR}."
            continue
        fi
        LOG "Creating: ${CGDIR}"
        mkdir -p ${CGDIR}
        RC=$?
        if [ ${RC} -ne 0 ]; then
            ERROR "Creating: ${CGDIR}, rc=${RC}"
            exit ${RC}
        fi
    done

    # Preserved cgroups — if any exist, skip setup
    for cnt in ${CONTROLLERS_PRESERVED[@]}; do
        local CGDIR=${CGROUP}/${cnt}/${cg_name}
        if [ -d ${CGDIR} ]; then
            LOG "Nothing to do, already configured: ${CGDIR}."
            return ${RC}
        fi
        LOG "Creating: ${CGDIR}"
        mkdir -p ${CGDIR}
        RC=$?
        if [ ${RC} -ne 0 ]; then
            ERROR "Creating: ${CGDIR}, rc=${RC}"
            exit ${RC}
        fi
    done

    # Configure cpuset attributes
    LOG "Configuring cgroup: ${cg_name}, nodeset: ${cg_nodeset}, cpuset: ${cg_cpuset}"
    local CGDIR=${CGROUP}/cpuset/${cg_name}
    local CGMEMS=${CGDIR}/cpuset.mems
    local CGCPUS=${CGDIR}/cpuset.cpus
    local CGTASKS=${CGDIR}/tasks

    # Assign cgroup memory nodeset
    LOG "Assign nodeset ${cg_nodeset} to ${CGMEMS}"
    echo ${cg_nodeset} > ${CGMEMS}
    RC=$?
    if [ ${RC} -ne 0 ]; then
        ERROR "Unable to write to: ${CGMEMS}, rc=${RC}"
        exit ${RC}
    fi

    # Assign cgroup cpuset
    LOG "Assign cpuset ${cg_cpuset} to ${CGCPUS}"
    echo ${cg_cpuset} > ${CGCPUS}
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
# Define an upper limit for the memory consumed by the kubepod cgroups
function set_kubepods_memory_limit {
    local cg_name=$1
    local cg_limit_in_bytes=$2

    local CGATTR="memory.limit_in_bytes"
    local CGDIR="/sys/fs/cgroup/memory/${cg_name}/kubepods"

    if [ ! -d "${CGDIR}" ]; then
        LOG "Creating: ${CGDIR}"
        mkdir -p "${CGDIR}"
        RC=$?
        if [ ${RC} -ne 0 ]; then
            ERROR "Creating: ${CGDIR}, rc=${RC}"
            exit ${RC}
        fi
    fi

    echo ${cg_limit_in_bytes} > ${CGDIR}/${CGATTR}
    RC=$?
    if [ ${RC} -ne 0 ]; then
        ERROR "Setting memory limit for cgroup: ${CGDIR}, Attr: ${CGATTR}, Value: ${cg_limit_in_bytes}, rc=${RC}"
        exit ${RC}
    fi

    LOG "Memory limit set for kubepods cgroup in ${CGDIR}: ${cg_limit_in_bytes}"
    return ${RC}
}

setup_cgroup_v1() {
    # Configure default kubepods cpuset to span all online cpus and nodes.
    ONLINE_NODESET=$(/bin/cat /sys/devices/system/node/online)
    ONLINE_CPUSET=$(/bin/cat /sys/devices/system/cpu/online)

    sed -i 's|cgroupDriver:.*|cgroupDriver: cgroupfs|' /var/lib/kubelet/config.yaml 2>/dev/null

    # Configure kubelet cgroup to match cgroupRoot.
    create_cgroup_v1 'k8sinfra' ${ONLINE_NODESET} ${ONLINE_CPUSET}
    create_cgroup_v1 'k8sinfra_stx' ${ONLINE_NODESET} ${ONLINE_CPUSET}

    # Use the same amount of memory reserved for the system as reference
    SYSTEM_RESERVED_MEMORY_MiB=$(sed -nr 's/.*--system-reserved=memory=([0-9]+)Mi.*/\1/p' /etc/default/kubelet 2>&1)
    RC=$?

    if [[ ${SYSTEM_RESERVED_MEMORY_MiB} =~ ^[0-9]+$ ]]; then
        # Convert to bytes
        SYSTEM_RESERVED_MEMORY_BYTES=$(( SYSTEM_RESERVED_MEMORY_MiB * 1048576 ))

        # Limit memory consumption on kubepods
        set_kubepods_memory_limit 'k8sinfra_stx' ${SYSTEM_RESERVED_MEMORY_BYTES}

    else
        WARN "Unable to extract the value of reserved system memory from kubelet parameters. rc=${RC}:${SYSTEM_RESERVED_MEMORY_BYTES}"
    fi

    LOG "cgroup v1 setup complete"
}

########################################################################
# MAIN
########################################################################
# Update cgroupDriver to match the active cgroup version during
# migration. This handles the window where grub has switched the
# cgroup hierarchy but kubelet config has not yet been updated
# by puppet/kubeadm. Without this, kubelet fails to start on
# the first reboot after cgroup version change.
if is_cgroup_v2; then
    LOG "Detected cgroup v2 (unified hierarchy)"
    setup_cgroup_v2
else
    LOG "Detected cgroup v1 (legacy hierarchy)"
    setup_cgroup_v1
fi

exit $?
