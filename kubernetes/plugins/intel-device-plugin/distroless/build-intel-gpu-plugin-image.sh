#!/bin/bash

IMAGE_TAG=$1
PROXY=$2
DEVICE='intel-gpu-plugin'

if [ -z "${IMAGE_TAG}" ]; then
    echo "image tag must be specified. build ${DEVICE} Aborting..." >&2
    exit 1
fi

make ${DEVICE}

if [ $? -ne 0 ]; then
    echo "Failed to make intel-gpu-plugin. Aborting..." >&2
    exit 1
fi

# will exit 1 if "${IMAGE_TAG}" do not match docker tag formate
docker tag ${DEVICE}:devel "${IMAGE_TAG}"
