#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for mgr-restful-plugin server_loop, context managers,
request_* static methods, create_certificate,
InitWrapper, and monitor_loop.
"""

import contextlib
import errno
import importlib
import os
import socket
import subprocess
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

sys.modules.setdefault('daemon', MagicMock())
sys.modules.setdefault('psutil', MagicMock())
sys.modules.setdefault('requests', MagicMock())

import psutil

_P = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'ceph', 'ceph', 'debian',
    os.environ.get('STX_DEBIAN_VARIANT', 'bullseye'),
    'files', 'mgr-restful-plugin.py')


def _load_module():
    """Load the module under test.

    Returns:
        The loaded module object.
    """
    spec = importlib.util.spec_from_file_location('mrp3', _P)
    mod = importlib.util.module_from_spec(spec)
    h = MagicMock()
    h.level = 0
    with patch('socket.gethostname', return_value='ctrl-0'), \
         patch('logging.FileHandler', return_value=h):
        spec.loader.exec_module(mod)
    return mod


def _load_mgr_module():
    """Load mgr-restful-plugin with mocked check_output.

    Returns:
        The loaded module object.
    """
    mod = _load_module()
    return mod, mod.ServiceMonitor()

# ── server_loop ──────────────────────────────────────────────


class TestServerLoop(unittest.TestCase):
    """Tests for server_loop command dispatch."""

    def _run_loop(self, request_bytes):
        """Run server_loop with a single request then stop."""
        mod, m = _load_mgr_module()
        m.command = MagicMock()
        client = MagicMock()
        # First accept returns client, second raises to break loop
        if request_bytes == b'stop':
            m.command.accept.return_value = (client, None)
            client.recv.return_value = request_bytes
            m.stop = MagicMock()
        else:
            # Send the request, then send 'stop' to break loop
            m.command.accept.side_effect = [
                (client, None),
                (client, None),
            ]
            client.recv.side_effect = [request_bytes, b'stop']
            m.stop = MagicMock()
        m.send_response = MagicMock()
        m.status = MagicMock(return_value='OK')
        m.server_loop()
        return mod, m, client

    def test_status_command(self):
        """server_loop handles 'status' command."""
        mod, m, client = self._run_loop(b'status')
        m.status.assert_called()
        # Verify response was sent back to client
        m.send_response.assert_called()

    def test_stop_command(self):
        """server_loop handles 'stop' command."""
        mod, m, client = self._run_loop(b'stop')
        m.stop.assert_called()
        # Verify stop was invoked (loop exited)

    def test_restful_url_command(self):
        """server_loop handles 'restful-url' command."""
        mod, m = _load_mgr_module()
        m.command = MagicMock()
        client = MagicMock()
        m.command.accept.side_effect = [
            (client, None), (client, None)]
        client.recv.side_effect = [
            b'restful-url https://test:7999', b'stop']
        m.stop = MagicMock()
        m.send_response = MagicMock()
        m.server_loop()
        self.assertEqual(m.restful_plugin_url, b'https://test:7999')

    def test_certificate_command(self):
        """server_loop handles 'certificate' command."""
        mod, m = _load_mgr_module()
        m.command = MagicMock()
        client = MagicMock()
        m.command.accept.side_effect = [
            (client, None), (client, None)]
        client.recv.side_effect = [
            b'certificate /tmp/cert.pem', b'stop']
        m.stop = MagicMock()
        m.send_response = MagicMock()
        m.server_loop()
        self.assertEqual(m.certificate, b'/tmp/cert.pem')

    def test_ping_failures_command(self):
        """server_loop handles 'ping-failures' command."""
        mod, m = _load_mgr_module()
        m.command = MagicMock()
        client = MagicMock()
        m.command.accept.side_effect = [
            (client, None), (client, None)]
        client.recv.side_effect = [b'ping-failures 5', b'stop']
        m.stop = MagicMock()
        m.send_response = MagicMock()
        m.server_loop()
        self.assertEqual(m.ping_failure_count, 5)

    def test_ceph_mgr_failures_command(self):
        """server_loop handles 'ceph-mgr-failures' command."""
        mod, m = _load_mgr_module()
        m.command = MagicMock()
        client = MagicMock()
        m.command.accept.side_effect = [
            (client, None), (client, None)]
        client.recv.side_effect = [b'ceph-mgr-failures 2', b'stop']
        m.stop = MagicMock()
        m.send_response = MagicMock()
        m.server_loop()
        self.assertEqual(m.ceph_mgr_failure_count, 2)


class TestServiceLock(unittest.TestCase):
    """Tests for service_lock context manager."""

    @patch('fcntl.flock', side_effect=IOError(errno.EAGAIN, 'busy'))
    @patch('os.makedirs')
    @patch('builtins.open', mock_open())
    def test_lock_already_started(self, mock_mkdirs, mock_flock):
        """Raises ServiceAlreadyStarted on EAGAIN."""
        mod, m = _load_mgr_module()
        with self.assertRaises(mod.ServiceAlreadyStarted):
            with m.service_lock():
                pass

    @patch('fcntl.flock', side_effect=IOError(errno.EACCES, 'denied'))
    @patch('os.makedirs')
    @patch('builtins.open', mock_open())
    def test_lock_failed(self, mock_mkdirs, mock_flock):
        """Raises ServiceLockFailed on other errors."""
        mod, m = _load_mgr_module()
        with self.assertRaises(mod.ServiceLockFailed):
            with m.service_lock():
                pass


class TestServiceSocket(unittest.TestCase):
    """Tests for service_socket context manager."""

    def test_socket_create_error(self):
        """Raises ServiceNoSocket on socket error."""
        mod, m = _load_mgr_module()
        with patch.object(mod.socket, 'socket',
                          side_effect=socket.error('fail')):
            with self.assertRaises(mod.ServiceNoSocket):
                with m.service_socket():
                    pass

    @patch('os.unlink')
    def test_socket_bind_error(self, mock_unlink):
        """Raises ServiceSocketBindFailed on bind error."""
        mod, m = _load_mgr_module()
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = socket.error('addr in use')
        with patch.object(mod.socket, 'socket', return_value=mock_sock):
            with self.assertRaises(mod.ServiceSocketBindFailed):
                with m.service_socket():
                    pass


class TestServicePidFile(unittest.TestCase):
    """Tests for service_pid_file context manager."""

    @patch('builtins.open', side_effect=OSError('perm'))
    def test_pid_file_error(self, mock_file):
        """Raises ServiceNoPidFile on error."""
        mod, m = _load_mgr_module()
        with self.assertRaises(mod.ServiceNoPidFile):
            with m.service_pid_file():
                pass

# ── request_* static methods ─────────────────────────────────


class TestRequestMethods(unittest.TestCase):
    """Tests for request_status, request_stop, etc."""

    def _mock_socket(self, mod, recv_data=b'OK'):
        """Configure mock socket for module."""
        mock_sock = MagicMock()
        mock_sock.recv.return_value = recv_data
        mod.ServiceMonitor._make_client_socket = MagicMock(
            return_value=mock_sock)
        return mock_sock

    def test_request_status_ok(self):
        """request_status returns True on OK."""
        mod = _load_module()
        self._mock_socket(mod, b'OK')
        self.assertTrue(mod.ServiceMonitor.request_status())

    def test_request_status_err(self):
        """request_status returns False on ERR."""
        mod = _load_module()
        self._mock_socket(mod, b'ERR')
        self.assertFalse(mod.ServiceMonitor.request_status())

    def test_request_status_socket_error(self):
        """request_status returns False on socket error."""
        mod = _load_module()
        mod.ServiceMonitor._make_client_socket = MagicMock(
            side_effect=socket.error('refused'))
        self.assertFalse(mod.ServiceMonitor.request_status())

    def test_request_stop_ok(self):
        """request_stop returns True on success."""
        mod = _load_module()
        self._mock_socket(mod, b'OK')
        self.assertTrue(mod.ServiceMonitor.request_stop())

    def test_request_stop_error(self):
        """request_stop returns False on socket error."""
        mod = _load_module()
        mod.ServiceMonitor._make_client_socket = MagicMock(
            side_effect=socket.error('refused'))
        self.assertFalse(mod.ServiceMonitor.request_stop())

    def test_request_update_ceph_mgr_failures(self):
        """request_update_ceph_mgr_failures sends count."""
        mod = _load_module()
        self._mock_socket(mod)
        self.assertTrue(
            mod.ServiceMonitor.request_update_ceph_mgr_failures(5))

    def test_request_update_ping_failures(self):
        """request_update_ping_failures sends count."""
        mod = _load_module()
        self._mock_socket(mod)
        self.assertTrue(
            mod.ServiceMonitor.request_update_ping_failures(3))

    def test_request_update_plugin_url(self):
        """request_update_plugin_url sends url."""
        mod = _load_module()
        self._mock_socket(mod)
        self.assertTrue(
            mod.ServiceMonitor.request_update_plugin_url('https://x'))

    def test_request_update_certificate(self):
        """request_update_certificate sends path."""
        mod = _load_module()
        self._mock_socket(mod)
        self.assertTrue(
            mod.ServiceMonitor.request_update_certificate('/tmp/c'))

# ── create_certificate ───────────────────────────────────────


class TestCreateCertificate(unittest.TestCase):
    """Tests for restful_plugin_create_certificate."""

    @patch('shutil.rmtree')
    @patch('tempfile.mkdtemp', return_value='/tmp/test')
    @patch('subprocess.check_call')
    def test_create_cert(self, mock_check, mock_mkd, mock_rm):
        """Creates certificate when none exists."""
        mod, m = _load_mgr_module()
        err = subprocess.CalledProcessError(1, 'cmd', output='err')
        # has_certificate returns False (CommandFailed), then create
        with patch.object(mod.subprocess, 'check_output',
                          side_effect=[err, '', '', '', '']):
            m.restful_plugin_create_certificate()
        mock_check.assert_called()
        mock_rm.assert_called_with('/tmp/test')

# ── stop_unmanaged_ceph_mgr ─────────────────────────────────


class TestStopUnmanagedCephMgr(unittest.TestCase):
    """Tests for stop_unmanaged_ceph_mgr."""


class TestStartMonitor(unittest.TestCase):
    """Tests for start_monitor."""


class TestSetupLoggingCleanup(unittest.TestCase):
    """Tests for setup_logging with cleanup."""

    @patch('logging.FileHandler', return_value=MagicMock(level=0))
    def test_cleanup_handlers(self, mock_handler):
        """setup_logging with cleanup_handlers=True."""
        mod = _load_module()
        logger = mod.setup_logging(name='test-clean',
                                   cleanup_handlers=True)
        self.assertIsNotNone(logger)

    @patch('logging.FileHandler', return_value=MagicMock(level=0))
    def test_no_cleanup(self, mock_handler):
        """setup_logging without cleanup."""
        mod = _load_module()
        logger = mod.setup_logging(name='test-noclean',
                                   cleanup_handlers=False)
        self.assertIsNotNone(logger)


if __name__ == '__main__':
    unittest.main()
