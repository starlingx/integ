#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for ceph-manage-journal module."""

import unittest
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch
import os
import sys
import importlib

# Load ceph-manage-journal as a module (filename has hyphens)
_CEPH_JOURNAL_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'ceph', 'ceph', 'debian',
    os.environ.get('STX_DEBIAN_VARIANT', 'bullseye'),
    'files', 'ceph-manage-journal.py')


def _load_ceph_module():
    """Load ceph-manage-journal.py as a module."""
    spec = importlib.util.spec_from_file_location(
        'ceph_manage_journal', _CEPH_JOURNAL_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Prevent main() from running on import
    with patch.object(mod, '__name__', 'ceph_manage_journal'):
        # We need to mock sys.argv to prevent main from running
        old_argv = sys.argv
        sys.argv = ['ceph-manage-journal.py']
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
    return mod


class TestCephCommand(unittest.TestCase):
    """Tests for the command() utility function."""

    @patch('subprocess.Popen')
    def test_command_success(self, mock_popen):
        """Test command returns stdout, stderr, returncode."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ('output', '')
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        mod = _load_ceph_module()
        out, err, ret = mod.command(['echo', 'test'])
        self.assertEqual(out, 'output')
        self.assertEqual(ret, 0)

    @patch('subprocess.Popen')
    def test_command_failure(self, mock_popen):
        """Test command returns non-zero returncode on failure."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ('', 'error msg')
        mock_proc.returncode = 1
        mock_popen.return_value = mock_proc

        mod = _load_ceph_module()
        out, err, ret = mod.command(['false'])
        self.assertEqual(ret, 1)
        self.assertEqual(err, 'error msg')


class TestCephGetInput(unittest.TestCase):
    """Tests for the get_input() function."""

    def test_valid_input(self):
        """Test valid dict input parsing."""
        mod = _load_ceph_module()
        result = mod.get_input(
            "{'disk_path': '/dev/sda', 'journals': [100, 200]}",
            ['disk_path', 'journals'])
        self.assertIsNotNone(result)
        self.assertEqual(result['disk_path'], '/dev/sda')

    def test_missing_key(self):
        """Test input with missing required key returns None."""
        mod = _load_ceph_module()
        result = mod.get_input(
            "{'disk_path': '/dev/sda'}",
            ['disk_path', 'journals'])
        self.assertIsNone(result)

    def test_invalid_input(self):
        """Test invalid input returns None."""
        mod = _load_ceph_module()
        result = mod.get_input("not a dict", ['key'])
        self.assertIsNone(result)


class TestCephGetPartitionUuid(unittest.TestCase):
    """Tests for get_partition_uuid()."""

    @patch('subprocess.Popen')
    def test_uuid_found(self, mock_popen):
        """Test UUID extraction from blkid output."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ('', '')
        mock_proc.returncode = 0
        mock_proc.stdout = iter([
            '/dev/sda1: PARTUUID="abc-123-def"\n'
        ])
        # Override for the actual Popen call
        mock_popen.return_value = mock_proc
        mock_proc.communicate.return_value = (
            '/dev/sda1: PARTUUID="abc-123-def"', '')

        mod = _load_ceph_module()
        result = mod.get_partition_uuid('/dev/sda1')
        self.assertEqual(result, 'abc-123-def')

    @patch('subprocess.Popen')
    def test_uuid_not_found(self, mock_popen):
        """Test None returned when no PARTUUID in output."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            '/dev/sda1: TYPE="xfs"', ''
        )
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        mod = _load_ceph_module()
        result = mod.get_partition_uuid('/dev/sda1')
        self.assertIsNone(result)


class TestCephDevicePathConversion(unittest.TestCase):
    """Tests for device path conversion functions."""

    @patch('subprocess.Popen')
    def test_device_path_to_device_node(self, mock_popen):
        """Test device path to node conversion."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ('/dev/sda\n', '')
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        mod = _load_ceph_module()
        result = mod.device_path_to_device_node(
            '/dev/disk/by-path/test'
        )
        self.assertEqual(result, '/dev/sda')

    @patch('subprocess.Popen')
    def test_device_path_to_device_node_exception(self, mock_popen):
        """Test device path conversion returns None on exception."""
        mock_popen.side_effect = Exception("test error")

        mod = _load_ceph_module()
        result = mod.device_path_to_device_node(
            '/dev/disk/by-path/test'
        )
        self.assertIsNone(result)

    @patch('subprocess.Popen')
    def test_device_path_to_mpath_node(self, mock_popen):
        """Test mpath device path conversion."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            '/dev/mapper/mpath0\n', ''
        )
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        mod = _load_ceph_module()
        result = mod.device_path_to_mpath_node(
            '/dev/disk/by-path/mpath-test'
        )
        self.assertEqual(result, '/dev/mapper/mpath0')


