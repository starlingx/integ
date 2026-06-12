#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (c) 2026 Wind River Systems, Inc.
#

from unittest import mock
from unittest import TestCase

import update_kubelet_version as ukv


class TestKubeletVersionUpdateManager(TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch.object(ukv.KubeletVersionUpdateManager, "__init__", lambda self: None)
    def test_get_kube_version_from_symlink(self):
        manager = ukv.KubeletVersionUpdateManager()
        with mock.patch("os.readlink", return_value="/usr/local/kubernetes/1.32.2/stage1"):
            version = manager._get_kube_version_from_symlink(stage_number=1)
            assert version == "1.32.2"
