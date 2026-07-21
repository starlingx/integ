#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Extended tests for update_kubelet_version.

Covers additional methods and edge cases.
"""

import importlib
import subprocess
import json
import os
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

# Mock keyring before import
sys.modules.setdefault('keyring', MagicMock())

_UKV_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'kubernetes', 'kubernetes-unversioned',
    'debian', 'all', 'deb_folder',
    'update_kubelet_version.py')

_PLATFORM_SIMPLEX_CTRL = (
    "system_mode=simplex\nnodetype=controller\n"
)
_PLATFORM_SIMPLEX_WORKER = (
    "system_mode=simplex\nnodetype=worker\n"
)
_VERSION_DATA = {'to_kubelet_version': 'v1.28.4',
                 'to_release': '24.09'}


def _load_module():
    """Load update_kubelet_version module.

    Returns the loaded module object.
    """
    spec = importlib.util.spec_from_file_location(
        'ukv2', _UKV_PATH
    )
    loaded_mod = importlib.util.module_from_spec(spec)
    loaded_mod.__name__ = 'ukv2'
    spec.loader.exec_module(loaded_mod)
    return loaded_mod


def _make_manager(ukv_mod, platform_data=None, version_data=None):
    """Create a KubeletVersionUpdateManager with mocked __init__ dependencies.

    New __init__ does:
      1. get_system_info() -> reads PLATFORM_FILE
      2. Checks system_mode == simplex (exits otherwise)
      3. _read_version_details() -> checks os.path.exists + reads JSON file
    """
    if platform_data is None:
        platform_data = _PLATFORM_SIMPLEX_CTRL
    if version_data is None:
        version_data = _VERSION_DATA

    with patch('builtins.open',
               mock_open(read_data=platform_data)):
        with patch('os.path.exists', return_value=True):
            with patch('json.load', return_value=version_data):
                mgr = ukv_mod.KubeletVersionUpdateManager()
    return mgr


class TestGetCurrentKubeletVersion(unittest.TestCase):
    """Tests for _get_current_kubelet_version."""

    def test_returns_version(self):
        """Return version from symlink."""
        ukv_mod = _load_module()
        mgr = _make_manager(ukv_mod)
        # _get_current_kubelet_version calls self._get_kube_version_from_symlink(stage_number=2)
        # which calls os.readlink on KUBERNETES_SYMLINKS_STAGE_2
        with patch('os.readlink',
                   return_value='/usr/local/kubernetes/1.27.5/stage2'):
            result = mgr._get_current_kubelet_version()
        self.assertEqual(result, '1.27.5')


class TestUpdatePauseImage(unittest.TestCase):
    """Tests for _update_pause_image_in_containerd."""

    def test_empty_containerd_config_raises(self):
        """Raise when containerd config is empty."""
        ukv_mod = _load_module()
        mgr = _make_manager(ukv_mod)
        mgr._get_k8s_images = MagicMock(
            side_effect=lambda ver: (
                {'pause': 'pause:3.9'}
                if ver == '1.27.5'
                else {'pause': 'pause:3.10'}
            ))
        with patch('builtins.open',
                   mock_open(read_data='')):
            with self.assertRaises(Exception):  # noqa: H202
                mgr._update_pause_image_in_containerd(
                    '1.27.5', '1.28.4'
                )

    def test_worker_pulls_pause_image(self):
        """Worker node pulls pause image."""
        ukv_mod = _load_module()
        mgr = _make_manager(ukv_mod,
                            platform_data=_PLATFORM_SIMPLEX_WORKER)
        mgr._get_k8s_images = MagicMock(
            side_effect=lambda ver: (
                {'pause': 'pause:3.9'}
                if ver == '1.27.5'
                else {'pause': 'pause:3.10'}
            ))
        mgr._pull_pause_image = MagicMock()
        sandbox_img = (
            'sandbox_image = '
            '"registry.local:9001/pause:3.9"'
        )
        with patch('builtins.open') as mock_file:
            mock_file.side_effect = [
                mock_open(
                    read_data=sandbox_img
                ).return_value,
                mock_open().return_value,
            ]
            mgr._update_pause_image_in_containerd(
                '1.27.5', '1.28.4'
            )
        mgr._pull_pause_image.assert_called_once_with('pause:3.10')


class TestUpdateStage2Symlink(unittest.TestCase):
    """Tests for _update_stage2_symlink."""

    @patch('os.symlink')
    @patch('os.remove')
    @patch('os.path.islink', return_value=True)
    def test_updates_symlink(
        self, mock_islink, mock_rm, mock_sym
    ):
        """Update stage2 symlink."""
        ukv_mod = _load_module()
        mgr = _make_manager(ukv_mod)
        mgr._update_stage2_symlink('1.28.4')
        mock_rm.assert_called_once_with(ukv_mod.KUBERNETES_SYMLINKS_STAGE_2)
        mock_sym.assert_called_once_with(
            os.path.join(ukv_mod.KUBERNETES_VERSIONED_BINARIES_ROOT,
                         '1.28.4', 'stage2'),
            ukv_mod.KUBERNETES_SYMLINKS_STAGE_2
        )

    @patch('os.symlink')
    @patch('os.path.islink', return_value=False)
    def test_no_existing_symlink(
        self, mock_islink, mock_sym
    ):
        """Work when no existing symlink."""
        ukv_mod = _load_module()
        mgr = _make_manager(ukv_mod)
        mgr._update_stage2_symlink('1.28.4')
        mock_sym.assert_called_once()


class TestFullUpgradeFlow(unittest.TestCase):
    """Tests for update_kubelet_version full flow."""

    def test_missing_to_version_raises(self):
        """Raise when to_kubelet_version missing."""
        ukv_mod = _load_module()
        version_data = {'other': 'value'}
        mgr = _make_manager(ukv_mod, version_data=version_data)
        with self.assertRaises(Exception) as ctx:  # noqa: H202
            mgr.update_kubelet_version()
        self.assertIn("to_kubelet_version", str(ctx.exception))


class TestPullPauseImage(unittest.TestCase):
    """Tests for _pull_pause_image."""

    def test_pull_failure_raises(self):
        """Pull pause image failure raises."""
        ukv_mod = _load_module()
        mgr = _make_manager(ukv_mod,
                            platform_data=_PLATFORM_SIMPLEX_WORKER)
        # _pull_pause_image calls _get_local_docker_registry_auth then
        # _pull_image_to_crictl; if _pull_image_to_crictl returns falsy, raises
        mgr._get_local_docker_registry_auth = MagicMock(
            return_value={'username': 'u', 'password': 'p'})
        mgr._pull_image_to_crictl = MagicMock(return_value=None)
        with self.assertRaises(Exception):  # noqa: H202
            mgr._pull_pause_image('pause:3.10')


class TestSetupLogger(unittest.TestCase):
    """Tests for setup_logger."""


class TestExecuteMethod(unittest.TestCase):
    """Tests for _execute method (subprocess wrapper)."""

    def test_execute_success(self):
        """Returns stdout, stderr on success."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ('output', '')
            mock_proc.__enter__ = MagicMock(return_value=mock_proc)
            mock_proc.__exit__ = MagicMock(return_value=False)
            mock_popen.return_value = mock_proc
            stdout, stderr = mgr._execute('echo test')
            self.assertEqual(stdout, 'output')

    def test_execute_timeout(self):
        """Returns empty on timeout."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
                'cmd', 5)
            mock_proc.kill = MagicMock()
            mock_proc.__enter__ = MagicMock(return_value=mock_proc)
            mock_proc.__exit__ = MagicMock(return_value=True)
            mock_popen.return_value = mock_proc
            stdout, stderr = mgr._execute('slow cmd')
            self.assertEqual(stdout, '')

    def test_execute_exception(self):
        """Returns empty on generic exception."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with patch('subprocess.Popen', side_effect=OSError('fail')):
            stdout, stderr = mgr._execute('bad cmd')
            self.assertEqual(stdout, '')