class TestCephMainFunction(unittest.TestCase):
    """Tests for the main() function argument parsing."""

    def test_main_invalid_args_count(self):
        """Test main with wrong number of args exits."""
        mod = _load_ceph_module()
        with self.assertRaises(SystemExit):
            mod.main(['only_one_arg'])

    def test_main_invalid_command(self):
        """Test main with invalid command exits."""
        mod = _load_ceph_module()
        with self.assertRaises(SystemExit):
            mod.main(['invalid', '{}'])

    def test_main_partitions_invalid_input(self):
        """Test main with invalid partitions input exits."""
        mod = _load_ceph_module()
        with self.assertRaises(SystemExit):
            mod.main(['partitions', 'not-a-dict'])

    def test_main_location_invalid_input(self):
        """Test main with invalid location input exits."""
        mod = _load_ceph_module()
        with self.assertRaises(SystemExit):
            mod.main(['location', 'not-a-dict'])

    def test_main_partitions_non_list_journals(self):
        """Test main with non-list journals exits."""
        mod = _load_ceph_module()
        with self.assertRaises(SystemExit):
            mod.main([
                'partitions',
                "{'disk_path': '/dev/sda', 'journals': 'not-a-list'}"])

    def test_main_location_non_int_osdid(self):
        """Test main with non-int osdid exits."""
        mod = _load_ceph_module()
        with self.assertRaises(SystemExit):
            mod.main([
                'location',
                ("{'data_path': '/dev/sda1', "
                 "'journal_path': '/dev/sdb1', 'osdid': 'abc'}")])


class TestCephIsPartitioningCorrect(unittest.TestCase):
    """Tests for is_partitioning_correct()."""

    @patch('subprocess.Popen')
    def test_correct_partitioning(self, mock_popen):
        """Test correct partitioning returns True."""
        mod = _load_ceph_module()
        # Mock sequence: device_path_to_device_node,
        # udevadm, parted print,
        # then per partition: udevadm, parted print, final udevadm
        responses = [
            ('/dev/sda\n', '', 0),  # udevadm settle
            ('/dev/sda\n', '', 0),  # readlink
            ('/dev/sda\n', '', 0),  # udevadm settle
            ('Partition Table: gpt\n', '', 0),  # parted print
            ('/dev/sda1\n', '', 0),  # udevadm settle
            ('Disk /dev/sda1: 100.0MiB\n', '', 0),  # parted print
            ('', '', 0),  # final udevadm settle
        ]
        call_idx = [0]

        def popen_side_effect(*args, **kwargs):
            """Mock Popen side effect."""
            mock_proc = MagicMock()
            idx = call_idx[0]
            if idx < len(responses):
                mock_proc.communicate.return_value = (
                    responses[idx][0], responses[idx][1])
                mock_proc.returncode = responses[idx][2]
            else:
                mock_proc.communicate.return_value = ('', '')
                mock_proc.returncode = 0
            call_idx[0] += 1
            return mock_proc

        mock_popen.side_effect = popen_side_effect
        result = mod.is_partitioning_correct('/dev/sda', [100])
        self.assertTrue(result)

    @patch('subprocess.Popen')
    def test_non_gpt_partitioning(self, mock_popen):
        """Test non-GPT partition table returns False."""
        mod = _load_ceph_module()
        responses = [
            ('/dev/sda\n', '', 0),
            ('/dev/sda\n', '', 0),
            ('/dev/sda\n', '', 0),
            ('Partition Table: msdos\n', '', 0),
        ]
        call_idx = [0]

        def popen_side_effect(*args, **kwargs):
            """Mock Popen side effect."""
            mock_proc = MagicMock()
            idx = call_idx[0]
            if idx < len(responses):
                mock_proc.communicate.return_value = (
                    responses[idx][0], responses[idx][1])
                mock_proc.returncode = responses[idx][2]
            else:
                mock_proc.communicate.return_value = ('', '')
                mock_proc.returncode = 0
            call_idx[0] += 1
            return mock_proc

        mock_popen.side_effect = popen_side_effect
        result = mod.is_partitioning_correct('/dev/sda', [100])
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
