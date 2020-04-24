#!/bin/bash
################################################################################
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################

PROJECT=$1
IMAGE_TAG=$2

if [ -z "${IMAGE_TAG}" ]; then
    echo "image tag must be specified. build ${PROJECT} Aborting..." >&2
    exit 1
fi

make build
if [ $? -ne 0 ]; then
    echo "Failed to build ${PROJECT}. Aborting..." >&2
    exit 1
fi

make image
if [ $? -ne 0 ]; then
    echo "Failed to make ${PROJECT} image. Aborting..." >&2
    exit 1
fi

RETVAL=0
docker tag nfvpe/${PROJECT}:latest "${IMAGE_TAG}"
if [ $? -ne 0 ]; then
    echo "Failed to tag ${PROJECT} with ${IMAGE_TAG}. Aborting..." >&2
    RETVAL=1
fi

docker rmi nfvpe/${PROJECT}:latest
exit ${RETVAL}

