#!/usr/bin/env python3
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# The script is intented to run before the kubelet service is started as a part
# of the host-unlock operation of "software deploy host" stage of USM platform
# upgrade. This script runs as a "ExecStartPre" action. The script updates kubelet
# version to the version mentioned in the file /etc/kubelet/kubelet_version.
# This script is currently supported on AIO-SX but is designed and implemented
# to be extendable on all deployment configurations as "Combined platform and K8s upgrade"
# will be eventually supported on all deployment configs.

import configparser
import json
import logging as LOG
import os
import re
import sys

from sysinv.common import constants
from sysinv.common import containers
from sysinv.common import kubernetes
from sysinv.common import utils

KUBELET_VERSION_FILE = '/etc/kubernetes/kubelet_version'
PLATFORM_FILE = '/etc/platform/platform.conf'
LOG_FILE = '/var/log/software.log'
SIMPLEX = 'simplex'
NODETYPE_WORKER = 'worker'
NODETYPE_CONTROLLER = 'controller'


# Logging
def setup_logger():
    """Setup a logger."""
    LOGGER_FORMAT = "%(asctime)s.%(msecs)03d %(process)s %(filename)s [%(levelname)s] %(message)s"
    LOG.basicConfig(filename=LOG_FILE, format=LOGGER_FORMAT, level=LOG.DEBUG, datefmt="%FT%T")


def get_system_info():
    """Read platform details from /etc/platform/platform.conf

    :return: Return dictionary containing only few important platform
             details like system_type, system_mode, node type,
             software version, uuid and the subfunction
    """
    ini_str = '[DEFAULT]\n' + open(PLATFORM_FILE, 'r').read()

    config_applied = configparser.RawConfigParser()
    config_applied.read_string(ini_str)

    system_mode = config_applied.get('DEFAULT', 'system_mode', fallback=None)

    system_type = config_applied.get('DEFAULT', 'system_type', fallback=None)

    nodetype = config_applied.get('DEFAULT', 'nodetype', fallback=None)

    subfunction = config_applied.get('DEFAULT', 'subfunction', fallback=None)

    sw_version = config_applied.get('DEFAULT', 'sw_version', fallback=None)

    uuid = config_applied.get('DEFAULT', 'uuid', fallback=None)

    info = {
        "system_mode": system_mode,
        "system_type": system_type,
        "nodetype": nodetype,
        "subfunction": subfunction,
        "sw_version": sw_version,
        "uuid": uuid
    }

    LOG.debug(info)

    return info


