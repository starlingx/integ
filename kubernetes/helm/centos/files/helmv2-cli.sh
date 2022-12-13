#!/bin/bash

# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# This script is wrapper to Helm v2 client, providing access to containerized
# armada/tiller managed charts.

# There are two modes of operation:
# - no command specified: this is an interactive BusyBox shell
# - command and options specified: this executes a single helm v2 command

set -euo pipefail

# Define minimal path
PATH=/bin:/usr/bin:/usr/local/bin

# Process input options
SCRIPT=$(basename $0)
OPTS=$(getopt -o dh --long debug,help -n ${SCRIPT} -- "$@")
if [ $? != 0 ]; then
    echo "Failed parsing options." >&2
    exit 1
fi
eval set -- "$OPTS"

DEBUG=false
HELP=false
while true; do
    case "$1" in
        -d | --debug ) DEBUG=true; shift ;;
        -h | --help )  HELP=true; shift ;;
        -- ) shift; break ;;
        * ) break ;;
    esac
done

# Treat remaining arguments as commands + options
shift $((OPTIND-1))
OTHERARGS="$@"

if [ ${HELP} == 'true' ]; then
    echo "Usage: ${SCRIPT} [-d|--debug] [-h|--help] -- [command] [options]"
    echo "Options:"
    echo " -d | --debug : display initialization information"
    echo " -h | --help  : this help"
    echo
    echo "Command option examples:"
    echo " helmv2-cli -- helm search"
    echo " helmv2-cli -- helm list"
    echo " helmv2-cli -- helm list --namespace openstack --pending"
    exit 0
fi

# Logger setup
LOG_FACILITY=user
LOG_PRIORITY=info
function LOG {
    logger -t "${0##*/}[$$]" -p ${LOG_FACILITY}.${LOG_PRIORITY} "$@"
    echo "${0##*/}[$$]" "$@"
}
function ERROR {
    MSG="ERROR"
    echo "${MSG} $@" >&2
    LOG "${MSG} $@"
}

# Determine running armada pods, including list of status conditions
# This jsonpath gives the following output format per pod:
# armada-api-bc77f956d-jwl4n::Initialized=True:Ready=True:ContainersReady=True:PodScheduled=True
JSONPATH='{range .items[*]}{"\n"}{@.metadata.name}:{@.metadata.deletionTimestamp}{range @.status.conditions[*]}{":"}{@.type}={@.status}{end}{end}'
ARMADA_PODS=( $(kubectl get pods -n armada \
                --selector=application=armada,component=api \
                --field-selector status.phase=Running \
                --output=jsonpath="${JSONPATH}") )
if [ ${#ARMADA_PODS[@]} -eq 0 ]; then
    ERROR "Could not find armada pod."
    exit 1
fi
if [ ${DEBUG} == 'true' ]; then
    LOG "Found armada pods: ${ARMADA_PODS[@]}"
fi

# Get first available Running and Ready armada pod, with tiller container we can exec
POD=""
for LINE in "${ARMADA_PODS[@]}"; do
    # match only Ready pods with nil deletionTimestamp
    if [[ $LINE =~ ::.*Ready=True ]]; then
        # extract pod name, it is first element delimited by :
        A=( ${LINE/:/ } )
        P=${A[0]}
    else
        continue
    fi

    kubectl exec -it -n armada ${P} -c tiller -- pwd 1>/dev/null 2>/dev/null
    RC=$?
    if [ ${RC} -eq 0 ]; then
        POD=${P}
        break
    fi
done
if [ -z "${POD}" ]; then
    ERROR "Could not find armada pod."
    exit 1
fi
if [ ${DEBUG} == 'true' ]; then
    LOG "Found armada pod: ${POD}"
fi

# Determine tiller listen port (configured by armada chart)
# armada-api is container index 0, tiller is container index 1
TILLER_PORT=$(kubectl get pod -n armada ${POD} \
                --output=jsonpath={.spec.containers[1].ports[0].containerPort})
if [ -z "${TILLER_PORT}" ]; then
    ERROR "Could not find tiller listen port."
    exit 1
fi
if [ ${DEBUG} == 'true' ]; then
    LOG "Found tiller listen port: ${TILLER_PORT}"
fi

# Launch BusyBox shell with access to local tiller.
# Can execute helm v2 commands as '/helm' or 'helm'.
if [ ${DEBUG} == 'true' ]; then
    LOG "Launching Helm-v2 client"
fi
HELM_HOST=":${TILLER_PORT}"
if [ -z "${OTHERARGS}" ]; then
    # Interactive BusyBox shell
    kubectl exec -it -n armada ${POD} -c tiller -- \
        /bin/sh -c "PATH=${PATH}:/tmp PS1='Helm-v2 \h:\w $ ' HELM_HOST=${HELM_HOST} /bin/sh"
else
    # Execute single helm v2 command in BusyBox shell
    kubectl exec -n armada ${POD} -c tiller -- \
        /bin/sh -c "PATH=${PATH}:/tmp HELM_HOST=${HELM_HOST} /bin/sh -c '$OTHERARGS'"
fi

exit 0
