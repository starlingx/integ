#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for storage_topology module."""

import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

# Mock external deps before import
try:
    import prettytable  # noqa: F401
except ImportError:
    pass
sys.modules.setdefault('keyring', MagicMock())
sys.modules.setdefault('prettytable', MagicMock())
sys.modules.setdefault('cgtsclient', MagicMock())
sys.modules.setdefault('cgtsclient.common', MagicMock())
sys.modules.setdefault('cgtsclient.common.utils', MagicMock())
sys.modules.setdefault('cgtsclient.client', MagicMock())
sys.modules.setdefault('cgtsclient.exc', MagicMock())

_ST_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'tools', 'storage-topology', 'storage-topology',
    'storage_topology', 'exec', 'storage_topology.py')


def _load_module():
    """Load storage_topology.py as a module."""
    spec = importlib.util.spec_from_file_location(
        'storage_topology', _ST_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestConvertToReadableSize(unittest.TestCase):
    """Tests for convert_to_readable_size function."""

    def test_bytes_to_gb(self):
        """Test converting bytes to human readable."""
        mod = _load_module()
        result = mod.convert_to_readable_size(1073741824)
        self.assertIn('GB', result)

    def test_mb_to_gb(self):
        """Test converting MB to GB."""
        mod = _load_module()
        result = mod.convert_to_readable_size(1024, 'MB')
        self.assertIn('GB', result)

    def test_kb_to_mb(self):
        """Test converting KB to MB."""
        mod = _load_module()
        result = mod.convert_to_readable_size(1024, 'KB')
        self.assertIn('MB', result)

    def test_tb_size(self):
        """Test TB-scale size."""
        mod = _load_module()
        result = mod.convert_to_readable_size(1099511627776)
        self.assertIn('TB', result)

    def test_invalid_unit_raises(self):
        """Test invalid unit raises RuntimeError."""
        mod = _load_module()
        with self.assertRaises(RuntimeError):
            mod.convert_to_readable_size(100, 'INVALID')

    def test_small_bytes(self):
        """Test small byte values."""
        mod = _load_module()
        result = mod.convert_to_readable_size(512)
        self.assertIn('B', result)


class TestConfigureDebugging(unittest.TestCase):
    """Tests for configure_debuggubg function."""


class TestParseArguments(unittest.TestCase):
    """Tests for parse_arguments function."""

    def test_default_arguments(self):
        """Test default argument values."""
        mod = _load_module()
        show = {}
        with patch('sys.argv', ['storage-topology']):
            mod.parse_arguments(show)
        self.assertFalse(show['diskview'])
        self.assertFalse(show['vgview'])
        self.assertFalse(show['all'])
        self.assertFalse(show['extended'])

    def test_diskview_flag(self):
        """Test -d flag sets diskview."""
        mod = _load_module()
        show = {}
        with patch('sys.argv', ['storage-topology', '-d']):
            mod.parse_arguments(show)
        self.assertTrue(show['diskview'])

    def test_vgview_flag(self):
        """Test -v flag sets vgview."""
        mod = _load_module()
        show = {}
        with patch('sys.argv', ['storage-topology', '-v']):
            mod.parse_arguments(show)
        self.assertTrue(show['vgview'])

    def test_all_flag(self):
        """Test -a flag sets all."""
        mod = _load_module()
        show = {}
        with patch('sys.argv', ['storage-topology', '-a']):
            mod.parse_arguments(show)
        self.assertTrue(show['all'])

    def test_extended_flag(self):
        """Test -e flag sets extended."""
        mod = _load_module()
        show = {}
        with patch('sys.argv', ['storage-topology', '-e']):
            mod.parse_arguments(show)
        self.assertTrue(show['extended'])


class TestGetSystemCreds(unittest.TestCase):
    """Tests for get_system_creds function."""

    @patch('subprocess.Popen')
    def test_get_creds(self, mock_popen):
        """Test credential extraction from env."""
        mod = _load_module()
        mock_proc = MagicMock()
        mock_proc.stdout = iter([
            'OS_USERNAME=admin\n',
            'OS_PASSWORD=secret\n',
            'OS_AUTH_URL=http://localhost:5000/v3\n',
            'HOME=/root\n',
        ])
        mock_proc.communicate.return_value = (None, None)
        mock_popen.return_value = mock_proc
        result = mod.get_system_creds()
        self.assertEqual(result['os_username'], 'admin')
        self.assertEqual(result['os_password'], 'secret')
        self.assertNotIn('home', result)


class TestPrintDiskView(unittest.TestCase):
    """Tests for print_disk_view function."""

    def test_empty_rows(self):
        """Test print_disk_view with empty rows."""
        mod = _load_module()
        # Should not raise
        mod.print_disk_view(rows=[], extended=False)

    @unittest.skipUnless(
        'prettytable' in sys.modules
        and not isinstance(sys.modules['prettytable'], MagicMock),
        'prettytable not available')
    def test_nonempty_rows_extended(self):
        """Test print_disk_view with extended rows."""
        mod = _load_module()
        rows = [['host1', '/dev/sda', 'SSD', 'uuid1', '100 GB',
                 'pv1', 'active', 'pv-uuid', 'vg1:active:vg-uuid']]
        mod.print_disk_view(rows=rows, extended=True)


class TestPrintVgView(unittest.TestCase):
    """Tests for print_vg_view function."""

    def test_empty_rows(self):
        """Test print_vg_view with empty rows."""
        mod = _load_module()
        mod.print_vg_view(rows=[], extended=False)

    @unittest.skipUnless(
        'prettytable' in sys.modules
        and not isinstance(sys.modules['prettytable'], MagicMock),
        'prettytable not available')
    def test_nonempty_rows_brief(self):
        """Test print_vg_view with brief rows."""
        mod = _load_module()
        rows = [['host1', 'vg1', 'active', '100 GB', '2', '1',
                 'pv1:active', '{}']]
        mod.print_vg_view(rows=rows, extended=False)


def _make_topology_obj(**kwargs):
    """Create a mock object with given attributes."""
    obj = MagicMock()
    for key, value in kwargs.items():
        setattr(obj, key, value)
    return obj


class TestGetInfoMultiplePvs(unittest.TestCase):
    """Tests for get_info_and_display with multiple PVs."""

    def test_two_pvs_on_same_disk_produce_two_rows(self):
        """Extended disk view with 2 PVs on same disk produces 2 rows."""
        mod = _load_module()
        cc = MagicMock()
        cc.ihost.list.return_value = [
            _make_topology_obj(hostname='h1', uuid='u1')]
        cc.idisk.list.return_value = [
            _make_topology_obj(
                device_node='/dev/sda', device_type='SSD',
                uuid='du', size_mib=1024)]
        pv1 = _make_topology_obj(
            lvm_pv_name='pv0', pv_state='active',
            lvm_pv_uuid='pu0', lvm_vg_name='vg0',
            idisk_device_node='/dev/sda')
        pv2 = _make_topology_obj(
            lvm_pv_name='pv1', pv_state='active',
            lvm_pv_uuid='pu1', lvm_vg_name='vg0',
            idisk_device_node='/dev/sda')
        cc.ipv.list.return_value = [pv1, pv2]
        vg = _make_topology_obj(
            lvm_vg_name='vg0', uuid='vu', vg_state='active')
        cc.ilvg.list.return_value = [vg]
        mod.print_disk_view = MagicMock()
        mod.print_vg_view = MagicMock()
        mod.get_info_and_display(cc, {
            'diskview': True, 'vgview': False,
            'all': False, 'extended': True})
        rows = mod.print_disk_view.call_args[1]['rows']
        self.assertGreaterEqual(len(rows), 2)

    def test_pv_on_different_disk_not_matched(self):
        """PV on different disk does not appear in disk's row."""
        mod = _load_module()
        cc = MagicMock()
        cc.ihost.list.return_value = [
            _make_topology_obj(hostname='h1', uuid='u1')]
        cc.idisk.list.return_value = [
            _make_topology_obj(device_node='/dev/sda', size_mib=1024)]
        pv = _make_topology_obj(
            lvm_pv_name='pv0', pv_state='active',
            lvm_vg_name='vg0',
            idisk_device_node='/dev/sdb')
        cc.ipv.list.return_value = [pv]
        cc.ilvg.list.return_value = []
        mod.print_disk_view = MagicMock()
        mod.print_vg_view = MagicMock()
        mod.get_info_and_display(cc, {
            'diskview': True, 'vgview': False,
            'all': False, 'extended': False})
        rows = mod.print_disk_view.call_args[1]['rows']
        for row in rows:
            self.assertNotIn('pv0', row)


class TestMainErrorHandling(unittest.TestCase):
    """Tests for main() credential validation and error handling."""

    @patch('sys.exit')
    @patch('sys.argv', ['storage-topology'])
    def test_missing_username_exits_with_error(self, mock_exit):
        """main() exits with -4 when username is empty."""
        mod = _load_module()
        with patch.object(mod, 'get_system_creds',
                          return_value={
                              'os_username': '',
                              'os_password': 'pass',
                              'os_project_name': 'admin',
                              'os_auth_url': 'http://localhost:5000/v3',
                              'os_region_name': 'RegionOne'}):
            mod.main()
        mock_exit.assert_called_with(-4)

    @patch('sys.exit')
    @patch('sys.argv', ['storage-topology'])
    def test_missing_password_non_root_exits_with_error(self, mock_exit):
        """main() exits with -4 when password empty for non-root."""
        mod = _load_module()
        with patch.object(mod, 'get_system_creds',
                          return_value={
                              'os_username': 'admin',
                              'os_password': '',
                              'os_project_name': 'admin',
                              'os_auth_url': 'http://localhost:5000/v3',
                              'os_region_name': 'RegionOne'}), \
             patch('os.geteuid', return_value=1000):
            mod.main()
        mock_exit.assert_called_with(-4)

    @patch('sys.exit')
    def test_keyboard_interrupt_exits_gracefully(self, mock_exit):
        """main() handles KeyboardInterrupt with exit(0)."""
        mod = _load_module()
        mod.parse_arguments = MagicMock(side_effect=KeyboardInterrupt())
        mod.main()
        mock_exit.assert_called_with(0)

    @patch('sys.exit')
    def test_unexpected_exception_exits_with_error(self, mock_exit):
        """main() handles unexpected exception with exit(-4)."""
        mod = _load_module()
        mod.parse_arguments = MagicMock(
            side_effect=RuntimeError('unexpected'))
        mod.main()
        mock_exit.assert_called_with(-4)


if __name__ == '__main__':
    unittest.main()


class TestMainCredentialValidation(unittest.TestCase):
    """Tests for main() credential validation paths."""

    @patch('sys.exit')
    @patch('sys.argv', ['storage-topology', '-a'])
    def test_missing_project_name_exits(self, mock_exit):
        """main() exits with -4 when project_name is empty."""
        mod = _load_module()
        with patch.object(mod, 'get_system_creds',
                          return_value={
                              'os_username': 'admin',
                              'os_password': 'pass',
                              'os_project_name': '',
                              'os_auth_url': 'http://localhost:5000/v3',
                              'os_region_name': 'RegionOne'}):
            mod.main()
        mock_exit.assert_called_with(-4)

    @patch('sys.exit')
    @patch('sys.argv', ['storage-topology', '-a'])
    def test_missing_auth_url_exits(self, mock_exit):
        """main() exits with -4 when auth_url is empty."""
        mod = _load_module()
        with patch.object(mod, 'get_system_creds',
                          return_value={
                              'os_username': 'admin',
                              'os_password': 'pass',
                              'os_project_name': 'admin',
                              'os_auth_url': '',
                              'os_region_name': 'RegionOne'}):
            mod.main()
        mock_exit.assert_called_with(-4)

    @patch('sys.exit')
    @patch('sys.argv', ['storage-topology', '-a'])
    def test_missing_region_name_exits(self, mock_exit):
        """main() exits with -4 when region_name is empty."""
        mod = _load_module()
        with patch.object(mod, 'get_system_creds',
                          return_value={
                              'os_username': 'admin',
                              'os_password': 'pass',
                              'os_project_name': 'admin',
                              'os_auth_url': 'http://localhost:5000/v3',
                              'os_region_name': ''}):
            mod.main()
        mock_exit.assert_called_with(-4)

    @patch('sys.exit')
    @patch('sys.argv', ['storage-topology', '-d'])
    def test_successful_run_exits_0(self, mock_exit):
        """main() exits with 0 on successful run."""
        mod = _load_module()
        mock_cc = MagicMock()
        mock_cc.ihost.list.return_value = []
        with patch.object(mod, 'get_system_creds',
                          return_value={
                              'os_username': 'admin',
                              'os_password': 'pass',
                              'os_project_name': 'admin',
                              'os_auth_url': 'http://localhost:5000/v3',
                              'os_region_name': 'RegionOne'}), \
             patch.object(mod.cgts_client, 'get_client',
                          return_value=mock_cc):
            mod.print_disk_view = MagicMock()
            mod.print_vg_view = MagicMock()
            mod.main()
        mock_exit.assert_called_with(0)


class TestGetInfoVgView(unittest.TestCase):
    """Tests for get_info_and_display VG view paths."""

    def test_vg_view_produces_rows(self):
        """VG view with valid data produces rows."""
        mod = _load_module()
        cc = MagicMock()
        cc.ihost.list.return_value = [
            _make_topology_obj(hostname='h1', uuid='u1')]
        cc.idisk.list.return_value = []
        pv = _make_topology_obj(
            lvm_pv_name='pv0', pv_state='active',
            lvm_vg_name='vg0')
        cc.ipv.list.return_value = [pv]
        vg = _make_topology_obj(
            lvm_vg_name='vg0', uuid='vu',
            vg_state='active', lvm_vg_size=2048,
            lvm_cur_lv=2, lvm_cur_pv=1,
            capabilities='{}')
        cc.ilvg.list.return_value = [vg]
        mod.print_disk_view = MagicMock()
        mod.print_vg_view = MagicMock()
        mod.get_info_and_display(cc, {
            'diskview': False, 'vgview': True,
            'all': False, 'extended': False})
        rows = mod.print_vg_view.call_args[1]['rows']
        self.assertGreater(len(rows), 0)
        self.assertIn('vg0', rows[0])

    def test_vg_view_extended_produces_rows(self):
        """VG view extended with valid data produces rows."""
        mod = _load_module()
        cc = MagicMock()
        cc.ihost.list.return_value = [
            _make_topology_obj(hostname='h1', uuid='u1')]
        cc.idisk.list.return_value = []
        pv = _make_topology_obj(
            lvm_pv_name='pv0', pv_state='active',
            lvm_pv_uuid='pu0', lvm_vg_name='vg0')
        cc.ipv.list.return_value = [pv]
        vg = _make_topology_obj(
            lvm_vg_name='vg0', uuid='vu',
            vg_state='active', lvm_vg_size=4096,
            lvm_cur_lv=3, lvm_cur_pv=1,
            capabilities='{}')
        cc.ilvg.list.return_value = [vg]
        mod.print_disk_view = MagicMock()
        mod.print_vg_view = MagicMock()
        mod.get_info_and_display(cc, {
            'diskview': False, 'vgview': True,
            'all': False, 'extended': True})
        rows = mod.print_vg_view.call_args[1]['rows']
        self.assertGreater(len(rows), 0)
        self.assertIn('h1', rows[0])
        self.assertIn('vg0', rows[0])

    def test_disk_view_no_pv_pads_empty(self):
        """Disk view without matching PV pads empty values."""
        mod = _load_module()
        cc = MagicMock()
        cc.ihost.list.return_value = [
            _make_topology_obj(hostname='h1', uuid='u1')]
        cc.idisk.list.return_value = [
            _make_topology_obj(device_node='/dev/sda', size_mib=1024)]
        cc.ipv.list.return_value = []
        cc.ilvg.list.return_value = []
        mod.print_disk_view = MagicMock()
        mod.print_vg_view = MagicMock()
        mod.get_info_and_display(cc, {
            'diskview': True, 'vgview': False,
            'all': False, 'extended': False})
        rows = mod.print_disk_view.call_args[1]['rows']
        self.assertGreater(len(rows), 0)
        # First element should be hostname
        self.assertEqual(rows[0][0], 'h1')

    def test_disk_view_extended_no_pv(self):
        """Extended disk view without PV pads correctly."""
        mod = _load_module()
        cc = MagicMock()
        cc.ihost.list.return_value = [
            _make_topology_obj(hostname='h1', uuid='u1')]
        cc.idisk.list.return_value = [
            _make_topology_obj(device_node='/dev/sda', device_type='SSD',
                               uuid='du', size_mib=1024)]
        cc.ipv.list.return_value = []
        cc.ilvg.list.return_value = []
        mod.print_disk_view = MagicMock()
        mod.print_vg_view = MagicMock()
        mod.get_info_and_display(cc, {
            'diskview': True, 'vgview': False,
            'all': False, 'extended': True})
        rows = mod.print_disk_view.call_args[1]['rows']
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows[0][0], 'h1')
