#! /bin/bash
# Copyright (c) 2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# The script will run everytime before the kubelet service is started.
# (Runs as a "ExecStartPre" action)
#
# It reads the reserved-cpus list for the kubelet from the kubelet
# environment file and sanitizes it on the basis of online CPUs.
#
# If none of the reserved cpus is online, it removes the --reserved-cpus flag
# from the environment file which allows the kubelet to choose CPUs itself
#

ENVIRONMENT_FILE=$1

# Log info message to /var/log/daemon.log
function LOG {
    logger -p daemon.info "$0($$): $@"
}


# Log error message to /var/log/daemon.log
function ERROR {
    logger -s -p daemon.error "$0($$): ERROR: $@"
}

function sanitize_reserved_cpus {
    kubelet_extra_args=$(cat ${ENVIRONMENT_FILE} 2>/dev/null)
    RC=$?
    if [ ${RC} != "0" ]; then
        ERROR "Error reading kubelet extra arguments. Error code: [${RC}]"
        exit ${RC}
    fi

    # Get reserved-cpus comma-separated-values string from environment file and strip double quotes
    # format of kubelet_extra_args is:
    # "KUBELET_EXTRA_ARGS=--cni-bin-dir=/usr/libexec/cni --node-ip=abcd:204::2
    # --system-reserved=memory=9000Mi --reserved-cpus="0-29" --pod-max-pids 10000"
    if [[ ${kubelet_extra_args} =~ --reserved-cpus=\"([0-9,-]+)\" ]]; then
        reserved_cpus=${BASH_REMATCH[1]}
    else
        reserved_cpus=""
    fi
    if test -z "${reserved_cpus}"; then
        LOG "No reserved-cpu list found for kubelet. Nothing to do."
        exit 0
    fi
    LOG "Current reserved-cpus for the kubelet service: ${reserved_cpus}"

    cpus_online=$(cat /sys/devices/system/cpu/online)
    RC=$?
    if [ ${RC} != "0" ]; then
        ERROR "Error reading online CPU list. Error code: [${RC}]"
        exit ${RC}
    fi
    LOG "Online CPUs: ${cpus_online}"

    # Possible formats for reserved_cpus could be
    # 0,2,4,6
    # 0-23,36-45
    # 0-4,6,9,13,23-34
    expanded_reserved_cpus=$(expand_sequence ${reserved_cpus})
    reserved_cpus_array=(${expanded_reserved_cpus//,/ })

    sanitized_reserved_cpus=""
    for element in "${reserved_cpus_array[@]}"; do
        in_list ${element} ${cpus_online}
        if [[ "$?" == "0" ]] ; then
            sanitized_reserved_cpus+=",${element}"
        fi
    done
    # Remove the extra leading ','
    sanitized_reserved_cpus=${sanitized_reserved_cpus#","}
    LOG "Sanitized reserved-cpus list for the kubelet: ${sanitized_reserved_cpus}"

    if test -z "${sanitized_reserved_cpus}"; then
        # Strip out --reserved-cpus option if no reserved-cpus are online
        sed -i "s/ --reserved-cpus=\"${reserved_cpus}\"//g" ${ENVIRONMENT_FILE}
    else
        # Replace existing reserved-cpus with sanitized list
        sed -i "s/--reserved-cpus=\"${reserved_cpus}\"/--reserved-cpus=\"${sanitized_reserved_cpus}\"/g" ${ENVIRONMENT_FILE}
    fi
    RC="$?"
    if [ ${RC} != "0" ]; then
        ERROR "Error updating reserved-cpus list for the kubelet. Error code: [${RC}]"
        exit ${RC}
    fi
    LOG "Successfully updated reserved-cpus list for the kubelet."

}

source /etc/init.d/cpumap_functions.sh

sanitize_reserved_cpus

exit 0
