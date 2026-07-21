#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for update_kubelet_version module."""

import importlib
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
    'kubernetes', 'kubernetes-unversioned', 'debian', 'all',
    'deb_folder', 'update_kubelet_version.py')

_PLATFORM_SIMPLEX_CTRL = (
    "system_mode=simplex\nnodetype=controller\n"
)
_VERSION_DATA = json.dumps({'to_kubelet_version': 'v1.28.4',
                            'to_release': '24.09'})


def _load_module():
    """Load update_kubelet_version.py as a module."""
    spec = importlib.util.spec_from_file_location(
        'update_kubelet_version', _UKV_PATH)
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = 'update_kubelet_version'
    spec.loader.exec_module(mod)
    return mod


def _create_manager(mod, platform_data=None, version_data=None):
    """Helper to create KubeletVersionUpdateManager with proper mocks.

    The new __init__ reads platform.conf, checks system_mode,
    then reads the kubelet version file via _read_version_details().
    """
    if platform_data is None:
        platform_data = _PLATFORM_SIMPLEX_CTRL
    if version_data is None:
        version_data = _VERSION_DATA

    with patch('builtins.open',
               mock_open(read_data=platform_data)):
        with patch.object(mod.os.path, 'exists', return_value=True):
            with patch.object(mod, '_UKV_PATH' if hasattr(mod, '_UKV_PATH') else '__name__',
                              mod.__name__):
                # Need to mock the version file read separately
                with patch.object(mod.json, 'load',
                                  return_value=json.loads(version_data)):
                    mgr = mod.KubeletVersionUpdateManager()
    return mgr


class TestGetSystemInfo(unittest.TestCase):
    """Tests for get_system_info function."""

    def test_get_system_info(self):
        """Test parsing platform.conf."""
        mod = _load_module()
        platform_content = (
            "system_mode=simplex\n"
            "system_type=All-in-one\n"
            "nodetype=controller\n"
            "subfunction=controller,worker\n"
            "sw_version=24.09\n"
            "uuid=test-uuid-1234\n"
        )
        with patch('builtins.open',
                   mock_open(read_data=platform_content)):
            info = mod.get_system_info()
        self.assertEqual(info['system_mode'], 'simplex')
        self.assertEqual(info['system_type'], 'All-in-one')
        self.assertEqual(info['nodetype'], 'controller')
        self.assertEqual(info['sw_version'], '24.09')
        self.assertEqual(info['uuid'], 'test-uuid-1234')

    def test_get_system_info_missing_fields(self):
        """Test parsing platform.conf with missing fields."""
        mod = _load_module()
        platform_content = "system_mode=simplex\n"
        with patch('builtins.open',
                   mock_open(read_data=platform_content)):
            info = mod.get_system_info()
        self.assertEqual(info['system_mode'], 'simplex')
        self.assertIsNone(info['nodetype'])


class TestKubeletVersionUpdateManager(unittest.TestCase):
    """Tests for KubeletVersionUpdateManager class."""

    def test_init(self):
        """Test manager initialization on simplex with version file."""
        mod = _load_module()
        version_details = {'to_kubelet_version': 'v1.28.4',
                           'to_release': '24.09'}
        with patch('builtins.open',
                   mock_open(read_data=_PLATFORM_SIMPLEX_CTRL)):
            with patch('os.path.exists', return_value=True):
                with patch('json.load', return_value=version_details):
                    mgr = mod.KubeletVersionUpdateManager()
        self.assertIsNotNone(mgr.system_info)
        self.assertEqual(mgr.system_info['system_mode'], 'simplex')
        self.assertEqual(mgr._version_details, version_details)

    def test_read_version_details(self):
        """Test reading kubelet version file."""
        mod = _load_module()
        version_details = {'to_kubelet_version': 'v1.28.4',
                           'to_release': '24.09'}
        # Create manager first
        with patch('builtins.open',
                   mock_open(read_data=_PLATFORM_SIMPLEX_CTRL)):
            with patch('os.path.exists', return_value=True):
                with patch('json.load', return_value=version_details):
                    mgr = mod.KubeletVersionUpdateManager()
        # Now test _read_version_details independently
        new_version_data = {'to_kubelet_version': 'v1.29.0',
                            'to_release': '25.03'}
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open()):
                with patch('json.load', return_value=new_version_data):
                    details = mgr._read_version_details()
        self.assertEqual(details['to_kubelet_version'], 'v1.29.0')

    def test_update_kubelet_non_simplex_exits(self):
        """Test __init__ exits for non-simplex system."""
        mod = _load_module()
        platform_duplex = "system_mode=duplex\nnodetype=controller\n"
        with patch('builtins.open',
                   mock_open(read_data=platform_duplex)):
            with self.assertRaises(SystemExit) as ctx:
                mod.KubeletVersionUpdateManager()
            self.assertEqual(ctx.exception.code, 0)

    def test_update_kubelet_no_system_mode_raises(self):
        """Test __init__ raises when system_mode missing."""
        mod = _load_module()
        platform_no_mode = "nodetype=controller\n"
        with patch('builtins.open',
                   mock_open(read_data=platform_no_mode)):
            with self.assertRaises(Exception) as ctx:  # noqa: H202
                mod.KubeletVersionUpdateManager()
            self.assertIn("system mode not found", str(ctx.exception))

    def test_update_kubelet_no_version_file_exits(self):
        """Test __init__ exits when kubelet version file not found."""
        mod = _load_module()
        with patch('builtins.open',
                   mock_open(read_data=_PLATFORM_SIMPLEX_CTRL)):
            with patch('os.path.exists', return_value=False):
                with self.assertRaises(SystemExit) as ctx:
                    mod.KubeletVersionUpdateManager()
                self.assertEqual(ctx.exception.code, 0)


class TestMainFunction(unittest.TestCase):
    """Tests for main function."""

    def test_main_success(self):
        """Test main runs without error on non-simplex (exits cleanly)."""
        mod = _load_module()
        # Non-simplex causes sys.exit(0) in __init__
        platform_duplex = "system_mode=duplex\nnodetype=controller\n"
        with patch.object(mod, 'setup_logger'):
            with patch('builtins.open',
                       mock_open(read_data=platform_duplex)):
                # main() catches SystemExit? No - it catches Exception.
                # SystemExit inherits BaseException, not Exception.
                # So sys.exit(0) will propagate out of main().
                with self.assertRaises(SystemExit) as ctx:
                    mod.main()
                self.assertEqual(ctx.exception.code, 0)

    def test_main_failure(self):
        """Test main handles exception without re-raising."""
        mod = _load_module()
        with patch.object(mod, 'setup_logger'):
            with patch.object(mod, 'KubeletVersionUpdateManager',
                              side_effect=Exception("fail")):
                # main() catches Exception and logs it, does not re-raise
                mod.main()


if __name__ == '__main__':
    unittest.main()
