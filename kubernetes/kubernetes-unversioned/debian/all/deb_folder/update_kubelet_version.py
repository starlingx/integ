#!/usr/bin/python3
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
import keyring
import logging as LOG
import os
import re
import subprocess
import time
import sys


CONTAINERD_CONFIG_FULL_PATH = "/etc/containerd/config.toml"
DOCKER_REGISTRY_HOST = 'registry.local'
DOCKER_REGISTRY_PORT = '9001'
DOCKER_REGISTRY_SERVER = '%s:%s' % (DOCKER_REGISTRY_HOST, DOCKER_REGISTRY_PORT)
DOCKER_REGISTRY_USER = 'sysinv'
KUBEADM_FLAGS_FILE = '/var/lib/kubelet/kubeadm-flags.env'
KUBEADM_PATH_FORMAT_STR = "/usr/local/kubernetes/{kubeadm_ver}/stage1/usr/bin/kubeadm"
KUBELET_VERSION_FILE = '/etc/kubernetes/kubelet_version'
KUBERNETES_VERSIONED_BINARIES_ROOT = '/usr/local/kubernetes/'
KUBERNETES_SYMLINKS_ROOT = '/var/lib/kubernetes/'
KUBERNETES_SYMLINKS_STAGE_1 = os.path.join(KUBERNETES_SYMLINKS_ROOT, 'stage1')
KUBERNETES_SYMLINKS_STAGE_2 = os.path.join(KUBERNETES_SYMLINKS_ROOT, 'stage2')
LOG_FILE = '/var/log/software.log'
NODETYPE_CONTROLLER = 'controller'
NODETYPE_WORKER = 'worker'
OSTREE1_USM_UPGRADE_IN_PROGRESS = '/ostree/1/etc/platform/.usm_upgrade_in_progress'
PLATFORM_FILE = '/etc/platform/platform.conf'
SIMPLEX = 'simplex'


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

        system_mode = self.system_info.get("system_mode")
        if not system_mode:
            raise Exception("system mode not found.")
        # Currently only AIO-SX is supported. Remove this condition to extend
        # this functionality to multinode.
        if system_mode != SIMPLEX:
            LOG.info("Not a Simplex system. Kubelet version update not required.")
            sys.exit(0)

        self._version_details = self._read_version_details()
        if not self._version_details:
            # This may be a classic platform upgrade. Do nothing. Simply log and exit.
            LOG.warning("Kubelet version file [%s] not found. Combined platform and k8s upgrade "
                        "may fail if it is being attempted." % (KUBELET_VERSION_FILE))
            sys.exit(0)

    def _execute(self, command):
        """Helper method to execute a shell command, capture output, and avoid zombie processes.

        :param command: The shell command to execute.

        :returns: a tuple: (stdout, stderr) from the command, or ("", "")
        if an error occurs.
        """
        stdout, stderr = "", ""

        try:
            with subprocess.Popen(command,
                                  stdout=subprocess.PIPE,
                                  shell=True,
                                  universal_newlines=True) as process:
                stdout, stderr = process.communicate(timeout=5)

        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()  # Reap the process to avoid zombie
            LOG.error("Command '%s' timed out", command)
            return ("", "")
        except Exception as e:
            LOG.error("Could not execute command '%s': %s", command, e)
            return ("", "")

        return (stdout, stderr)

    def _get_kube_version_from_symlink(self, stage_number=None):
        """Retrieve current kubernetes version based on the stage1 symlink.

        Expecting the following symlink, e.g., for version 1.32.2
        /var/lib/kubernetes/stage1 -> /usr/local/kubernetes/1.32.2/stage1

        :param: stage_number(optional) int 1 or 2 as there are two stages total
        :returns: kubernetes_version string
        """
        # Any stage can be used as default if "stage_number" is not provided
        stage = KUBERNETES_SYMLINKS_STAGE_1
        pattern = r"/usr/local/kubernetes/(.*)/stage1"
        if stage_number:
            if int(stage_number) == 1:
                stage = KUBERNETES_SYMLINKS_STAGE_1
                pattern = r"/usr/local/kubernetes/(.*)/stage1"
            elif int(stage_number) == 2:
                stage = KUBERNETES_SYMLINKS_STAGE_2
                pattern = r"/usr/local/kubernetes/(.*)/stage2"
            else:
                raise Exception(
                    "Invalid stage number to retrieve kubernetes version: %d."
                    "Could only be either 1 or 2" % (stage_number))

        # Read the symlink
        try:
            target = os.readlink(stage)
        except OSError as ex:
            raise Exception("Failed to read symlink %s. Error: %s" % (stage, ex))

        # Parse the kubernetes_version from the symlink target
        match = re.search(pattern, target)
        if match is None:
            LOG.error("Unable to find kubernetes_version in symlink target %s" % (target))
            return None
        else:
            return match.group(1)

    def _get_local_docker_registry_auth(self):
        registry_password = keyring.get_password(
            DOCKER_REGISTRY_USER, "services")

        if not registry_password:
            raise Exception(name=DOCKER_REGISTRY_USER)

        return dict(username=DOCKER_REGISTRY_USER,
                    password=registry_password)

    def _get_current_kubelet_version(self):
        """Return current kubelet version"""
        current_version = self._get_kube_version_from_symlink(stage_number=2)
        LOG.debug("Current kubelet version: %s" % (current_version))
        return current_version

    def _read_version_details(self):
        """Parse the kubelet_version file and return version details

        """
        if not os.path.exists(KUBELET_VERSION_FILE):
            return None

        with open(KUBELET_VERSION_FILE, "r") as file:
            version_details = json.load(file)
        return version_details

    def _pull_image_to_crictl(self, image, crictl_auth, attempts=5, delay_on_retry=True):
        """Helper method to pull an image into crictl

        This method pulls the specified image into containerd cache.

        :param: image: image name
        :param: crictl_auth: auth credentials for containerd
        :param: attempts: Number of retries
        :param: delay_on_retry: delay between attempts in seconds

        :raises: SysinvException upon error
        """
        start = time.time()
        try:
            LOG.info("crictl image pull [%s] started." % (image))

            cmd = f"crictl pull --creds {crictl_auth}, {image}"
            self._execute(
                cmd, attempts=attempts, delay_on_retry=delay_on_retry, check_exit_code=0)
        except Exception as e:
            raise Exception("crictl pull for image [%s] failed: "
                            "Error: [%s]" % (image, e))

        elapsed_time = time.time() - start
        LOG.info("crictl image pull [%s] succeeded in %s seconds" % (image, elapsed_time))

    def _pull_pause_image(self, target_pause_image):
        """Pull pause image of the target version

        :param: target_pause_image: Target pause image string
        """
        local_registry_auth = self._get_local_docker_registry_auth()
        crictl_auth = (
            f"{local_registry_auth['username']}:{local_registry_auth['password']}"
        )
        pause_image_to_download = \
            f"{DOCKER_REGISTRY_SERVER}/{target_pause_image}"
        if not self._pull_image_to_crictl(pause_image_to_download, crictl_auth):
            raise Exception("Failed to pull the pause image required for "
                            "the kubelet upgrade.")

    def _get_k8s_images(self, kube_version):
        """Provides a list of images for a kubernetes version.

        :param: kube_version: kubernetes version string.
        :returns: nested dictionary component name as a key and upstream (public) image name:tag as
                value.
                e.g. {'kube-apiserver': 'registry.k8s.io/kube-apiserver:v1.29.2',
                        'kube-controller-manager': 'registry.k8s.io/kube-controller-manager:v1.29.2',
                        'kube-scheduler': 'registry.k8s.io/kube-scheduler:v1.29.2',
                        'kube-proxy': 'registry.k8s.io/kube-proxy:v1.29.2',
                        'coredns': 'registry.k8s.io/coredns/coredns:v1.11.1',
                        'pause': 'registry.k8s.io/pause:3.9',
                        'etcd': 'registry.k8s.io/etcd:3.5.10-0'}
        """
        try:
            kubeadm_path = KUBEADM_PATH_FORMAT_STR.format(kubeadm_ver=kube_version)
            cmd = f"{kubeadm_path} config images list --kubernetes-version {kube_version}"
            stdout, _ = self._execute(cmd)
            images = stdout.split()
            # It may be feasible to do below parsing wherever required but doing it once will
            # make it easier and efficient to access using image name whenever required. So do
            # just once here itstead of doing repetitively at different places.
            image_dict = {}
            for image in images:
                key = image.split('/')[1].split(':')[0]
                image_dict.update({key: image})
            LOG.info("List of images for kubernetes version %s: %s" % (kube_version, image_dict))
        except Exception as ex:
            raise Exception("Error getting all kubernetes images: %s" % (ex))
        return image_dict

    def _enable_kubelet_garbage_collection(self):
        """Enables kubelet garbage collection

        This method virtually enables back kubelet image garbage collection by removing
        high(100) image garbage collection threshold in the kubelet config.
        Note that, this DOES NOT restart the kubelet after updating the value and must be
        restarted explicitly to take effect.

        :raises: SysinvException if an error is encountered
        """
        try:
            stream = None
            with open(KUBEADM_FLAGS_FILE, "r") as file:
                stream = file.read()
            if stream and "image-gc-high-threshold" in stream:
                stream = stream.replace("--image-gc-high-threshold 100 ", "")
                with open(KUBEADM_FLAGS_FILE, "w") as file:
                    file.write(stream)
        except Exception as ex:
            raise Exception("Failed to enable kubelet garbage "
                            "collection. Error: [%s]" % (ex))

    def _update_pause_image_in_containerd(self, from_kubelet_version, to_kubelet_version):
        """Update pause image in containerd config file

        :param: from_kubelet_version: Current kubelet version
        :param: to_kubelet_version: Version string to update kubelet version to
        """
        try:
            current_images = self._get_k8s_images(from_kubelet_version)
            current_pause_image = current_images['pause']

            target_images = self._get_k8s_images(to_kubelet_version)
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
            with open(CONTAINERD_CONFIG_FULL_PATH, 'r') as file:
                stream = file.read()
            if stream != "":
                update_sandbox_image = (
                    f'sandbox_image = "{DOCKER_REGISTRY_SERVER}/{target_pause_image}"'
                )
                # containerd config.toml has a single sandbox_image entry
                stream = re.sub(r'sandbox_image\s*=\s*".*?"', update_sandbox_image, stream, count=1)
                with open(CONTAINERD_CONFIG_FULL_PATH, 'w') as file:
                    file.write(stream + '\n')
                LOG.info("Successfully updated pause image version in the "
                         "containerd config: %s" % (target_pause_image))
            else:
                raise Exception("Could not properly read containerd config file: "
                                "[%s]. " % (CONTAINERD_CONFIG_FULL_PATH))
        except Exception as ex:
            raise Exception("Failed to update containerd config file [%s] with the "
                            "new pause image version. Error: [%s]"
                            % (CONTAINERD_CONFIG_FULL_PATH, ex))

    def _update_stage2_symlink(self, to_kubelet_version):
        """Update stage2 symlink to update the kubelet version

        :param: to_kubelet_version: Version string to upgrade kubelet version to
        """
        try:
            versioned_stage = \
                os.path.join(KUBERNETES_VERSIONED_BINARIES_ROOT,
                             to_kubelet_version, 'stage2')

            # Remove symlink for previous kuberbetes version
            if os.path.islink(KUBERNETES_SYMLINKS_STAGE_2):
                os.remove(KUBERNETES_SYMLINKS_STAGE_2)
            os.symlink(versioned_stage, KUBERNETES_SYMLINKS_STAGE_2)
            LOG.info("Kubernetes symlink [%s] is updated to [%s] "
                     % (KUBERNETES_SYMLINKS_STAGE_2, versioned_stage))
        except Exception as ex:
            raise Exception("Failed to update symlink [%s]. Error: [%s]"
                            % (KUBERNETES_SYMLINKS_STAGE_2, ex))

    def update_kubelet_version(self, upgrade=True):
        """Update kubelet version on this host

        Updates kubelet to the version retrived from file /etc/kubernetes/kubelet_version
        By default it does an upgrade as of now. But in future it can be extended to support
        rollback with only minimal changes

        :param: upgrade: Bool (default True) True for upgrade, False for downgrade (future scope)
        """
        to_kubelet_version = self._version_details.get("to_kubelet_version", None)
        if not to_kubelet_version:
            raise Exception("'to_kubelet_version' not found in the additional data.")
        to_kubelet_version = to_kubelet_version.strip('v')
        from_kubelet_version = self._get_current_kubelet_version()
        if from_kubelet_version == to_kubelet_version:
            LOG.info("Kubelet already updated to version %s on this host."
                     % (to_kubelet_version))
            return

        to_release = self._version_details.get("to_release", None)
        if not to_release:
            raise Exception("'to_release' not found in the additional data.")
        sw_version = self.system_info.get("sw_version", None)
        if sw_version != to_release:
            LOG.warning("Current installed release %s does not match the to_release %s. "
                        "Nothing to do." % (sw_version, to_release))
            return

        LOG.info("Updating kubelet to version %s on this host." % (to_kubelet_version))

        self._update_pause_image_in_containerd(from_kubelet_version, to_kubelet_version)
        self._update_stage2_symlink(to_kubelet_version)
        # GC was disabled during image download to prevent undesirable image removal before
        # control plane and kubelet upgrade. Re-enable it here.
        if self.system_info.get("nodetype") == NODETYPE_CONTROLLER:
            self._enable_kubelet_garbage_collection()
        LOG.info("Kubelet version update successful from %s to %s on this host."
                 % (from_kubelet_version, to_kubelet_version))


def main():
    try:
        setup_logger()
        manager = KubeletVersionUpdateManager()
        manager.update_kubelet_version()
    except Exception as ex:
        LOG.error("Error updating kubelet version %s" % (ex))


if __name__ == "__main__":
    main()
    sys.exit(0)
