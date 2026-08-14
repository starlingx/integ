#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Extended tests for mgr-restful-plugin.

Patches subprocess.check_output
to test run_with_timeout and all methods that depend on it."""

import importlib
import os
import signal
import subprocess
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

sys.modules.setdefault('daemon', MagicMock())
sys.modules.setdefault('psutil', MagicMock())
sys.modules.setdefault('requests', MagicMock())

import psutil
import socket

_MGR_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'ceph', 'ceph', 'debian',
    os.environ.get('STX_DEBIAN_VARIANT', 'bullseye'),
    'files',
    'mgr-restful-plugin.py')


def _load_module():
    """Load the module under test.

    Returns:
        The loaded module object.
    """
    spec = importlib.util.spec_from_file_location('mrp2', _MGR_PATH)
    mod = importlib.util.module_from_spec(spec)
    mock_handler = MagicMock()
    mock_handler.level = 0
    with patch('socket.gethostname', return_value='ctrl-0'), \
         patch('logging.FileHandler', return_value=mock_handler):
        spec.loader.exec_module(mod)
    return mod


def _create_monitor():
    """Create a ServiceMonitor instance.

    Returns:
        Tuple of (module, monitor_instance).
    """
    loaded_mod = _load_module()
    monitor = loaded_mod.ServiceMonitor()
    return loaded_mod, monitor


class TestRunWithTimeout(unittest.TestCase):
    """Tests for run_with_timeout static method."""

    def test_success(self):
        """Returns stripped output on success."""
        mod, monitor = _create_monitor()
        with patch.object(mod.subprocess, 'check_output',
                          return_value='output\n'):
            result = mod.ServiceMonitor.run_with_timeout(
                ['echo', 'test'], timeout=10)
        self.assertEqual(result, 'output')

    def test_timeout_raises(self):
        """Raises CommandTimeout on retcode 124."""
        mod, monitor = _create_monitor()
        err = subprocess.CalledProcessError(124, 'cmd', output='')
        with patch.object(mod.subprocess, 'check_output',
                          side_effect=err):
            with self.assertRaises(mod.CommandTimeout):
                mod.ServiceMonitor.run_with_timeout(['cmd'], timeout=10)

    def test_failure_raises(self):
        """Raises CommandFailed on other errors."""
        mod, monitor = _create_monitor()
        err = subprocess.CalledProcessError(1, 'cmd', output='err')
        with patch.object(mod.subprocess, 'check_output',
                          side_effect=err):
            with self.assertRaises(mod.CommandFailed):
                mod.ServiceMonitor.run_with_timeout(['cmd'], timeout=10)


class TestCephFsidGet(unittest.TestCase):
    """Tests for ceph_fsid_get."""

    def test_returns_fsid(self):
        """Returns cluster fsid."""
        mod, monitor = _create_monitor()
        with patch.object(mod.subprocess, 'check_output',
                          return_value='abc-123\n'):
            result = monitor.ceph_fsid_get()
        self.assertEqual(result, 'abc-123')


class TestCephMgrHasAuth(unittest.TestCase):
    """Tests for ceph_mgr_has_auth."""

    @patch('os.makedirs')
    def test_has_auth_true(self, mock_mkdirs):
        """Returns True when auth key exists."""
        mod, monitor = _create_monitor()
        with patch.object(mod.subprocess, 'check_output',
                          return_value='key\n'):
            self.assertTrue(monitor.ceph_mgr_has_auth())

    @patch('os.makedirs')
    def test_has_auth_false_enoent(self, mock_mkdirs):
        """Returns False when ENOENT in error."""
        mod, monitor = _create_monitor()
        err = subprocess.CalledProcessError(
            1, 'cmd', output='ENOENT: entity not found')
        with patch.object(mod.subprocess, 'check_output',
                          side_effect=err):
            self.assertFalse(monitor.ceph_mgr_has_auth())

    @patch('os.makedirs')
    def test_has_auth_reraises_other(self, mock_mkdirs):
        """Re-raises non-ENOENT CommandFailed."""
        mod, monitor = _create_monitor()
        err = subprocess.CalledProcessError(
            1, 'cmd', output='permission denied')
        with patch.object(mod.subprocess, 'check_output',
                          side_effect=err):
            with self.assertRaises(mod.CommandFailed):
                monitor.ceph_mgr_has_auth()


class TestCephMgrAuthCreate(unittest.TestCase):
    """Tests for ceph_mgr_auth_create."""


class TestCephMgrIsRunning(unittest.TestCase):
    """Tests for ceph_mgr_is_running."""

    def test_running(self):
        """True when process alive (wait raises TimeoutExpired)."""
        mod, monitor = _create_monitor()
        monitor.ceph_mgr = MagicMock()
        # psutil is mocked, so TimeoutExpired is a MagicMock class
        # We need wait() to raise it
        timeout_exc = type('TimeoutExpired', (Exception,), {})
        mod.psutil.TimeoutExpired = timeout_exc
        monitor.ceph_mgr.wait.side_effect = timeout_exc(0)
        self.assertTrue(monitor.ceph_mgr_is_running())

    def test_not_running_none(self):
        """None when no process."""
        mod, monitor = _create_monitor()
        monitor.ceph_mgr = None
        self.assertIsNone(monitor.ceph_mgr_is_running())

    def test_not_running_exited(self):
        """False when process exited (wait returns)."""
        mod, monitor = _create_monitor()
        monitor.ceph_mgr = MagicMock()
        monitor.ceph_mgr.wait.return_value = 0
        self.assertFalse(monitor.ceph_mgr_is_running())


class TestCephMgrStart(unittest.TestCase):
    """Tests for ceph_mgr_start."""

    def test_start_success(self):
        """Starts ceph-mgr process."""
        mod, monitor = _create_monitor()
        monitor.ceph_mgr = None  # not running
        monitor.stop_unmanaged_ceph_mgr = MagicMock()
        mock_proc = MagicMock()
        psutil.Popen = MagicMock(return_value=mock_proc)
        with patch('time.sleep'), \
             patch('builtins.open', MagicMock()):
            monitor.ceph_mgr_start()
        self.assertIsNotNone(monitor.ceph_mgr)

    def test_start_oserror_raises(self):
        """Raises CephMgrStartFailed on OSError."""
        mod, monitor = _create_monitor()
        monitor.ceph_mgr = None
        monitor.stop_unmanaged_ceph_mgr = MagicMock()
        psutil.Popen = MagicMock(side_effect=OSError('fail'))
        with patch('builtins.open', MagicMock()):
            with self.assertRaises(mod.CephMgrStartFailed):
                monitor.ceph_mgr_start()


class TestCephMgrStopRestart(unittest.TestCase):
    """Tests for ceph_mgr_stop and restart."""

    def test_uptime_no_start(self):
        """Uptime 0 when no start date."""
        mod, monitor = _create_monitor()
        monitor.ceph_mgr_start_date = None
        self.assertEqual(monitor.ceph_mgr_uptime(), 0)


class TestRestfulPluginServerPort(unittest.TestCase):
    """Tests for server port methods."""

    def test_has_port_true(self):
        """True when port is set."""
        mod, monitor = _create_monitor()
        with patch.object(mod.subprocess, 'check_output',
                          return_value='7999'):
            self.assertTrue(monitor.restful_plugin_has_server_port())

    def test_has_port_false(self):
        """False when port doesn't match."""
        mod, monitor = _create_monitor()
        err = subprocess.CalledProcessError(1, 'cmd', output='err')
        with patch.object(mod.subprocess, 'check_output',
                          side_effect=err), \
             patch('builtins.open', MagicMock()):
            self.assertFalse(monitor.restful_plugin_has_server_port())


