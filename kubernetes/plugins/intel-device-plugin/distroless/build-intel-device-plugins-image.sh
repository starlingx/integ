#!/bin/bash
################################################################################
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################

DEVICE=$1
IMAGE_TAG=$2

if [ -z "${IMAGE_TAG}" ]; then
    echo "image tag must be specified. build ${DEVICE} Aborting..." >&2
    exit 1
fi

# https://bugs.launchpad.net/starlingx/+bug/1927153
# https://bugs.launchpad.net/starlingx/+bug/1939448
# pin clearlinux/golang to the last known working tag
CLEAR_LINUX_BASE=clearlinux/golang:1.15.10
CLEAR_LINUX_VERSION=34900

sed -i -r \
    -e 's!^(\s*ARG\s+CLEAR_LINUX_BASE\s*=\s*).*!\1'$CLEAR_LINUX_BASE'!' \
    -e 's!^(\s*ARG\s+CLEAR_LINUX_VERSION\s*=\s*).*!\1--version='$CLEAR_LINUX_VERSION'!' \
    build/docker/${DEVICE}.Dockerfile || exit 1

make ${DEVICE}

if [ $? -ne 0 ]; then
    echo "Failed to make ${DEVICE}. Aborting..." >&2
    exit 1
fi

RETVAL=0
docker tag intel/${DEVICE}:devel "${IMAGE_TAG}"
if [ $? -ne 0 ]; then
    echo "Failed to tag ${DEVICE} with ${IMAGE_TAG}. Aborting..." >&2
    RETVAL=1
fi

docker rmi intel/${DEVICE}:devel
exit ${RETVAL}
