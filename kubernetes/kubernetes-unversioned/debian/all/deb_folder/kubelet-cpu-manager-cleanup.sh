#!/bin/bash
#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Remove a stale kubelet cpu_manager_state checkpoint before kubelet starts.
#
# When the kubelet CPU manager policy changes (e.g. none -> static during a
# DM-driven unlock), the old cpu_manager_state checkpoint persists from a
# previous kubelet run. Kubelet crashes on startup if the configured policy
# differs from the checkpoint. Removing the stale file lets kubelet
# regenerate it cleanly on the next start.
#
# Runs as a kubelet ExecStartPre so it covers every kubelet start, not only
# puppet-driven config applies.

# Define minimal path
PATH=/bin:/usr/bin:/usr/local/bin

# Log info message to /var/log/daemon.log
function LOG {
    logger -p daemon.info "$0($$): $@"
}

S=/var/lib/kubelet/cpu_manager_state
if [ -f "$S" ]; then
    C=$(grep -oP "cpu-manager-policy=\K[^ ]*" /etc/default/kubelet 2>/dev/null)
    P=$(python3 -c "import json;print(json.load(open('$S')).get('policyName',''))" 2>/dev/null)
    if [ -n "$C" ] && [ -n "$P" ] && [ "$C" != "$P" ]; then
        rm -f "$S"
        LOG "Removed stale cpu_manager_state (was=$P, now=$C)"
    fi
fi

exit 0
