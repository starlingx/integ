#!/bin/bash
# Copyright (c) 2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# This will run for every k8s upgrade as a part of the control-plane upgrade of the first master.
# - updates kubeadm-config configmap to configure kube-apiserver manifest with RemoveSelfLink=false.
# - generates a kubelet config override file to configure cgroupDriver=cgroupfs.
#   This is consumed by kubeadm upgrade apply
#
# Background:
# Kubernetes 1.21 changed cgroupDriver default to systemd (was cgroupfs).
# Kubernetes 1.20 changed feature-gates RemoveSelfLink default to true.


KUBEADM_CONFIGMAP_TMPFILE='/tmp/kubeadm_cm.yaml'

function log {
    logger -p local1.info "$1"
}

# Update the configmap for kubeadm
function update_apiserver_configmap {

    log "Retrieving kubeadm configmap to temporary location: ${KUBEADM_CONFIGMAP_TMPFILE}"
    counter=0
    RC=0
    RETRIES=10
    until  [ $counter -gt $RETRIES ]; do
        kubectl --kubeconfig=/etc/kubernetes/admin.conf -n kube-system get \
            configmap kubeadm-config -o yaml > ${KUBEADM_CONFIGMAP_TMPFILE}
        RC=$?
        if [ "$RC" = "0" ] ; then
            log "Kubeadm configmap retrieved."
            break
        fi
        log "Error retrieving kubeadm configmap, retrying..."
        sleep 5
        let "counter+=1"
    done

    if [ $counter -gt $RETRIES ]; then
        log "Failed to retrieve kubeadm configmap with error code [$RC]".
        exit $RC
    fi

    if ! grep -q 'RemoveSelfLink=false' ${KUBEADM_CONFIGMAP_TMPFILE}; then

        log "Updating kube-apiserver feature-gates in retrieved kubeadm-config"

        if sed -i \
'/^\s*feature-gates:\s*.*HugePageStorageMediumSize='\
'true/ s/$/,RemoveSelfLink=false/' ${KUBEADM_CONFIGMAP_TMPFILE}; then

            if grep -q 'RemoveSelfLink=false' ${KUBEADM_CONFIGMAP_TMPFILE};
            then
                log "Successfully updated retrieved kubeadm-config"
                if kubectl --kubeconfig=/etc/kubernetes/admin.conf replace -f \
                        ${KUBEADM_CONFIGMAP_TMPFILE}; then
                    log 'Successfully replaced updated kubeadm configmap.'
                else
                    RC=$?
                    log "Failed to replace updated kubeadm configmap with error code: [$RC]"
                    exit $RC
                fi
            else
                log 'Failed to update kube-apiserver feature-gates with an unknown error'
                exit -1
            fi
        else
            RC=$?
            log "Failed to update ${KUBEADM_CONFIGMAP_TMPFILE} with error code: [$RC]"
            exit $RC
        fi
    else
        log "Kubeadm configmap was already updated with RemoveSelfLink=false. Nothing to do."
    fi

    rm -f ${KUBEADM_CONFIGMAP_TMPFILE}

}

update_apiserver_configmap
exit 0
