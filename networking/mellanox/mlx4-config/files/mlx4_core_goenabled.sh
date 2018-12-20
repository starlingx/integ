#!/bin/bash
#
# Copyright (c) 2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# mlx4_core options "goenabled" check.
# If a /etc/modprobe.d/mlx_sriov.conf has been modified/created on this node, it should be rebooted to apply this options.

NAME=$(basename $0)
OPTIONS_CHANGED_FLAG=/var/run/.mlx4_cx3_reboot_required
WORKER_CONFIG_COMPLETE=/var/run/.worker_config_complete

function LOG {
    logger "$NAME: $*"
}

if [ -f $OPTIONS_CHANGED_FLAG ] && [ -f $WORKER_CONFIG_COMPLETE ]; then
    LOG "mlx4_core options has been changed. Failing goenabled check."
    exit 1
fi

exit 0

