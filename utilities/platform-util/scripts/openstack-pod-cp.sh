#! /bin/bash

#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

CLIENT_IMAGE_NAME="openstack-clients"
NAMESPACE="openstack"
STATE="Running"
MOUNT_PATH="/scratch"
POD_NAME=$(kubectl -n ${NAMESPACE} get pods -o wide 2>&1 |grep ${CLIENT_IMAGE_NAME} |grep ${STATE} |awk '{print $1}')

declare -A levels=([DEBUG]=0 [INFO]=1 [WARN]=2 [ERROR]=3)
script_log_level="ERROR"

log_message() {
    local log_message=$1
    local log_message_priority=$2

    # check if we provide and invalid log level
    if [ -z "${levels[$log_message_priority]}" ]; then
        return 1
    fi

    #check if the log level is above the script log level
    if [ ${levels[$log_message_priority]} -lt ${levels[$script_log_level]} ]; then
        return 2
    fi

    echo "${log_message_priority}: ${log_message}"
}

if [ -z "${POD_NAME}" ]; then
    log_message "No ${CLIENT_IMAGE_NAME} pod found" "ERROR"
    exit 1
fi

if [ "$#" -ne 0 ]; then
    param="$1"
    if [ "${param}" == "-d" ]; then
        MOUNT_PATH="$2"
        log_message "Destination override = ${MOUNT_PATH}" "DEBUG"
        shift
        shift
    fi
fi

if [ "$#" -eq 0 ]; then
    log_message "Invalid number of parameters" "ERROR"
    log_message "Usage: $0 [-d destination] <file_or_directory_path...>" "ERROR"
    exit 1
fi

for file_name in "$@"; do
    if [[ ! -d "$file_name" && ! -f "$file_name" ]]; then
        log_message "Given file \"${file_name}\" not a file or directory" "ERROR"
        exit 1
    fi
done

for file_name in "$@"; do
    log_message "Copying file \"${file_name}\" to pod \"${POD_NAME}\"" "DEBUG"
    kubectl cp "${file_name}" "${NAMESPACE}/${POD_NAME}:${MOUNT_PATH}/"
done