class TestRestfulPluginAdminKey(unittest.TestCase):
    """Tests for admin key methods."""

    def test_has_key_true(self):
        """True when key exists."""
        mod, monitor = _create_monitor()
        with patch.object(mod.subprocess, 'check_output',
                          return_value='key-data\n'):
            self.assertTrue(monitor.restful_plugin_has_admin_key())

    def test_has_key_false(self):
        """False on CommandFailed."""
        mod, monitor = _create_monitor()
        err = subprocess.CalledProcessError(1, 'cmd', output='err')
        with patch.object(mod.subprocess, 'check_output',
                          side_effect=err):
            self.assertFalse(monitor.restful_plugin_has_admin_key())


class TestRestfulPluginCertificate(unittest.TestCase):
    """Tests for certificate methods."""

    def test_has_cert_true(self):
        """True when cert exists."""
        mod, monitor = _create_monitor()
        with patch.object(mod.subprocess, 'check_output',
                          return_value='-----BEGIN CERT-----\ndata\n'):
            self.assertTrue(monitor.restful_plugin_has_certificate())

    def test_has_cert_false(self):
        """False on CommandFailed."""
        mod, monitor = _create_monitor()
        err = subprocess.CalledProcessError(1, 'cmd', output='err')
        with patch.object(mod.subprocess, 'check_output',
                          side_effect=err):
            self.assertFalse(monitor.restful_plugin_has_certificate())


