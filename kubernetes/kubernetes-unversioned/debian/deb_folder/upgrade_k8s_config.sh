#!/bin/bash
# Copyright (c) 2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# This will run during a k8s upgrade as a part of the control-plane upgrade of
# the first master. It updates the kubeadm-config configmap to edit the
# manifests and remove the 'feature-gates' lines.
#
# Background:
# Kubernetes 1.24 no longer allows setting kube-apsierver feature-gate
# RemoveSelfLink=false. All the other feature gates we were using now default
# to true so we don't want to specify them anymore.

# Temporary configuration file
KUBEADM_CONFIGMAP_TMPFILE=$(mktemp /tmp/kubeadm_cm.yaml.XXXXXX 2>/dev/null)

# Log info message to /var/log/daemon.log
function LOG {
    logger -p daemon.info "$0($$): " "${@}"
}

# Log error message to /var/log/daemon.log
function ERROR {
    logger -s -p daemon.error "$0($$): " "${@}"
}

# Cleanup and exit
function cleanup_and_exit {
    rm -v -f "${KUBEADM_CONFIGMAP_TMPFILE}"
    exit "${1:-0}"
}

# Update the configmap for kubeadm
function update_apiserver_configmap {
    LOG "Retrieving kubeadm configmap: ${KUBEADM_CONFIGMAP_TMPFILE}"
    counter=0
    RETRIES=10
    RC=0
    until  [ $counter -gt $RETRIES ]; do
        kubectl --kubeconfig=/etc/kubernetes/admin.conf -n kube-system get \
            configmap kubeadm-config -o yaml > "${KUBEADM_CONFIGMAP_TMPFILE}"
        RC=$?
        if [ "$RC" = "0" ] ; then
            LOG "Kubeadm configmap retrieved."
            break
            ((counter+=1))
        fi
        ERROR "Failed to retrieve kubeadm configmap, retrying..."
        sleep 5
        ((counter+=1))
    done

    if [ $counter -gt $RETRIES ]; then
        ERROR "Failed to retrieve kubeadm configmap with error code [$RC]".
        cleanup_and_exit $RC
    fi

    if grep -q 'RemoveSelfLink=false' "${KUBEADM_CONFIGMAP_TMPFILE}"; then
        LOG "Updating kube-apiserver feature-gates in retrieved kubeadm-config"
        if sed -i '/feature-gates/d' "${KUBEADM_CONFIGMAP_TMPFILE}"; then
            if ! grep -q 'RemoveSelfLink=false' "${KUBEADM_CONFIGMAP_TMPFILE}";
            then
                LOG "Successfully updated retrieved kubeadm-config"
                if kubectl --kubeconfig=/etc/kubernetes/admin.conf replace -f \
                        "${KUBEADM_CONFIGMAP_TMPFILE}"; then
                    LOG 'Successfully replaced updated kubeadm configmap.'
                else
                    RC=$?
                    ERROR "Failed to replace updated kubeadm configmap with error code: [$RC]"
                    cleanup_and_exit $RC
                fi
            else
                ERROR 'Failed to update kube-apiserver feature-gates with an unknown error'
                cleanup_and_exit 1
            fi
        else
            RC=$?
            ERROR "Failed to update ${KUBEADM_CONFIGMAP_TMPFILE} with error code: [$RC]"
            cleanup_and_exit $RC
        fi
    else
        LOG "Kubeadm configmap was already updated with RemoveSelfLink=false removed. Nothing to do."
    fi
}

# Update kube-apiserver configMap only for k8s 1.23.1
K8S_VERSION_FROM='v1.23.1'
K8S_VERSION=$(kubectl version --output=yaml| grep -m1 -oP 'gitVersion: \K(\S+)')
if [[ "${K8S_VERSION}" == "${K8S_VERSION_FROM}" ]]; then
    LOG "k8s version ${K8S_VERSION} matches ${K8S_VERSION_FROM}"
    update_apiserver_configmap
else
    LOG "k8s version ${K8S_VERSION} does not match ${K8S_VERSION_FROM}, skip update"
fi

cleanup_and_exit 0
