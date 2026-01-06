#!/bin/bash
#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

script=$(basename $0)

# Set nullglob so wildcards will return empty string if no match
shopt -s nullglob

state=$(timeout 10 systemctl is-system-running)
case $? in
    124)
        # If systemctl hangs, proceed with unmounting RBD devices to prevent
        # shutdown hang. This maintains any existing edge-case behavior
        logger -t ${script} "systemctl timed out. System state unknown."
        ;;

    [01])
        # 0 - running; 1 - initializing, starting, degraded, maintenance, stopping
        logger -t ${script} "System is $state"
        if [ "$state" != "stopping" ]; then
            logger -t ${script} "System is not shutting down. Leaving RBD devices mounted"
            exit 0
        fi
        ;;
esac

logger -t ${script} "Unmounting RBD devices"

# Unmount the RBD devices as the system is shutting down.
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

# Stop Ceph MDS, OSD, MON with 10s timeout
timeout 10s /etc/init.d/ceph-init-wrapper stop mds
timeout 10s /etc/init.d/ceph-init-wrapper stop osd
timeout 10s /etc/init.d/ceph-init-wrapper stop mon

lsmod | grep -q '^rbd\>' && /usr/sbin/modprobe -r rbd
lsmod | grep -q '^libceph\>' && /usr/sbin/modprobe -r libceph

exit 0
