#!/bin/bash
# Copyright (c) 2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# This script is intended to be run during platform upgrade.
# It removes below feature gates from kube-apiserver configmap and rewrites
# kube-api-server and kube-controller-manager manifests
#  - SCTPSupport=true
#  - HugePageStorageMediumSize=true
#  - TTLAfterFinished=true
#
#
# Background:
# HugePageStorageMediumSize is deprecated in Kubernetes 1.22
# SCTPSupport blocks kube-apiserver pod to spawn after control-plane upgrade
# TTLAfterFinished value defaults to true from k8s 1.21
#

KUBEADM_CONFIGMAP_TMPFILE='/tmp/kubeadm_cm'

rc_controller_manager=0
rc_apiserver=0

function log {
    logger -p local1.info "$1"
}

function get_kubeadm_configmap {

    log "Retrieving kubeadm configmap to temporary location: ${KUBEADM_CONFIGMAP_TMPFILE}"
    counter=0
    RC=0
    RETRIES=10
    until  [ ${counter} -gt ${RETRIES} ]; do
        kubectl --kubeconfig=/etc/kubernetes/admin.conf -n kube-system get \
            configmap kubeadm-config -o "$1" > ${KUBEADM_CONFIGMAP_TMPFILE}
        RC=$?
        if [ 0 == ${RC} ] ; then
            log "Kubeadm configmap retrieved."
            break
        fi
        log "Error retrieving kubeadm configmap, retrying..."
        sleep 5
        counter=$(( counter+1 ))
    done

    if [ ${counter} -gt ${RETRIES} ]; then
        log "Failed to retrieve kubeadm configmap with error code [${RC}]".
        exit ${RC}
    fi
}

# Update the configmap for kubeadm
function update_kubeadm_configmap {

    get_kubeadm_configmap yaml

    log "Updating kube-apiserver feature-gates in retrieved kubeadm-config"

    # Update api-server feature-gates
    sed -i \
    's/^\( *\)feature-gates:\s.*RemoveSelfLink=false/\1feature-gates: RemoveSelfLink=false/g' \
    ${KUBEADM_CONFIGMAP_TMPFILE}
    rc_apiserver=$?
    if [ 0 == ${rc_apiserver} ]; then
        log "Successfully updated kube-apiserver feature-gates in retrieved kubeadm-config"
    else
        log "Failed to update kube-apiserver feature-gates in retrieved kubeadm-config with error code: [${rc_apiserver}]"
    fi

    # update controller-manager feature-gates
    sed -i \
    '/feature-gates: TTLAfterFinished=true/d' ${KUBEADM_CONFIGMAP_TMPFILE}
    rc_controller_manager=$?
    if [ 0 == ${rc_controller_manager} ]; then
        log "Successfully updated controller-manager feature-gates in retrieved kubeadm-config"
    else
        # we need not gracefully exit here as failing to update this does not
        # make any difference to the k8s cluster functions as default value of
        # TTLAfterFinished is true
        log "Failed to update controller-manager feature-gates in retrieved kubeadm-config with error code: [${rc_controller_manager}]"
    fi

    if [ ${rc_controller_manager} ] || [ ${rc_apiserver} ]; then
        if kubectl --kubeconfig=/etc/kubernetes/admin.conf replace -f \
        ${KUBEADM_CONFIGMAP_TMPFILE}; then
            log 'Successfully replaced updated kubeadm configmap.'
        else
            RC=$?
            log "Failed to replace updated kubeadm configmap with error code: [${RC}]"
            rm -f ${KUBEADM_CONFIGMAP_TMPFILE}
            exit ${RC}
        fi
    else
        log "Failed to update ${KUBEADM_CONFIGMAP_TMPFILE}"
        rm -f ${KUBEADM_CONFIGMAP_TMPFILE}
        exit ${RC}
    fi

}

function update_manifests {

    get_kubeadm_configmap jsonpath='{.data.ClusterConfiguration}'

    # Rewrite apiserver manifest only if it is updated in the configmap
    if [ 0 == ${rc_apiserver} ]; then
        kubeadm init phase control-plane apiserver \
            --config ${KUBEADM_CONFIGMAP_TMPFILE}
        RC=$?
        if [ 0 == ${RC} ]; then
            log "Success executing kubeadm init phase control-plane for kube-api-server"
        else
            log "Failed to update kube-api-server manifest with error code: [${RC}]"
            rm -f ${KUBEADM_CONFIGMAP_TMPFILE}
            exit ${RC}
        fi
    fi

    # Rewrite controller-manager manifest only if it is updated in the configmap
    if [ 0 == ${rc_controller_manager} ]; then
        kubeadm init phase control-plane controller-manager \
            --config ${KUBEADM_CONFIGMAP_TMPFILE}
        RC=$?
        if [ 0 == ${RC} ]; then
            log "Success executing kubeadm init phase control-plane for kube-controller-manager"
        else
            log "Failed to update kube-controller-manager manifest with error code: [${RC}]"
            rm -f ${KUBEADM_CONFIGMAP_TMPFILE}
            exit ${RC}
        fi
    fi

}

update_kubeadm_configmap
update_manifests

rm -f ${KUBEADM_CONFIGMAP_TMPFILE}

exit 0
