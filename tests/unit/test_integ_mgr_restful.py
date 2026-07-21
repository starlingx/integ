#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for ceph mgr-restful-plugin module."""

import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

# Mock heavy external deps before import
sys.modules.setdefault('daemon', MagicMock())
sys.modules.setdefault('psutil', MagicMock())
sys.modules.setdefault('requests', MagicMock())

import psutil

_MGR_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'ceph', 'ceph', 'debian',
    os.environ.get('STX_DEBIAN_VARIANT', 'bullseye'),
    'files',
    'mgr-restful-plugin.py')


def _load_module():
    """Load mgr-restful-plugin.py as a module."""
    spec = importlib.util.spec_from_file_location(
        'mgr_restful_plugin', _MGR_PATH)
    mod = importlib.util.module_from_spec(spec)
    mock_handler = MagicMock()
    mock_handler.level = 0
    with patch('socket.gethostname', return_value='controller-0'), \
         patch('logging.FileHandler', return_value=mock_handler):
        spec.loader.exec_module(mod)
    return mod


class TestPsutilTerminateKill(unittest.TestCase):
    """Tests for psutil_terminate_kill function."""


class TestServiceMonitorInit(unittest.TestCase):
    """Tests for ServiceMonitor initialization."""

    def test_service_monitor_init(self):
        """Verify ServiceMonitor initializes with expected attrs."""
        mod = _load_module()
        monitor = mod.ServiceMonitor()
        self.assertIsNone(monitor.monitor)
        self.assertIsNone(monitor.command)
        self.assertIsNone(monitor.ceph_mgr)
        self.assertEqual(monitor.ceph_mgr_failure_count, 0)
        self.assertEqual(monitor.ping_failure_count, 0)

    def test_get_ceph_executable_default(self):
        """Verify get_ceph_executable.

        Returns /usr/bin/ceph when local missing.
        """
        mod = _load_module()
        monitor = mod.ServiceMonitor()
        with patch('os.path.exists', return_value=False):
            result = monitor.get_ceph_executable()
        self.assertEqual(result, '/usr/bin/ceph')

    def test_get_ceph_executable_local(self):
        """Verify get_ceph_executable returns local path when exists."""
        mod = _load_module()
        monitor = mod.ServiceMonitor()
        with patch('os.path.exists', return_value=True):
            result = monitor.get_ceph_executable()
        self.assertEqual(result, '/usr/local/bin/ceph')


if __name__ == '__main__':
    unittest.main()