class KubeletVersionUpdateManager(object):
    """Kubelet version update manager"""

    def __init__(self):
        self.system_info = get_system_info()

    def _get_current_kubelet_version(self):
        """Return current kubelet version"""
        current_version = kubernetes.get_kube_version_from_symlink(stage_number=2)
        LOG.debug("Current kubelet version: %s" % (current_version))
        return current_version

    def _read_version_details(self):
        """Parse the kubelet_version file and return version details

        """
        # File existence check is not strictly required as below block will
        # throw an exception in case file does not exist which is caught
        # and logged in the main() method.
        with open(KUBELET_VERSION_FILE, "r") as file:
            version_details = json.load(file)
        return version_details

    def _pull_pause_image(self, target_pause_image):
        """Pull pause image of the target version

        :param: target_pause_image: Target pause image string
        """
        local_registry_auth = utils.get_local_docker_registry_auth()
        crictl_auth = (
            f"{local_registry_auth['username']}:{local_registry_auth['password']}"
        )
        pause_image_to_download = \
            f"{constants.DOCKER_REGISTRY_SERVER}/{target_pause_image}"
        if not containers.pull_image_to_crictl(pause_image_to_download, crictl_auth):
            raise Exception("Failed to pull the pause image required for "
                            "the kubelet upgrade.")

    def update_kubelet_version_update_status(self, success):
        """Update database with kubelet upgrade/downgrade status

        :param: success: bool. True: If version update succeeds False otherwise
        """
        pass

    def _update_pause_image_in_containerd(self, from_kubelet_version, to_kubelet_version):
        """Update pause image in containerd config file

        :param: from_kubelet_version: Current kubelet version
        :param: to_kubelet_version: Version string to update kubelet version to
        """
        try:
            current_images = kubernetes.get_k8s_images(from_kubelet_version)
            current_pause_image = current_images['pause']

            target_images = kubernetes.get_k8s_images(to_kubelet_version)
            target_pause_image = target_images['pause']

            if current_pause_image == target_pause_image:
                LOG.info("No need to update 'pause' image inside containerd config. Proceeding...")
                return

            # Pause image is pulled on controllers as a part of kube-download-images
            # step. On compute nodes, it is not present and it needs to be pulled.
            # This is not presently supported but will be required in the future.
            if self.system_info.get("nodetype") == NODETYPE_WORKER:
                self._pull_pause_image(target_pause_image)

            stream = ""
            with open(containers.CONTAINERD_CONFIG_FULL_PATH, 'r') as file:
                stream = file.read()
            if stream != "":
                update_sandbox_image = (
                    f'sandbox_image = "{constants.DOCKER_REGISTRY_SERVER}/{target_pause_image}"'
                )
                # containerd config.toml has a single sandbox_image entry
                stream = re.sub(r'sandbox_image\s*=\s*".*?"', update_sandbox_image, stream, count=1)
                with open(containers.CONTAINERD_CONFIG_FULL_PATH, 'w') as file:
                    file.write(stream + '\n')
                LOG.info("Successfully updated pause image version in the "
                         "containerd config: %s" % (target_pause_image))
            else:
                raise Exception("Could not properly read containerd config file: "
                                "[%s]. " % (containers.CONTAINERD_CONFIG_FULL_PATH))
        except Exception as ex:
            raise Exception("Failed to update containerd config file [%s] with the "
                            "new pause image version [%s], Error: [%s]"
                            % (containers.CONTAINERD_CONFIG_FULL_PATH, target_pause_image, ex))

    def _update_stage2_symlink(self, to_kubelet_version):
        """Update stage2 symlink to update the kubelet version

        :param: to_kubelet_version: Version string to upgrade kubelet version to
        """
        try:
            to_kubelet_version = to_kubelet_version.strip('v')

            versioned_stage = \
                os.path.join(kubernetes.KUBERNETES_VERSIONED_BINARIES_ROOT,
                             to_kubelet_version, 'stage2')

            # Remove symlink for previous kuberbetes version
            if os.path.islink(kubernetes.KUBERNETES_SYMLINKS_STAGE_2):
                os.remove(kubernetes.KUBERNETES_SYMLINKS_STAGE_2)
            os.symlink(versioned_stage, kubernetes.KUBERNETES_SYMLINKS_STAGE_2)
            LOG.info("Kubernetes symlink [%s] is updated to [%s] "
                     % (kubernetes.KUBERNETES_SYMLINKS_STAGE_2, versioned_stage))
        except Exception as ex:
            raise Exception("Failed to update symlink [%s]. Error: [%s]"
                            % (kubernetes.KUBERNETES_SYMLINKS_STAGE_2, ex))

    def update_kubelet_version(self, upgrade=True):
        """Update kubelet version on this host

        Updates kubelet to the version retrived from file /etc/kubernetes/kubelet_version
        By default it does an upgrade as of now. But in future it can be extended to support
        rollback with only minimal changes

        :param: upgrade: Bool (default True) True for upgrade, False for downgrade (future scope)
        """
        system_mode = self.system_info.get("system_mode")
        if not system_mode:
            raise Exception("system mode not found.")

        # Currently only AIO-SX is supported. Remove this condition to extend
        # this functionality to multinode.
        if system_mode != SIMPLEX:
            return

        version_details = self._read_version_details()
        LOG.debug("Version details: %s" % (version_details))
        to_kubelet_version = version_details.get("to_kubelet_version", None)
        if not to_kubelet_version:
            raise Exception("'to_kubelet_version' not found in the additional data.")

        from_kubelet_version = self._get_current_kubelet_version()
        if from_kubelet_version == to_kubelet_version:
            LOG.info("Kubelet already updated to version %s on this host."
                     % (to_kubelet_version))
            return

        LOG.info("Updating kubelet to version %s on this host." % (to_kubelet_version))
        self._update_pause_image_in_containerd(from_kubelet_version, to_kubelet_version)
        self._update_stage2_symlink(to_kubelet_version)
        # GC was disabled during image download to prevent undesirable image removal before
        # control plane and kubelet upgrade. Re-enable it here.
        if self.system_info.get("nodetype") == NODETYPE_CONTROLLER:
            kubernetes.enable_kubelet_garbage_collection()
        LOG.info("Kubelet version update successful from %s to %s on this host."
                 % (from_kubelet_version, to_kubelet_version))


def main():
    try:
        manager = None
        setup_logger()
        manager = KubeletVersionUpdateManager()
        manager.update_kubelet_version()
        manager.update_kubelet_version_update_status(True)
        return 0
    except Exception as ex:
        LOG.error(ex)
        if not manager:
            manager = KubeletVersionUpdateManager()
        manager.update_kubelet_version_update_status(False)
        return 1


if __name__ == "__main__":
    sys.exit(main())
