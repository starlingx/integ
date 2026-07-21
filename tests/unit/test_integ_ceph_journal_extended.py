#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Extended tests for ceph-manage-journal.

Covers create_partitions, mount_data_partition,
is_location_correct, fix_location, and main flows.
"""

import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import mock_open
from unittest.mock import patch

_CEPH_JOURNAL_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'ceph', 'ceph', 'debian',
    os.environ.get('STX_DEBIAN_VARIANT', 'bullseye'),
    'files', 'ceph-manage-journal.py')


def _load_module():
    """Load ceph-manage-journal module.

    Returns the loaded module object.
    """
    spec = importlib.util.spec_from_file_location(
        'cmj', _CEPH_JOURNAL_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = 'cmj'
    old = sys.argv
    sys.argv = ['cmj']
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    finally:
        sys.argv = old
    return mod


class TestCreatePartitions(unittest.TestCase):
    """Tests for create_partitions function."""

    @patch('subprocess.Popen')
    @patch('os.path.isdir', return_value=False)
    def test_create_partitions_mktable_fail(
        self, mock_isdir, mock_popen
    ):
        """create_partitions exits on mktable failure."""
        mod = _load_module()
        responses = [
            ('/dev/sda\n', '', 0),
            ('/dev/sda\n', '', 0),
            ('', 'error', 1),  # parted mktable fails
        ]
        idx = [0]

        def side_effect(*a, **kw):
            """Mock Popen side effect."""
            p = MagicMock()
            i = min(idx[0], len(responses) - 1)
            p.communicate.return_value = (
                responses[i][0], responses[i][1]
            )
            p.returncode = responses[i][2]
            idx[0] += 1
            return p

        mock_popen.side_effect = side_effect
        with self.assertRaises(SystemExit):
            mod.create_partitions('/dev/sda', [100])

    @patch('subprocess.Popen')
    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir', return_value=['uuid1'])
    @patch('os.path.islink', return_value=True)
    @patch('os.path.realpath', return_value='/dev/sda1')
    @patch('os.remove')
    def test_create_partitions_cleans_symlinks(
            self, mock_rm, mock_real, mock_islink, mock_ls,
            mock_isdir, mock_popen):
        """create_partitions removes old symlinks."""
        mod = _load_module()
        responses = [
            ('/dev/sda\n', '', 0),
            ('/dev/sda\n', '', 0),
            ('', '', 0),  # mktable
            ('', '', 0),  # mkpart
            ('', '', 0),  # sgdisk
        ]
        idx = [0]

        def side_effect(*a, **kw):
            """Mock Popen side effect."""
            p = MagicMock()
            i = min(idx[0], len(responses) - 1)
            p.communicate.return_value = (
                responses[i][0], responses[i][1]
            )
            p.returncode = responses[i][2]
            idx[0] += 1
            return p

        mock_popen.side_effect = side_effect
        mod.create_partitions('/dev/sda', [100])
        mock_rm.assert_called()

    @patch('subprocess.Popen')
    @patch('os.path.isdir', return_value=False)
    def test_create_partitions_nvme(self, mock_isdir, mock_popen):
        """create_partitions with nvme device uses p suffix."""
        mod = _load_module()
        # For is_partitioning_correct with nvme
        responses = [
            ('/dev/nvme0n1\n', '', 0),
            ('/dev/nvme0n1\n', '', 0),
            ('/dev/nvme0n1\n', '', 0),
            ('Partition Table: gpt\n', '', 0),
            ('/dev/nvme0n1p1\n', '', 0),
            ('Disk /dev/nvme0n1p1: 100.0MiB\n', '', 0),
            ('', '', 0),
        ]
        idx = [0]

        def side_effect(*a, **kw):
            """Mock Popen side effect."""
            p = MagicMock()
            i = min(idx[0], len(responses) - 1)
            p.communicate.return_value = (
                responses[i][0], responses[i][1]
            )
            p.returncode = responses[i][2]
            idx[0] += 1
            return p

        mock_popen.side_effect = side_effect
        result = mod.is_partitioning_correct('/dev/nvme0n1', [100])
        self.assertTrue(result)


class TestMountDataPartition(unittest.TestCase):
    """Tests for mount_data_partition."""

    @patch('subprocess.Popen')
    def test_already_mounted(self, mock_popen):
        """Return path if already mounted."""
        mod = _load_module()
        responses = [
            ('/dev/sda1\n', '', 0),  # udevadm
            ('/dev/sda1\n', '', 0),  # readlink
            ('/dev/sda1 on /var/lib/ceph/osd/ceph-0 type xfs\n', '', 0),
        ]
        idx = [0]

        def popen_side_effect(*args, **kwargs):
            """Mock Popen side effect."""
            p = MagicMock()
            i = min(idx[0], len(responses) - 1)
            p.communicate.return_value = (
                responses[i][0], responses[i][1]
            )
            p.returncode = responses[i][2]
            idx[0] += 1
            return p

        mock_popen.side_effect = popen_side_effect
        result = mod.mount_data_partition('/dev/sda1', 0)
        self.assertIn('ceph-0', result)

    @patch('subprocess.Popen')
    def test_mount_success(self, mock_popen):
        """Mount succeeds."""
        mod = _load_module()
        responses = [
            ('/dev/sda1\n', '', 0),
            ('/dev/sda1\n', '', 0),
            ('', '', 0),  # mount output (not mounted)
            ('', '', 0),  # mount command
        ]
        idx = [0]

        def popen_side_effect(*args, **kwargs):
            """Mock Popen side effect."""
            p = MagicMock()
            i = min(idx[0], len(responses) - 1)
            p.communicate.return_value = (
                responses[i][0], responses[i][1]
            )
            p.returncode = responses[i][2]
            idx[0] += 1
            return p

        mock_popen.side_effect = popen_side_effect
        result = mod.mount_data_partition('/dev/sda1', 0)
        self.assertIn('ceph-0', result)

    @patch('subprocess.Popen')
    def test_mount_failure_exits(self, mock_popen):
        """Mount failure exits."""
        mod = _load_module()
        responses = [
            ('/dev/sda1\n', '', 0),
            ('/dev/sda1\n', '', 0),
            ('', '', 0),
            ('', 'err', 1),  # mount fails
        ]
        idx = [0]

        def popen_side_effect(*args, **kwargs):
            """Mock Popen side effect."""
            p = MagicMock()
            i = min(idx[0], len(responses) - 1)
            p.communicate.return_value = (
                responses[i][0], responses[i][1]
            )
            p.returncode = responses[i][2]
            idx[0] += 1
            return p

        mock_popen.side_effect = popen_side_effect
        with self.assertRaises(SystemExit):
            mod.mount_data_partition('/dev/sda1', 0)


class TestIsLocationCorrect(unittest.TestCase):
    """Tests for is_location_correct."""

    @patch('os.path.realpath', return_value='/dev/sdb1')
    @patch('subprocess.Popen')
    def test_correct(self, mock_popen, mock_real):
        """Returns True when journal points to correct device."""
        mod = _load_module()
        p = MagicMock()
        p.communicate.return_value = ('/dev/sdb1\n', '')
        p.returncode = 0
        mock_popen.return_value = p
        self.assertTrue(mod.is_location_correct('/mnt', '/dev/sdb1', 0))

    @patch('os.path.realpath', return_value='/dev/sdc1')
    @patch('subprocess.Popen')
    def test_incorrect(self, mock_popen, mock_real):
        """Returns False when journal points to wrong device."""
        mod = _load_module()
        p = MagicMock()
        p.communicate.return_value = ('/dev/sdb1\n', '')
        p.returncode = 0
        mock_popen.return_value = p
        self.assertFalse(
            mod.is_location_correct('/mnt', '/dev/sdb1', 0)
        )


class TestFixLocation(unittest.TestCase):
    """Tests for fix_location."""

    @patch('subprocess.Popen')
    @patch('os.path.lexists', return_value=True)
    @patch('os.unlink')
    @patch('os.symlink')
    def test_fix_location_success(
            self, mock_sym, mock_unlink, mock_lex, mock_popen):
        """fix_location creates symlink and formats journal."""
        mod = _load_module()
        responses = [
            ('/dev/sdb1\n', '', 0),  # udevadm
            ('/dev/sdb1\n', '', 0),  # readlink
            ('/dev/sdb1: PARTUUID="abc-123"\n', '', 0),  # blkid
            ('', '', 0),  # dd
            ('', '', 0),  # ceph-osd mkjournal
        ]
        idx = [0]

        def popen_side_effect(*args, **kwargs):
            """Mock Popen side effect."""
            p = MagicMock()
            i = min(idx[0], len(responses) - 1)
            p.communicate.return_value = (
                responses[i][0], responses[i][1]
            )
            p.returncode = responses[i][2]
            idx[0] += 1
            return p

        mock_popen.side_effect = popen_side_effect
        m = mock_open()
        with patch('builtins.open', m):
            mod.fix_location('/mnt/osd', '/dev/sdb1', 0)
        mock_sym.assert_called()


class TestMainPartitions(unittest.TestCase):
    """Tests for main() with partitions command."""