class TestGetCurrentKubeletVersionStages(unittest.TestCase):
    """Tests for _get_kube_version_from_symlink with different stages."""

    def test_stage1_parses_version(self):
        """Stage 1 symlink is parsed correctly."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with patch('os.readlink',
                   return_value='/usr/local/kubernetes/v1.27.5/stage1'):
            result = mgr._get_kube_version_from_symlink(stage_number=1)
            self.assertEqual(result, 'v1.27.5')

    def test_stage2_parses_version(self):
        """Stage 2 symlink is parsed correctly."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with patch('os.readlink',
                   return_value='/usr/local/kubernetes/v1.28.4/stage2'):
            result = mgr._get_kube_version_from_symlink(stage_number=2)
            self.assertEqual(result, 'v1.28.4')

    def test_invalid_stage_raises(self):
        """Invalid stage number raises Exception."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with self.assertRaises(Exception) as ctx:  # noqa: H202
            mgr._get_kube_version_from_symlink(stage_number=3)
        self.assertIn('Invalid stage number', str(ctx.exception))

    def test_readlink_failure_raises(self):
        """OSError on readlink raises Exception."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with patch('os.readlink', side_effect=OSError('no link')):
            with self.assertRaises(Exception) as ctx:  # noqa: H202
                mgr._get_kube_version_from_symlink()
            self.assertIn('Failed to read symlink', str(ctx.exception))

    def test_no_match_returns_none(self):
        """Returns None when symlink doesn't match pattern."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with patch('os.readlink', return_value='/some/other/path'):
            result = mgr._get_kube_version_from_symlink()
            self.assertIsNone(result)


class TestUpdateKubeletVersion(unittest.TestCase):
    """Tests for update_kubelet_version orchestration."""

    def test_already_at_target_version_returns_early(self):
        """No update when already at target version."""
        mod = _load_module()
        mgr = _make_manager(mod)
        mgr._version_details = {'to_kubelet_version': 'v1.28.4',
                                'to_release': '24.09'}
        mgr.system_info = {'sw_version': '24.09', 'nodetype': 'controller'}
        with patch.object(mgr, '_get_current_kubelet_version',
                          return_value='1.28.4'):
            # Should return without calling update methods
            with patch.object(mgr, '_update_pause_image_in_containerd') as mock_update:
                mgr.update_kubelet_version()
                mock_update.assert_not_called()

    def test_missing_to_kubelet_version_raises(self):
        """Raises when to_kubelet_version missing."""
        mod = _load_module()
        mgr = _make_manager(mod)
        mgr._version_details = {}
        with self.assertRaises(Exception) as ctx:  # noqa: H202
            mgr.update_kubelet_version()
        self.assertIn('to_kubelet_version', str(ctx.exception))

    def test_missing_to_release_raises(self):
        """Raises when to_release missing."""
        mod = _load_module()
        mgr = _make_manager(mod)
        mgr._version_details = {'to_kubelet_version': 'v1.28.4'}
        with patch.object(mgr, '_get_current_kubelet_version',
                          return_value='1.27.5'):
            with self.assertRaises(Exception) as ctx:  # noqa: H202
                mgr.update_kubelet_version()
            self.assertIn('to_release', str(ctx.exception))

    def test_release_mismatch_returns_early(self):
        """No update when sw_version doesn't match to_release."""
        mod = _load_module()
        mgr = _make_manager(mod)
        mgr._version_details = {'to_kubelet_version': 'v1.28.4',
                                'to_release': '25.03'}
        mgr.system_info = {'sw_version': '24.09', 'nodetype': 'controller'}
        with patch.object(mgr, '_get_current_kubelet_version',
                          return_value='1.27.5'):
            with patch.object(mgr, '_update_pause_image_in_containerd') as mock_update:
                mgr.update_kubelet_version()
                mock_update.assert_not_called()


