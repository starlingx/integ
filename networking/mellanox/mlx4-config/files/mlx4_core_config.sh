#!/bin/bash
################################################################################
# Copyright (c) 2015-2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
#
# Purpose:
#   create /var/run/.mlx4_cx3_reboot_required to indicate a reboot is required
#     this way newly generated mlx4_core kernel options can be applied
#   inject /etc/modprobe.d/mlx4_sriov.conf into initramfs, since when the system
#     is booted, the mlx4_core kernel module in initramfs will be used, so we need
#     to inject the newly created modprobe conf file into initramfs
#
# Usage: /usr/bin/mlx4_core_config.sh
#
# Define minimal path
PATH=/bin:/usr/bin:/usr/local/bin

/usr/sbin/touch /var/run/.mlx4_cx3_reboot_required
/usr/bin/dracut --include /etc/modprobe.d/mlx4_sriov.conf /etc/modprobe.d/mlx4_sriov.conf --force

exit 0
