#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for mgr-restful-plugin monitor_loop paths.

Uses SystemExit to safely break infinite loops.
"""

import importlib
import os
import socket
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

_VARIANT = os.environ.get(
    'STX_DEBIAN_VARIANT', 'bullseye'
)
_MGR_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'ceph', 'ceph', 'debian',
    _VARIANT, 'files', 'mgr-restful-plugin.py')


def _load_module():
    """Load mgr-restful-plugin module.

    Returns:
        The loaded module object.
    """
    spec = importlib.util.spec_from_file_location(
        'mgr_restful_mon', _MGR_PATH)
    mod = importlib.util.module_from_spec(spec)
    mock_handler = MagicMock()
    sys.modules['logging'] = MagicMock()
    sys.modules['logging.handlers'] = mock_handler
    sys.modules['daemon'] = MagicMock()
    mod.__name__ = 'mgr_restful_mon'
    spec.loader.exec_module(mod)
    sys.modules.pop('logging', None)
    sys.modules.pop('logging.handlers', None)
    sys.modules.pop('daemon', None)
    return mod


def _make_monitor(mod):
    """Create a ServiceMonitor without __init__.

    Args:
        mod: The loaded module.

    Returns:
        A ServiceMonitor instance with mocked attrs.
    """
    monitor = mod.ServiceMonitor.__new__(
        mod.ServiceMonitor
    )
    monitor.ping_failure_count = 0
    monitor.ceph_mgr_failure_count = 0
    monitor.ceph_mgr_start_date = None
    monitor.restful_plugin_url = ''
    monitor.certificate = ''
    return monitor


class TestMonitorLoopCmdFailed(unittest.TestCase):
    """CommandFailed exception path in monitor_loop."""

    @patch('time.sleep', side_effect=[None, SystemExit])
    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_command_failed_caught(
        self, mock_sig, mock_grp, mock_sleep
    ):
        """CommandFailed is caught and loop retries."""
        mod = _load_module()
        monitor = _make_monitor(mod)
        monitor.ceph_fsid_get = MagicMock(
            side_effect=mod.CommandFailed("c", 1, "e")
        )

        with self.assertRaises(SystemExit):
            monitor.monitor_loop()

    @patch('time.sleep', side_effect=SystemExit)
    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_command_timeout_caught(
        self, mock_sig, mock_grp, mock_sleep
    ):
        """CommandTimeout is caught."""
        mod = _load_module()
        monitor = _make_monitor(mod)
        monitor.ceph_fsid_get = MagicMock(
            side_effect=[
                mod.CommandTimeout("c", 30),
                SystemExit(),
            ]
        )

        with self.assertRaises(SystemExit):
            monitor.monitor_loop()

    @patch('time.sleep', side_effect=SystemExit)
    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_mgr_start_failed_caught(
        self, mock_sig, mock_grp, mock_sleep
    ):
        """CephMgrStartFailed is caught."""
        mod = _load_module()
        monitor = _make_monitor(mod)
        monitor.ceph_fsid_get = MagicMock(
            side_effect=mod.CephMgrStartFailed("f")
        )
        monitor.request_update_ceph_mgr_failures = (
            MagicMock()
        )

        with self.assertRaises(SystemExit):
            monitor.monitor_loop()

    @patch('time.sleep', side_effect=SystemExit)
    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_generic_exception_caught(
        self, mock_sig, mock_grp, mock_sleep
    ):
        """Generic Exception is caught."""
        mod = _load_module()
        monitor = _make_monitor(mod)
        monitor.ceph_fsid_get = MagicMock(
            side_effect=RuntimeError("unexpected")
        )

        with self.assertRaises(SystemExit):
            monitor.monitor_loop()


class TestMonitorLoopPingPaths(unittest.TestCase):
    """Ping success and failure paths."""

    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_ping_success_then_exit(
        self, mock_sig, mock_grp
    ):
        """Ping succeeds, sleep raises SystemExit."""
        mod = _load_module()
        monitor = _make_monitor(mod)
        monitor.ceph_fsid_get = MagicMock(
            return_value='fsid')
        monitor.ceph_mgr_auth_create = MagicMock()
        monitor.restful_plugin_set_server_port = (
            MagicMock()
        )
        monitor.restful_plugin_create_certificate = (
            MagicMock()
        )
        monitor.ceph_mgr_start = MagicMock()
        monitor.restful_plugin_enable = MagicMock()
        monitor.restful_plugin_create_admin_key = (
            MagicMock()
        )
        monitor.restful_plugin_get_url = MagicMock()
        monitor.restful_plugin_get_certificate = (
            MagicMock()
        )
        monitor.restful_plugin_ping = MagicMock()
        monitor.request_update_ping_failures = (
            MagicMock()
        )
        monitor.request_update_ceph_mgr_failures = (
            MagicMock()
        )
        monitor.ceph_mgr_uptime = MagicMock(
            return_value=0)

        with patch.object(mod, 'CONFIG') as cfg:
            cfg.ceph_mgr_lifecycle_days = -1
            cfg.restful_plugin_ping_delay_sec = 0
            with patch(
                'time.sleep', side_effect=SystemExit
            ):
                with self.assertRaises(SystemExit):
                    monitor.monitor_loop()

        monitor.restful_plugin_ping.assert_called()

    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_ping_fail_fsid_fail_breaks(
        self, mock_sig, mock_grp
    ):
        """Ping fails, fsid fails -> inner break."""
        mod = _load_module()
        monitor = _make_monitor(mod)

        call_count = [0]

        def fsid_side_effect():
            """Return fsid first, then False."""
            call_count[0] += 1
            if call_count[0] <= 1:
                return 'fsid'
            return False

        monitor.ceph_fsid_get = fsid_side_effect
        monitor.ceph_mgr_auth_create = MagicMock()
        monitor.restful_plugin_set_server_port = (
            MagicMock()
        )
        monitor.restful_plugin_create_certificate = (
            MagicMock()
        )
        monitor.ceph_mgr_start = MagicMock()
        monitor.restful_plugin_enable = MagicMock()
        monitor.restful_plugin_create_admin_key = (
            MagicMock()
        )
        monitor.restful_plugin_get_url = MagicMock()
        monitor.restful_plugin_get_certificate = (
            MagicMock()
        )
        monitor.restful_plugin_ping = MagicMock(
            side_effect=mod.RestApiPingFailed("f")
        )
        monitor.ceph_mgr_is_running = MagicMock(
            return_value=True)
        monitor.request_update_ping_failures = (
            MagicMock()
        )
        monitor.request_update_ceph_mgr_failures = (
            MagicMock()
        )
        monitor.ceph_mgr_uptime = MagicMock(
            return_value=0)

        with patch.object(mod, 'CONFIG') as cfg:
            cfg.ceph_mgr_lifecycle_days = -1
            cfg.restful_plugin_ping_delay_sec = 0
            cfg.cluster_grace_period_sec = 0
            cfg.ping_fail_count_restart_mgr = 999
            with patch(
                'time.sleep', side_effect=SystemExit
            ):
                with self.assertRaises(SystemExit):
                    monitor.monitor_loop()

    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_ping_fail_too_many_restarts_mgr(
        self, mock_sig, mock_grp
    ):
        """Too many ping failures -> stop mgr, break."""
        mod = _load_module()
        monitor = _make_monitor(mod)

        fsid_calls = [0]

        def fsid_effect():
            """Return fsid first, exit on retry."""
            fsid_calls[0] += 1
            if fsid_calls[0] > 1:
                raise SystemExit()
            return 'fsid'

        monitor.ceph_fsid_get = fsid_effect
        monitor.ceph_mgr_auth_create = MagicMock()
        monitor.restful_plugin_set_server_port = (
            MagicMock()
        )
        monitor.restful_plugin_create_certificate = (
            MagicMock()
        )
        monitor.ceph_mgr_start = MagicMock()
        monitor.ceph_mgr_stop = MagicMock()
        monitor.restful_plugin_enable = MagicMock()
        monitor.restful_plugin_create_admin_key = (
            MagicMock()
        )
        monitor.restful_plugin_get_url = MagicMock()
        monitor.restful_plugin_get_certificate = (
            MagicMock()
        )
        monitor.restful_plugin_ping = MagicMock(
            side_effect=mod.RestApiPingFailed("f")
        )
        monitor.ceph_mgr_is_running = MagicMock(
            return_value=True)
        monitor.request_update_ping_failures = (
            MagicMock()
        )
        monitor.request_update_ceph_mgr_failures = (
            MagicMock()
        )
        monitor.request_update_plugin_url = (
            MagicMock()
        )
        monitor.request_update_certificate = (
            MagicMock()
        )
        monitor.ceph_mgr_uptime = MagicMock(
            return_value=0)

        with patch.object(mod, 'CONFIG') as cfg:
            cfg.ceph_mgr_lifecycle_days = -1
            cfg.restful_plugin_ping_delay_sec = 0
            cfg.cluster_grace_period_sec = 0
            cfg.ping_fail_count_restart_mgr = 1
            with patch('time.sleep'):
                with self.assertRaises(SystemExit):
                    monitor.monitor_loop()

    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_ping_fail_mgr_not_running(
        self, mock_sig, mock_grp
    ):
        """Ping fails, mgr not running -> restart."""
        mod = _load_module()
        monitor = _make_monitor(mod)
        monitor.ceph_fsid_get = MagicMock(
            return_value='fsid')
        monitor.ceph_mgr_auth_create = MagicMock()
        monitor.restful_plugin_set_server_port = (
            MagicMock()
        )
        monitor.restful_plugin_create_certificate = (
            MagicMock()
        )
        monitor.ceph_mgr_start = MagicMock()
        monitor.restful_plugin_enable = MagicMock()
        monitor.restful_plugin_create_admin_key = (
            MagicMock()
        )
        monitor.restful_plugin_get_url = MagicMock()
        monitor.restful_plugin_get_certificate = (
            MagicMock()
        )
        monitor.restful_plugin_ping = MagicMock(
            side_effect=mod.RestApiPingFailed("f")
        )
        monitor.ceph_mgr_is_running = MagicMock(
            return_value=False)
        monitor.request_update_ping_failures = (
            MagicMock()
        )
        monitor.request_update_ceph_mgr_failures = (
            MagicMock()
        )
        monitor.ceph_mgr_uptime = MagicMock(
            return_value=0)

        with patch.object(mod, 'CONFIG') as cfg:
            cfg.ceph_mgr_lifecycle_days = -1
            cfg.restful_plugin_ping_delay_sec = 0
            cfg.ceph_mgr_grace_period_sec = 0
            cfg.ping_fail_count_restart_mgr = 999
            with patch(
                'time.sleep',
                side_effect=[None, SystemExit]
            ):
                with self.assertRaises(SystemExit):
                    monitor.monitor_loop()

    @patch('os.setpgrp')
    @patch('signal.signal')
    def test_lifecycle_restart(
        self, mock_sig, mock_grp
    ):
        """Lifecycle days exceeded triggers restart."""
        mod = _load_module()
        monitor = _make_monitor(mod)
        monitor.ceph_fsid_get = MagicMock(
            return_value='fsid')
        monitor.ceph_mgr_auth_create = MagicMock()
        monitor.restful_plugin_set_server_port = (
            MagicMock()
        )
        monitor.restful_plugin_create_certificate = (
            MagicMock()
        )
        monitor.ceph_mgr_start = MagicMock()
        monitor.ceph_mgr_restart = MagicMock()
        monitor.restful_plugin_enable = MagicMock()
        monitor.restful_plugin_create_admin_key = (
            MagicMock()
        )
        monitor.restful_plugin_get_url = MagicMock()
        monitor.restful_plugin_get_certificate = (
            MagicMock()
        )
        monitor.restful_plugin_ping = MagicMock()
        monitor.request_update_ping_failures = (
            MagicMock()
        )
        monitor.request_update_ceph_mgr_failures = (
            MagicMock()
        )
        monitor.ceph_mgr_uptime = MagicMock(
            return_value=100)

        with patch.object(mod, 'CONFIG') as cfg:
            cfg.ceph_mgr_lifecycle_days = 5
            cfg.restful_plugin_ping_delay_sec = 0
            with patch(
                'time.sleep', side_effect=SystemExit
            ):
                with self.assertRaises(SystemExit):
                    monitor.monitor_loop()

        monitor.ceph_mgr_restart.assert_called()


class TestRequestMethods(unittest.TestCase):
    """Tests for request_* static methods."""

    def test_request_status_success(self):
        """request_status returns True on OK."""
        mod = _load_module()
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'OK'
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            return_value=mock_sock
        ):
            result = mod.ServiceMonitor.request_status()
        self.assertTrue(result)

    def test_request_status_socket_error(self):
        """request_status returns False on error."""
        mod = _load_module()
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            side_effect=socket.error("fail")
        ):
            result = mod.ServiceMonitor.request_status()
        self.assertFalse(result)

    def test_request_stop_success(self):
        """request_stop returns True."""
        mod = _load_module()
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'OK'
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            return_value=mock_sock
        ):
            result = mod.ServiceMonitor.request_stop()
        self.assertTrue(result)

    def test_request_stop_socket_error(self):
        """request_stop returns False on error."""
        mod = _load_module()
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            side_effect=socket.error("fail")
        ):
            result = mod.ServiceMonitor.request_stop()
        self.assertFalse(result)

    def test_request_update_ceph_mgr_failures(self):
        """request_update_ceph_mgr_failures sends."""
        mod = _load_module()
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'OK'
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            return_value=mock_sock
        ):
            result = (
                mod.ServiceMonitor
                .request_update_ceph_mgr_failures(5)
            )
        self.assertTrue(result)

    def test_request_update_ping_failures(self):
        """request_update_ping_failures sends."""
        mod = _load_module()
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'OK'
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            return_value=mock_sock
        ):
            result = (
                mod.ServiceMonitor
                .request_update_ping_failures(3)
            )
        self.assertTrue(result)

    def test_request_update_plugin_url(self):
        """request_update_plugin_url sends."""
        mod = _load_module()
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'OK'
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            return_value=mock_sock
        ):
            result = (
                mod.ServiceMonitor
                .request_update_plugin_url('http://x')
            )
        self.assertTrue(result)

    def test_request_update_certificate(self):
        """request_update_certificate sends."""
        mod = _load_module()
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'OK'
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            return_value=mock_sock
        ):
            result = (
                mod.ServiceMonitor
                .request_update_certificate('/cert')
            )
        self.assertTrue(result)

    def test_request_update_url_socket_error(self):
        """request_update_plugin_url on error."""
        mod = _load_module()
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            side_effect=socket.error("fail")
        ):
            result = (
                mod.ServiceMonitor
                .request_update_plugin_url('http://x')
            )
        self.assertFalse(result)

    def test_request_update_mgr_failures_error(self):
        """request_update_ceph_mgr_failures on error."""
        mod = _load_module()
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            side_effect=socket.error("fail")
        ):
            result = (
                mod.ServiceMonitor
                .request_update_ceph_mgr_failures(1)
            )
        self.assertFalse(result)

    def test_request_update_ping_failures_error(self):
        """request_update_ping_failures on error."""
        mod = _load_module()
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            side_effect=socket.error("fail")
        ):
            result = (
                mod.ServiceMonitor
                .request_update_ping_failures(1)
            )
        self.assertFalse(result)

    def test_request_update_certificate_error(self):
        """request_update_certificate on error."""
        mod = _load_module()
        with patch.object(
            mod.ServiceMonitor, '_make_client_socket',
            side_effect=socket.error("fail")
        ):
            result = (
                mod.ServiceMonitor
                .request_update_certificate('/c')
            )
        self.assertFalse(result)


class TestServerLoopCommands(unittest.TestCase):
    """Tests for server_loop command handling."""

    def _make_server_monitor(self, mod, commands):
        """Create monitor with mocked socket.

        Args:
            mod: The loaded module.
            commands: List of byte commands to process.

        Returns:
            A configured ServiceMonitor instance.
        """
        monitor = _make_monitor(mod)
        monitor.command = MagicMock()
        mock_client = MagicMock()
        # accept returns (client, addr) pairs then stop
        accepts = [
            (mock_client, None) for _ in commands
        ]
        monitor.command.accept = MagicMock(
            side_effect=accepts + [SystemExit()]
        )
        mock_client.recv = MagicMock(
            side_effect=commands
        )
        monitor.send_response = MagicMock()
        monitor.stop = MagicMock()
        return monitor

    def test_status_command(self):
        """server_loop handles status command."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'status']
        )
        monitor.restful_plugin_url = 'http://x'
        monitor.ceph_mgr_failure_count = 0
        monitor.ping_failure_count = 0
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.ceph_mgr_fail_count_report_error = 10
            cfg.ping_fail_count_report_error = 10
            cfg.service_socket_bufsize = 1024
            with self.assertRaises(SystemExit):
                monitor.server_loop()
        monitor.send_response.assert_called()

    def test_restful_url_command(self):
        """server_loop handles restful-url command."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'restful-url http://new']
        )
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.service_socket_bufsize = 1024
            with self.assertRaises(SystemExit):
                monitor.server_loop()
        self.assertEqual(
            monitor.restful_plugin_url, b'http://new'
        )

    def test_certificate_command(self):
        """server_loop handles certificate command."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'certificate /path/cert']
        )
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.service_socket_bufsize = 1024
            with self.assertRaises(SystemExit):
                monitor.server_loop()
        self.assertEqual(
            monitor.certificate, b'/path/cert'
        )

    def test_ping_failures_command(self):
        """server_loop handles ping-failures."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'ping-failures 5']
        )
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.service_socket_bufsize = 1024
            with self.assertRaises(SystemExit):
                monitor.server_loop()
        self.assertEqual(monitor.ping_failure_count, 5)

    def test_ceph_mgr_failures_command(self):
        """server_loop handles ceph-mgr-failures."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'ceph-mgr-failures 2']
        )
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.service_socket_bufsize = 1024
            cfg.ceph_mgr_fail_count_exit = 10
            with self.assertRaises(SystemExit):
                monitor.server_loop()
        self.assertEqual(
            monitor.ceph_mgr_failure_count, 2
        )

    def test_restful_url_no_args(self):
        """server_loop restful-url with no args."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'restful-url']
        )
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.service_socket_bufsize = 1024
            with self.assertRaises(SystemExit):
                monitor.server_loop()

    def test_certificate_no_args(self):
        """server_loop certificate with no args."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'certificate']
        )
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.service_socket_bufsize = 1024
            with self.assertRaises(SystemExit):
                monitor.server_loop()

    def test_ceph_mgr_failures_invalid(self):
        """server_loop ceph-mgr-failures with bad value."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'ceph-mgr-failures abc']
        )
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.service_socket_bufsize = 1024
            with self.assertRaises(SystemExit):
                monitor.server_loop()

    def test_ping_failures_invalid(self):
        """server_loop ping-failures with bad value."""
        mod = _load_module()
        monitor = self._make_server_monitor(
            mod, [b'ping-failures xyz']
        )
        with patch.object(mod, 'CONFIG') as cfg:
            cfg.service_socket_bufsize = 1024
            with self.assertRaises(SystemExit):
                monitor.server_loop()


class TestInitWrapperStart(unittest.TestCase):
    """Tests for InitWrapper.start() method."""

    def test_start_parent_ok(self):
        """Parent process exits 0 on OK status."""
        mod = _load_module()
        with patch('os.pipe', return_value=(3, 4)):
            with patch('os.fork', return_value=123):
                with patch('os.close'):
                    with patch(
                        'os.read', return_value=b'OK'
                    ):
                        with patch('os.waitpid'):
                            with patch(
                                'sys.exit',
                                side_effect=SystemExit
                            ):
                                with self.assertRaises(
                                    SystemExit
                                ):
                                    mod.InitWrapper.start(
                                        MagicMock()
                                    )

    def test_start_parent_err(self):
        """Parent exits 1 on error status."""
        mod = _load_module()
        with patch('os.pipe', return_value=(3, 4)):
            with patch('os.fork', return_value=123):
                with patch('os.close'):
                    with patch(
                        'os.read',
                        return_value=b'ERR'
                    ):
                        with patch('os.waitpid'):
                            with patch(
                                'sys.exit'
                            ) as mock_exit:
                                mod.InitWrapper.start(
                                    MagicMock()
                                )
        mock_exit.assert_called_with(1)

    def test_start_parent_ioerror(self):
        """Parent handles IOError on pipe read."""
        mod = _load_module()
        with patch('os.pipe', return_value=(3, 4)):
            with patch('os.fork', return_value=123):
                with patch('os.close'):
                    with patch(
                        'os.read',
                        side_effect=IOError("e")
                    ):
                        with patch('os.waitpid'):
                            with patch(
                                'sys.exit'
                            ) as mock_exit:
                                mod.InitWrapper.start(
                                    MagicMock()
                                )
        mock_exit.assert_called_with(1)


class TestInitWrapperStop(unittest.TestCase):
    """Tests for InitWrapper.stop()."""


class TestInitWrapperStatus(unittest.TestCase):
    """Tests for InitWrapper.status()."""

    def test_status_ok(self):
        """status() exits 0 when OK."""
        mod = _load_module()
        with patch.object(
            mod.ServiceMonitor, 'request_status',
            return_value=True
        ):
            with patch('sys.exit') as mock_exit:
                mod.InitWrapper.status(MagicMock())
        mock_exit.assert_called_with(0)

    def test_status_fail(self):
        """status() exits 1 when down."""
        mod = _load_module()
        with patch.object(
            mod.ServiceMonitor, 'request_status',
            return_value=False
        ):
            with patch('sys.exit') as mock_exit:
                mod.InitWrapper.status(MagicMock())
        mock_exit.assert_called_with(1)


if __name__ == '__main__':
    unittest.main()
