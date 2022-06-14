#!/bin/bash
################################################################################
# Copyright (c) 2022 Wind River Systems, Inc.
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

# Copy patches from:
# https://opendev.org/starlingx/integ/src/branch/master/kubernetes/armada/debian/deb_folder/patches
tmp_dir=$(mktemp -d -t armada-XXXXXXXXXX --tmpdir=/tmp)
pushd ${tmp_dir}
git clone https://opendev.org/starlingx/integ/
if [ $? -ne 0 ]; then
    echo "Failed to clone patches for ${PROJECT}. Aborting..." >&2
    exit 1
fi
popd
cp -r ${tmp_dir}/integ/kubernetes/armada/debian/deb_folder/patches .
rm -rf ${tmp_dir}

# Apply patches
pushd patches
cat series | xargs -n 1 git am
if [ $? -ne 0 ]; then
    echo "Failed to apply patches for ${PROJECT}. Aborting..." >&2
    exit 1
fi
popd

# Use Makefile to build images
make images
if [ $? -ne 0 ]; then
    echo "Failed to make ${PROJECT} image. Aborting..." >&2
    exit 1
fi

RETVAL=0
docker tag quay.io/airshipit/armada:latest-ubuntu_bionic "${IMAGE_TAG}"
if [ $? -ne 0 ]; then
    echo "Failed to tag ${PROJECT} with ${IMAGE_TAG}. Aborting..." >&2
    RETVAL=1
fi

docker rmi quay.io/airshipit/armada:latest-ubuntu_bionic
exit ${RETVAL}
