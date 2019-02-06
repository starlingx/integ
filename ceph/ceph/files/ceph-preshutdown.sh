#!/bin/bash
#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

script=$(basename $0)

# Set nullglob so wildcards will return empty string if no match
shopt -s nullglob

for dev in /dev/rbd[0-9]*; do
    for mnt in $(mount | awk -v dev=$dev '($1 == dev) {print $3}'); do
        logger -t ${script} "Unmounting $mnt"
        /usr/bin/umount $mnt
    done
    logger -t ${script} "Unmounted $dev"
done

for dev in /dev/rbd[0-9]*; do
    /usr/bin/rbd unmap -o force $dev
    logger -t ${script} "Unmapped $dev"
done

lsmod | grep -q '^rbd\>' && /usr/sbin/modprobe -r rbd
lsmod | grep -q '^libceph\>' && /usr/sbin/modprobe -r libceph

exit 0

