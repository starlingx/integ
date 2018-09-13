#!/bin/bash
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# The following script tests the NFS mount in order to log when it is hung

MOUNT=/opt/platform
previous=1
delay=60

while : ; do
    # First, check that it's actually an NFS mount
    mount | grep -q $MOUNT
    if [ $? -ne 0 ]; then
        logger -t NFSCHECK "$MOUNT is not mounted"
        previous=1
        sleep $delay
        continue
    fi

    ls $MOUNT >/dev/null 2>&1 &

    sleep $delay

    # At this point, jobs will either report no jobs (empty) or Done,
    # unless the job is still running/hung
    rc=$(jobs)
    if [[ -z "$rc" || $rc =~ "Done" ]]; then
        # NFS is successful
        if [ $previous -ne 0 ]; then
            logger -t NFSCHECK "NFS test of $MOUNT is ok"
            previous=0
        fi
    else
        # Keep waiting until the job is done
        while ! [[ -z "$rc" || $rc =~ "Done" ]]; do
            logger -t NFSCHECK "NFS test of $MOUNT is failed"
            previous=1
            sleep $delay
            rc=$(jobs)
        done
    fi
done

