#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for pynetlink DPLL devices module."""

import unittest
import os
import sys

# Path setup handled by conftest.py

from pynetlink.dpll.constants import DeviceMode
from pynetlink.dpll.constants import DeviceType
from pynetlink.dpll.constants import LockStatus
from pynetlink.dpll.constants import LockStatusError

# Import devices directly to avoid
# triggering NetlinkDPLL class-level init
from pynetlink.dpll.devices import DpllDevice
from pynetlink.dpll.devices import DpllDevices


def _make_raw_device(dev_id=1, clock_id=100, **overrides):
    """Helper to create raw device dict."""
    base = {
        'id': dev_id,
        'clock-id': clock_id,
        'module-name': 'ice',
        'mode': 'automatic',
        'mode-supported': ['manual', 'automatic'],
        'type': 'eec',
        'lock-status': 'locked-ho-acq',
        'lock-status-error': 'none',
    }
    base.update(overrides)
    return base


class TestDpllDeviceLoadDevice(unittest.TestCase):
    """Tests for DpllDevice.loadDevice class method."""

    def test_load_full_device(self):
        """Load device with all fields populated."""
        raw = _make_raw_device()
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.dev_id, 1)
        self.assertEqual(dev.dev_clock_id, 100)
        self.assertEqual(dev.dev_module_name, 'ice')
        self.assertEqual(dev.dev_mode, DeviceMode.AUTO)
        self.assertEqual(dev.dev_type, DeviceType.EEC)
        self.assertEqual(
            dev.lock_status,
            LockStatus.LOCKED_AND_HOLDOVER
        )
        self.assertEqual(dev.lock_status_error, LockStatusError.NONE)

    def test_load_minimal_device(self):
        """Load device with only required fields."""
        raw = {'id': 2, 'clock-id': 200}
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.dev_id, 2)
        self.assertEqual(dev.dev_clock_id, 200)
        self.assertEqual(dev.dev_mode, DeviceMode.UNDEFINED)
        self.assertEqual(dev.dev_type, DeviceType.UNDEFINED)
        self.assertEqual(dev.lock_status, LockStatus.UNDEFINED)
        self.assertIsNone(dev.dev_module_name)
        self.assertIsNone(dev.dev_pad)

    def test_load_device_none_raises(self):
        """Loading None device raises ValueError."""
        with self.assertRaises(ValueError):
            DpllDevice.loadDevice(None)

    def test_load_device_with_pad(self):
        """Load device with pad field."""
        raw = _make_raw_device(pad='some-pad')
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.dev_pad, 'some-pad')

    def test_load_device_with_clock_quality(self):
        """Load device with clock quality level."""
        raw = _make_raw_device(**{'clock-quality-level': 'QL-PRC'})
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.dev_clock_quality_level, 'QL-PRC')

    def test_load_device_mode_supported_list(self):
        """Verify mode_supported is parsed as list of DeviceMode."""
        raw = _make_raw_device()
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(len(dev.dev_mode_supported), 2)
        self.assertIn(DeviceMode.MANUAL, dev.dev_mode_supported)
        self.assertIn(DeviceMode.AUTO, dev.dev_mode_supported)

    def test_load_device_no_mode_supported(self):
        """Device without mode-supported gets empty list."""
        raw = {'id': 3, 'clock-id': 300}
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.dev_mode_supported, [])

    def test_device_is_frozen(self):
        """Verify DpllDevice is immutable (frozen dataclass)."""
        dev = DpllDevice.loadDevice(_make_raw_device())
        with self.assertRaises(AttributeError):
            dev.dev_id = 999  # pylint: disable=assigning-non-slot

    def test_device_hash(self):
        """Verify DpllDevice is hashable (only dev_id in hash)."""
        dev1 = DpllDevice.loadDevice(_make_raw_device(dev_id=1))
        dev2 = DpllDevice.loadDevice(
            _make_raw_device(dev_id=1, clock_id=999)
        )
        self.assertEqual(hash(dev1), hash(dev2))

    def test_device_equality(self):
        """Verify two devices with same id are equal."""
        dev1 = DpllDevice.loadDevice(_make_raw_device(dev_id=5))
        dev2 = DpllDevice.loadDevice(_make_raw_device(dev_id=5))
        self.assertEqual(dev1, dev2)

    def test_device_inequality(self):
        """Verify two devices with different ids are not equal."""
        dev1 = DpllDevice.loadDevice(_make_raw_device(dev_id=1))
        dev2 = DpllDevice.loadDevice(_make_raw_device(dev_id=2))
        self.assertNotEqual(dev1, dev2)

    def test_load_device_pps_type(self):
        """Load device with PPS type."""
        raw = _make_raw_device(type='pps')
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.dev_type, DeviceType.PPS)

    def test_load_device_manual_mode(self):
        """Load device with manual mode."""
        raw = _make_raw_device(mode='manual')
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.dev_mode, DeviceMode.MANUAL)

    def test_load_device_holdover_status(self):
        """Load device with holdover lock status."""
        raw = _make_raw_device(**{'lock-status': 'holdover'})
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.lock_status, LockStatus.HOLDOVER)

    def test_load_device_unlocked_status(self):
        """Load device with unlocked lock status."""
        raw = _make_raw_device(**{'lock-status': 'unlocked'})
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(dev.lock_status, LockStatus.UNLOCKED)

    def test_load_device_media_down_error(self):
        """Load device with media-down lock status error."""
        raw = _make_raw_device(**{'lock-status-error': 'media-down'})
        dev = DpllDevice.loadDevice(raw)
        self.assertEqual(
            dev.lock_status_error,
            LockStatusError.MEDIA_DOWN
        )