class TestRestfulPluginEnable(unittest.TestCase):
    """Tests for enable/disable methods."""

    def test_is_enabled_true(self):
        """True when restful in module list."""
        mod, monitor = _create_monitor()
        json_out = '{"enabled_modules": ["restful", "dashboard"]}'
        with patch.object(mod.subprocess, 'check_output',
                          return_value=json_out), \
             patch('builtins.open', MagicMock()):
            self.assertTrue(monitor.restful_plugin_is_enabled())

    def test_is_enabled_false(self):
        """False when restful not in list."""
        mod, monitor = _create_monitor()
        json_out = '{"enabled_modules": ["dashboard"]}'
        with patch.object(mod.subprocess, 'check_output',
                          return_value=json_out), \
             patch('builtins.open', MagicMock()):
            self.assertFalse(monitor.restful_plugin_is_enabled())


class TestRestfulPluginUrl(unittest.TestCase):
    """Tests for URL methods."""

    def test_get_url(self):
        """Gets restful plugin URL from JSON output."""
        mod, monitor = _create_monitor()
        json_out = '{"restful": "https://ceph-restful:7999/"}'
        monitor.request_update_plugin_url = MagicMock()
        with patch.object(mod.subprocess, 'check_output',
                          return_value=json_out), \
             patch('builtins.open', MagicMock()):
            monitor.restful_plugin_get_url()
        self.assertIn('7999', monitor.restful_plugin_url)


class TestRestfulPluginPing(unittest.TestCase):
    """Tests for ping method."""

    def test_ping_no_url_raises(self):
        """Raises when no URL."""
        mod, monitor = _create_monitor()
        monitor.restful_plugin_url = ''
        with self.assertRaises(mod.RestApiPingFailed):
            monitor.restful_plugin_ping()

    def test_ping_no_cert_raises(self):
        """Raises when no certificate."""
        mod, monitor = _create_monitor()
        monitor.restful_plugin_url = 'https://localhost:7999'
        monitor.certificate = ''
        with self.assertRaises(mod.RestApiPingFailed):
            monitor.restful_plugin_ping()

    def test_ping_not_ok_raises(self):
        """Raises when no URL set."""
        mod, monitor = _create_monitor()
        monitor.restful_plugin_url = ''
        monitor.certificate = '/tmp/cert.pem'
        with self.assertRaises(mod.RestApiPingFailed):
            monitor.restful_plugin_ping()


class TestDisableCertCheck(unittest.TestCase):
    """Tests for disable_certificate_check."""


class TestSendResponse(unittest.TestCase):
    """Tests for send_response."""

    def test_send_ok(self):
        """Sends encoded response."""
        mod = _load_module()
        client = MagicMock()
        mod.ServiceMonitor.send_response(client, b'status', 'OK')
        client.send.assert_called_with(b'OK')


class TestStatusMethod(unittest.TestCase):
    """Tests for status method."""

    def test_no_url_low_failures_ok(self):
        """OK when starting up."""
        mod, monitor = _create_monitor()
        monitor.restful_plugin_url = ''
        monitor.ceph_mgr_failure_count = 0
        monitor.ping_failure_count = 0
        self.assertEqual(monitor.status(), 'OK')

    def test_no_url_high_failures_err(self):
        """ERR.down when too many failures."""
        mod, monitor = _create_monitor()
        monitor.restful_plugin_url = ''
        monitor.ceph_mgr_failure_count = 999
        monitor.ping_failure_count = 999
        self.assertEqual(monitor.status(), 'ERR.down')

    def test_url_ping_ok(self):
        """OK when ping succeeds."""
        mod, monitor = _create_monitor()
        monitor.restful_plugin_url = 'https://localhost:7999'
        monitor.certificate = '/tmp/cert.pem'
        mock_resp = MagicMock()
        mock_resp.ok = True
        mod.requests.request = MagicMock(return_value=mock_resp)
        self.assertEqual(monitor.status(), 'OK')

    def test_url_ping_fail_low_count_ok(self):
        """OK when ping fails but counts low."""
        mod, monitor = _create_monitor()
        monitor.restful_plugin_url = 'https://localhost:7999'
        monitor.certificate = ''
        monitor.ceph_mgr_failure_count = 0
        monitor.ping_failure_count = 0
        self.assertEqual(monitor.status(), 'OK')

    def test_url_ping_fail_high_count_err(self):
        """ERR when ping fails and counts high."""
        mod, monitor = _create_monitor()
        monitor.restful_plugin_url = 'https://localhost:7999'
        monitor.certificate = ''
        monitor.ceph_mgr_failure_count = 999
        monitor.ping_failure_count = 999
        self.assertEqual(monitor.status(), 'ERR.ping_failed')


class TestStopMethod(unittest.TestCase):
    """Tests for stop method."""


class TestSetupLogging(unittest.TestCase):
    """Tests for setup_logging function."""

    @patch('logging.FileHandler', return_value=MagicMock())
    def test_setup_logging(self, mock_handler):
        """Creates logger with file handler."""
        mod = _load_module()
        logger = mod.setup_logging(name='test', cleanup_handlers=True)
        self.assertIsNotNone(logger)


if __name__ == '__main__':
    unittest.main()
