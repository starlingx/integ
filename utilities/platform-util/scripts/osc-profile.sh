#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

if [ -n "$BASH_VERSION" -o -n "$KSH_VERSION" -o -n "$ZSH_VERSION" ]; then
    alias openstack >/dev/null 2>&1 || alias openstack='/usr/local/bin/openstack-pod-exec.sh openstack'
    alias nova >/dev/null 2>&1 || alias nova='/usr/local/bin/openstack-pod-exec.sh nova'
    alias platform-openstack >/dev/null 2>&1 || alias platform-openstack=/usr/bin/openstack
fi