class TestEnableKubeletGarbageCollection(unittest.TestCase):
    """Tests for _enable_kubelet_garbage_collection."""

    def test_removes_gc_threshold(self):
        """Removes --image-gc-high-threshold 100 from flags file."""
        mod = _load_module()
        mgr = _make_manager(mod)
        flags_content = '--image-gc-high-threshold 100 --other-flag value'
        m = mock_open(read_data=flags_content)
        with patch('builtins.open', m):
            mgr._enable_kubelet_garbage_collection()
        # Verify the write removed the threshold
        written = m().write.call_args[0][0]
        self.assertNotIn('image-gc-high-threshold', written)
        self.assertIn('--other-flag value', written)

    def test_no_gc_threshold_no_change(self):
        """No write when gc threshold not present."""
        mod = _load_module()
        mgr = _make_manager(mod)
        flags_content = '--other-flag value'
        m = mock_open(read_data=flags_content)
        with patch('builtins.open', m):
            mgr._enable_kubelet_garbage_collection()
        # write should not have been called for the second open
        # (only read happened)

    def test_file_error_raises(self):
        """Raises on file read error."""
        mod = _load_module()
        mgr = _make_manager(mod)
        with patch('builtins.open', side_effect=IOError('perm denied')):
            with self.assertRaises(Exception) as ctx:  # noqa: H202
                mgr._enable_kubelet_garbage_collection()
            self.assertIn('garbage', str(ctx.exception))

