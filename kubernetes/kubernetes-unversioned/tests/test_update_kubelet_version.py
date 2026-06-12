#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (c) 2026 Wind River Systems, Inc.
#

from unittest import mock
from unittest import TestCase

import copy
import update_kubelet_version as ukv


class TestKubeletVersionUpdateManager(TestCase):

    def setUp(self):
        self.test_system_info = {
            "system_mode": ukv.SIMPLEX,
            "system_type": "All-in-one",
            "nodetype": ukv.NODETYPE_CONTROLLER,
            "subfunction": f"{ukv.NODETYPE_CONTROLLER},{ukv.NODETYPE_WORKER}",
            "sw_version": "TEST_SW_VERSION",
            "uuid": "TEST_UUID"
        }
        mock_get_system_info = mock.MagicMock()
        self.mocked_get_system_info = mock.patch('update_kubelet_version.get_system_info',
                                                 mock_get_system_info)
        self.patched_get_system_info = self.mocked_get_system_info.start()

        self.test_version_details = {
            "from_release": "FROM_TEST_SW_VERSION",
            "to_release": "TEST_SW_VERSION",
            "to_kubelet_version": "TEST_TO_KUBELET_VERSION"
        }
        mock_read_version_details = mock.MagicMock()
        self.mocked_read_version_details = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._read_version_details',
            mock_read_version_details)
        self.patched_read_version_details = self.mocked_read_version_details.start()

    def tearDown(self):
        self.mocked_get_system_info.stop()
        self.mocked_read_version_details.stop()

    def test_update_kubelet_version_success(self):
        """Test successful execution of update_kubelet_version: expected workflow

        """
        from_kubelet_version = 'v1.31.5'
        to_kubelet_version = 'v1.32.2'

        fake_from_pause_image = 'fake_from_pause_image'
        fake_to_pause_image = 'fake_to_pause_image'

        containerd_read_data = 'sandbox_image = "%s/%s"' % (ukv.DOCKER_REGISTRY_SERVER,
                                                            fake_from_pause_image)

        versioned_stage = "fake_versioned_stage"

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy["to_kubelet_version"] = to_kubelet_version
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start().side_effect = [{'pause': fake_from_pause_image},
                                 {'pause': fake_to_pause_image}]
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data=containerd_read_data)
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start().return_value = versioned_stage
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start().return_value = True
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called_once()
        self.assertEqual(mock_get_k8s_images.call_count, 2)
        mock_get_k8s_images.assert_has_calls(
            [mock.call(from_kubelet_version), mock.call(to_kubelet_version.strip('v'))],
            any_order=True
        )
        self.assertEqual(mock_file_open.call_count, 2)
        mock_os_path_join.assert_called()
        mock_os_path_islink.assert_called()
        mock_os_remove.assert_called()
        mock_os_symlink.assert_called()
        mock_enable_kubelet_garbage_collection.assert_called()

    def test_update_kubelet_version_success_same_pause_images(self):
        """Test successful execution of update_kubelet_version: same pause images

        """
        from_kubelet_version = 'v1.31.5'
        to_kubelet_version = 'v1.32.2'

        fake_from_pause_image = 'same_pause_image'
        fake_to_pause_image = fake_from_pause_image

        containerd_read_data = 'sandbox_image = "%s/%s"' % (ukv.DOCKER_REGISTRY_SERVER,
                                                            fake_from_pause_image)

        versioned_stage = "fake_versioned_stage"

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy["to_kubelet_version"] = to_kubelet_version
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start().side_effect = [{'pause': fake_from_pause_image},
                                 {'pause': fake_to_pause_image}]
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data=containerd_read_data)
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start().return_value = versioned_stage
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start().return_value = True
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called_once()
        self.assertEqual(mock_get_k8s_images.call_count, 2)
        mock_get_k8s_images.assert_has_calls(
            [mock.call(from_kubelet_version), mock.call(to_kubelet_version.strip('v'))],
            any_order=True
        )
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_called()
        mock_os_path_islink.assert_called()
        mock_os_remove.assert_called()
        mock_os_symlink.assert_called()
        mock_enable_kubelet_garbage_collection.assert_called()

    def test_update_kubelet_version_failure_get_k8s_images_failed(self):
        """Test failed execution of update_kubelet_version: failed to get k8s images

        """
        from_kubelet_version = 'v1.31.5'
        to_kubelet_version = 'v1.32.2'

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy["to_kubelet_version"] = to_kubelet_version
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start().side_effect = Exception("Some kubeadm error!")
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open()
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start().return_value = True
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called_once()
        mock_get_k8s_images.assert_called()
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_failure_ctrd_config_read_failure(self):
        """Test failed execution of update_kubelet_version: failed to read containerd config

        """
        from_kubelet_version = 'v1.31.5'
        to_kubelet_version = 'v1.32.2'

        fake_from_pause_image = 'fake_from_pause_image'
        fake_to_pause_image = 'fake_to_pause_image'

        # This mocks the containerd config read failure
        containerd_read_data = ''

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy["to_kubelet_version"] = to_kubelet_version
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start().side_effect = [{'pause': fake_from_pause_image},
                                 {'pause': fake_to_pause_image}]
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data=containerd_read_data)
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start().return_value = True
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called_once()
        self.assertEqual(mock_get_k8s_images.call_count, 2)
        mock_get_k8s_images.assert_has_calls(
            [mock.call(from_kubelet_version), mock.call(to_kubelet_version.strip('v'))],
            any_order=True
        )
        mock_file_open.assert_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_failure_pause_image_update_failure(self):
        """Test failed execution of update_kubelet_version: pause image update failure

        """
        from_kubelet_version = 'v1.31.5'
        to_kubelet_version = 'v1.32.2'

        fake_from_pause_image = 'fake_from_pause_image'
        fake_to_pause_image = 'fake_to_pause_image'

        containerd_read_data = 'sandbox_image = "%s/%s"' % (ukv.DOCKER_REGISTRY_SERVER,
                                                            fake_from_pause_image)

        versioned_stage = "fake_versioned_stage"

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy["to_kubelet_version"] = to_kubelet_version
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start().side_effect = [{'pause': fake_from_pause_image},
                                 {'pause': fake_to_pause_image}]
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data=containerd_read_data)
        p = mock.patch('builtins.open', mock_file_open)
        p.start().side_effect = IOError("Fake Error!")
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start().return_value = versioned_stage
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start().return_value = True
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called_once()
        self.assertEqual(mock_get_k8s_images.call_count, 2)
        mock_get_k8s_images.assert_has_calls(
            [mock.call(from_kubelet_version), mock.call(to_kubelet_version.strip('v'))],
            any_order=True
        )
        mock_file_open.assert_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_failure_symlink_update_failure(self):
        """Test failed execution of update_kubelet_version: symlink update failure

        """
        from_kubelet_version = 'v1.31.5'
        to_kubelet_version = 'v1.32.2'

        fake_from_pause_image = 'fake_from_pause_image'
        fake_to_pause_image = 'fake_to_pause_image'

        containerd_read_data = 'sandbox_image = "%s/%s"' % (ukv.DOCKER_REGISTRY_SERVER,
                                                            fake_from_pause_image)

        versioned_stage = "fake_versioned_stage"

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy["to_kubelet_version"] = to_kubelet_version
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start().side_effect = [{'pause': fake_from_pause_image},
                                 {'pause': fake_to_pause_image}]
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data=containerd_read_data)
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start().return_value = versioned_stage
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start().return_value = True
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start().side_effect = Exception("Fake error!")
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called_once()
        self.assertEqual(mock_get_k8s_images.call_count, 2)
        mock_get_k8s_images.assert_has_calls(
            [mock.call(from_kubelet_version), mock.call(to_kubelet_version.strip('v'))],
            any_order=True
        )
        mock_file_open.assert_called()
        mock_os_path_join.assert_called()
        mock_os_path_islink.assert_called()
        mock_os_remove.assert_called()
        mock_os_symlink.assert_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_failure_system_mode_not_found(self):
        """Test failed execution of update_kubelet_version: system_mode not found

        """
        # Patch values in __init__()
        test_system_info_copy = copy.deepcopy(self.test_system_info)
        test_system_info_copy.pop("system_mode")
        self.patched_get_system_info.return_value = test_system_info_copy
        self.patched_read_version_details.return_value = self.test_version_details

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start()
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start()
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data='')
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start()
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_not_called()
        mock_get_k8s_images.assert_not_called()
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_skipped_system_mode_not_simplex(self):
        """Test skipped execution of update_kubelet_version: system_mode not found

        """
        # Patch values in __init__()
        test_system_info_copy = copy.deepcopy(self.test_system_info)
        test_system_info_copy["system_mode"] = "duplex"
        self.patched_get_system_info.return_value = test_system_info_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start()
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start()
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data='')
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start()
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        self.assertRaises(SystemExit, ukv.main)  # noqa: H202

        mock_get_current_kubelet_version.assert_not_called()
        mock_get_k8s_images.assert_not_called()
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_skipped_version_details_not_found(self):
        """Test skipped execution of update_kubelet_version: version details not found

        """
        # Patch values in __init__()
        self.patched_read_version_details.return_value = None

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start()
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start()
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data='')
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start()
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        self.assertRaises(SystemExit, ukv.main)  # noqa: H202

        mock_get_current_kubelet_version.assert_not_called()
        mock_get_k8s_images.assert_not_called()
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_failure_target_kubelet_version_not_found(self):
        """Test failed execution of update_kubelet_version: target kubelet version not found

        """
        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        self.patched_read_version_details.return_value = self.test_version_details
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy.pop("to_kubelet_version")
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start()
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start()
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data='')
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start()
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_not_called()
        mock_get_k8s_images.assert_not_called()
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_skipping_kubelet_version_already_updated(self):
        """Test skipped execution of update_kubelet_version: kubelet version already updated

        kubelet version already updated i.e. from_kubelet_version == to_kubelet_version
        """
        version = '1.32.2'
        from_kubelet_version = version
        to_kubelet_version = 'v' + version

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy["to_kubelet_version"] = to_kubelet_version
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start()
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data='')
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start()
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called()
        mock_get_k8s_images.assert_not_called()
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_failure_to_release_not_found(self):
        """Test failed execution of update_kubelet_version: to_release not found

        """
        from_kubelet_version = "1.31.5"
        to_kubelet_version = "v1.32.2"

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        self.patched_read_version_details.return_value = self.test_version_details
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy.pop("to_release")
        self.test_version_details["to_kubelet_version"] = to_kubelet_version
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start()
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data='')
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start()
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called()
        mock_get_k8s_images.assert_not_called()
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_update_kubelet_version_skipping_to_release_mismatch(self):
        """Test skipped execution of update_kubelet_version: to_release mismatched

        """
        from_kubelet_version = "1.31.5"
        to_kubelet_version = "v1.32.2"
        to_release = "FROM_TEST_SW_VERSION"

        # Patch values in __init__()
        self.patched_get_system_info.return_value = self.test_system_info
        test_version_details_copy = copy.deepcopy(self.test_version_details)
        test_version_details_copy["to_kubelet_version"] = to_kubelet_version
        test_version_details_copy["to_release"] = to_release
        self.patched_read_version_details.return_value = test_version_details_copy

        mock_get_current_kubelet_version = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_current_kubelet_version',
            mock_get_current_kubelet_version)
        p.start().return_value = from_kubelet_version
        self.addCleanup(p.stop)

        mock_get_k8s_images = mock.MagicMock()
        p = mock.patch('update_kubelet_version.KubeletVersionUpdateManager._get_k8s_images',
                       mock_get_k8s_images)
        p.start()
        self.addCleanup(p.stop)

        # Mock open inside method _update_pause_image_in_containerd
        mock_file_open = mock.mock_open(read_data='')
        p = mock.patch('builtins.open', mock_file_open)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_join = mock.MagicMock()
        p = mock.patch('os.path.join', mock_os_path_join)
        p.start()
        self.addCleanup(p.stop)

        mock_os_path_islink = mock.MagicMock()
        p = mock.patch('os.path.islink', mock_os_path_islink)
        p.start()
        self.addCleanup(p.stop)

        mock_os_remove = mock.MagicMock()
        p = mock.patch('os.remove', mock_os_remove)
        p.start()
        self.addCleanup(p.stop)

        mock_os_symlink = mock.MagicMock()
        p = mock.patch('os.symlink', mock_os_symlink)
        p.start()
        self.addCleanup(p.stop)

        mock_enable_kubelet_garbage_collection = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._enable_kubelet_garbage_collection',
            mock_enable_kubelet_garbage_collection)
        p.start()
        self.addCleanup(p.stop)

        ukv.main()

        mock_get_current_kubelet_version.assert_called()
        mock_get_k8s_images.assert_not_called()
        mock_file_open.assert_not_called()
        mock_os_path_join.assert_not_called()
        mock_os_path_islink.assert_not_called()
        mock_os_remove.assert_not_called()
        mock_os_symlink.assert_not_called()
        mock_enable_kubelet_garbage_collection.assert_not_called()

    def test_pull_pause_image_success(self):
        """Test successful execution of _pull_pause_image

        """
        self.patched_get_system_info.return_value = self.test_system_info
        self.patched_read_version_details.return_value = self.test_version_details

        fake_creds = {'username': 'fake_username', 'password': 'fake_password'}

        mock_get_local_docker_registry_auth = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_local_docker_registry_auth',
            mock_get_local_docker_registry_auth)
        p.start().return_value = fake_creds
        self.addCleanup(p.stop)

        mock_pull_image_to_crictl = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._pull_image_to_crictl',
            mock_pull_image_to_crictl)
        p.start().return_value = True
        self.addCleanup(p.stop)

        manager = ukv.KubeletVersionUpdateManager()
        manager._pull_pause_image("fake_pause_image")

        mock_get_local_docker_registry_auth.assert_called()
        mock_pull_image_to_crictl.assert_called()

    def test_pull_pause_image_failure(self):
        """Test failed execution of _pull_pause_image

        """
        self.patched_get_system_info.return_value = self.test_system_info
        self.patched_read_version_details.return_value = self.test_version_details

        fake_creds = {'username': 'fake_username', 'password': 'fake_password'}

        mock_get_local_docker_registry_auth = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._get_local_docker_registry_auth',
            mock_get_local_docker_registry_auth)
        p.start().return_value = fake_creds
        self.addCleanup(p.stop)

        mock_pull_image_to_crictl = mock.MagicMock()
        p = mock.patch(
            'update_kubelet_version.KubeletVersionUpdateManager._pull_image_to_crictl',
            mock_pull_image_to_crictl)
        p.start().return_value = False
        self.addCleanup(p.stop)

        manager = ukv.KubeletVersionUpdateManager()
        self.assertRaises(Exception, manager._pull_pause_image, "fake_pause_image")  # noqa: H202

        mock_get_local_docker_registry_auth.assert_called()
        mock_pull_image_to_crictl.assert_called()
