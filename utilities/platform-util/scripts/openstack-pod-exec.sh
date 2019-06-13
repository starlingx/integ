#!/bin/bash

#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

CLIENT_IMAGE_NAME="openstack-clients"
NAMESPACE="openstack"
STATE="Running"
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
    log_message "No openstackclients pod found" "ERROR"
    exit 1
fi

log_message "Found clients pod: ${POD_NAME}" "DEBUG"

# Pass stdin to the command only if we use a command that
# is expected to be interactive (like opening an openstack
# shell)
# This script should only be accessed through the defined
# aliases, so the first parameter is always passed.
# Depending on the existence of the second parameter, we
# decide if the command in interactive or not:
# Examples:
# - openstack (translates to ./openstack-pod-exec.sh openstack)
#   only has one parameter and is expected to a open an
#   interactive openstack shell
# - openstack endpoint list (translates to ./openstack-pod-exec.sh
#   openstack endpoint list) is expected to run just one command
#   and return the output
# If we had considered all commands as interactive, copying and
# pasting an openstack command followed by any other command
# would have passed all the input after the openstack call as
# input to the pod through "kubectl exec" and not execute the
# commands on the platform side.
if [ -z "$2" ]; then
    exec kubectl exec -ti -n ${NAMESPACE} ${POD_NAME} -- "$@"
else
    exec kubectl exec -t -n ${NAMESPACE} ${POD_NAME} -- "$@"
fi