class TestDpllDevicesLoadDevices(unittest.TestCase):
    """Tests for DpllDevices.loadDevices class method."""

    def test_load_empty_list(self):
        """Loading empty list returns empty DpllDevices."""
        devs = DpllDevices.loadDevices([])
        self.assertEqual(len(devs), 0)

    def test_load_single_device(self):
        """Loading single device list."""
        devs = DpllDevices.loadDevices([_make_raw_device()])
        self.assertEqual(len(devs), 1)

    def test_load_multiple_devices(self):
        """Loading multiple devices."""
        raw_list = [
            _make_raw_device(dev_id=1, clock_id=100),
            _make_raw_device(dev_id=2, clock_id=200),
            _make_raw_device(dev_id=3, clock_id=100),
        ]
        devs = DpllDevices.loadDevices(raw_list)
        self.assertEqual(len(devs), 3)

    def test_load_duplicate_devices(self):
        """Duplicate devices (same id) are deduplicated in set."""
        raw_list = [
            _make_raw_device(dev_id=1),
            _make_raw_device(dev_id=1),
        ]
        devs = DpllDevices.loadDevices(raw_list)
        self.assertEqual(len(devs), 1)


class TestDpllDevicesFilters(unittest.TestCase):
    """Tests for DpllDevices filter methods."""

    def setUp(self):
        """Create a set of test devices."""
        self.raw_list = [
            _make_raw_device(dev_id=1, clock_id=100, type='eec',
                             mode='automatic',
                             **{'lock-status': 'locked-ho-acq',
                                'lock-status-error': 'none'}),
            _make_raw_device(dev_id=2, clock_id=200, type='pps',
                             mode='manual',
                             **{'lock-status': 'holdover',
                                'lock-status-error': 'media-down'}),
            _make_raw_device(dev_id=3, clock_id=100, type='eec',
                             mode='automatic',
                             **{'lock-status': 'unlocked',
                                'lock-status-error': 'undefined'}),
        ]
        self.devs = DpllDevices.loadDevices(self.raw_list)

    def test_filter_by_device_clock_id(self):
        """Filter devices by clock id."""
        result = self.devs.filter_by_device_clock_id(100)
        self.assertEqual(len(result), 2)

    def test_filter_by_device_clock_id_no_match(self):
        """Filter by non-existent clock id returns empty."""
        result = self.devs.filter_by_device_clock_id(999)
        self.assertEqual(len(result), 0)

    def test_filter_by_device_clock_ids(self):
        """Filter devices by multiple clock ids."""
        result = self.devs.filter_by_device_clock_ids([100, 200])
        self.assertEqual(len(result), 3)

    def test_filter_by_device_id_found(self):
        """Filter by device id returns matching device."""
        result = self.devs.filter_by_device_id(1)
        self.assertIsNotNone(result)
        self.assertEqual(result.dev_id, 1)

    def test_filter_by_device_id_not_found(self):
        """Filter by non-existent device id returns None."""
        result = self.devs.filter_by_device_id(999)
        self.assertIsNone(result)

    def test_filter_by_device_type(self):
        """Filter devices by type."""
        result = self.devs.filter_by_device_type(DeviceType.EEC)
        self.assertEqual(len(result), 2)

    def test_filter_by_device_types(self):
        """Filter devices by multiple types."""
        result = self.devs.filter_by_device_types(
            [DeviceType.EEC, DeviceType.PPS])
        self.assertEqual(len(result), 3)

    def test_filter_by_device_mode(self):
        """Filter devices by mode."""
        result = self.devs.filter_by_device_mode(DeviceMode.AUTO)
        self.assertEqual(len(result), 2)

    def test_filter_by_device_mode_supported(self):
        """Filter devices by supported mode."""
        result = self.devs.filter_by_device_mode_supported(
            DeviceMode.MANUAL
        )
        # All devices have manual in mode-supported
        self.assertGreaterEqual(len(result), 1)

    def test_filter_by_device_lock_status(self):
        """Filter devices by lock status."""
        result = self.devs.filter_by_device_lock_status(
            LockStatus.HOLDOVER
        )
        self.assertEqual(len(result), 1)

    def test_filter_by_device_lock_statuses(self):
        """Filter devices by multiple lock statuses."""
        result = self.devs.filter_by_device_lock_statuses(
            [LockStatus.HOLDOVER, LockStatus.UNLOCKED])
        self.assertEqual(len(result), 2)

    def test_filter_by_device_lock_status_error(self):
        """Filter devices by lock status error."""
        result = self.devs.filter_by_device_lock_status_error(
            LockStatusError.MEDIA_DOWN)
        self.assertEqual(len(result), 1)

    def test_filter_by_device_lock_status_errors(self):
        """Filter devices by multiple lock status errors."""
        result = self.devs.filter_by_device_lock_status_errors(
            [LockStatusError.MEDIA_DOWN, LockStatusError.NONE])
        self.assertEqual(len(result), 2)

    def test_filter_returns_dpll_devices_type(self):
        """Verify filter methods return DpllDevices instances."""
        result = self.devs.filter_by_device_clock_id(100)
        self.assertIsInstance(result, DpllDevices)


if __name__ == '__main__':
    unittest.main()
