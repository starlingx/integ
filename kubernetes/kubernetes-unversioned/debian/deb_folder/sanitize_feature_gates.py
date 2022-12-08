#!/usr/bin/env python
'''Removes the "RemoveSelfLink=false" kube-apiserver feature gate

Usage:
    ./sanitize_feature_gates.py

This script is just to remove the "RemoveSelfLink=false" kube-apiserver
feature gate from the last_kube_extra_config_bootstrap.yaml file when
doing an upgrade from K8s 1.23 to 1.24.
Once we no longer need to worry about upgrading from 1.23 we can remove this.

Copyright (c) 2022 Wind River Systems, Inc.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:
      http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software  distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
OR CONDITIONS OF ANY KIND, either express or implied. 
'''

import syslog
import yaml

FILENAME = "/opt/platform/config/22.12/last_kube_extra_config_bootstrap.yaml"

# The above file contains information that is used during backup and restore.
# We want to remove the "RemoveSelfLink=false" kube-apiserver feature gate
# if it's present so that if we do a backup and restore after the upgrade
# to K8s 1.24 we won't try to use this feature gate any more.  Any other feature
# gates should be left alone, and if there aren't any other feature gates
# we want to delete the entire "feature-gates" entry.

# Logs will go to /var/log/daemon.log
syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

try:
    with open(FILENAME, "r") as stream:
        info = yaml.safe_load(stream)
except Exception as exc:
    syslog.syslog(syslog.LOG_ERR, "Problem reading from {}".format(FILENAME))
    syslog.syslog(syslog.LOG_ERR, str(exc))
    exit(1)

try:
    feature_gates = info['apiserver_extra_args']['feature-gates']
except KeyError:
    # No apiserver feature gates, nothing to do
    syslog.syslog('No kube-apiserver feature gates, nothing to do.')
    exit(0)

if "RemoveSelfLink=false" not in feature_gates:
    # Nothing to do
    syslog.syslog('No changes needed in kube-apiserver feature gates.')
    exit(0)

# Remove "RemoveSelfLink=false" from the feature gates
# we need to handle the case where it could be at the beginning of the string
# with other entries after it, or at the end of the string with other entries
# before it, in the middle of the string, or by itself.
feature_gates = feature_gates.replace('RemoveSelfLink=false,', '')
feature_gates = feature_gates.replace(',RemoveSelfLink=false', '')
feature_gates = feature_gates.replace('RemoveSelfLink=false', '')

if not feature_gates:
    # No feature gates left, so delete the entry
    syslog.syslog('Deleting kube-apiserver feature gates.')
    info['apiserver_extra_args'].pop('feature-gates', None)
else:
    # Update the feature gates with the new value
    syslog.syslog('Modifying kube-apiserver feature gates.')
    info['apiserver_extra_args']['feature-gates'] = feature_gates

# Write out the new file.
try:
    with open(FILENAME, 'w') as outfile:
        yaml.safe_dump(info, outfile, default_flow_style=False, sort_keys=False)
except Exception as exc:
    syslog.syslog(syslog.LOG_ERR, "Problem writing to {}".format(FILENAME))
    syslog.syslog(syslog.LOG_ERR, str(exc))
    exit(1)

syslog.syslog('Successfully wrote file with RemoveSelfLink=false removed.')
