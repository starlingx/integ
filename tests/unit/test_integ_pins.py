#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for pynetlink DPLL pins module."""

import unittest
import os
import sys

# Path setup handled by conftest.py

from pynetlink.dpll.constants import PinDirection
from pynetlink.dpll.constants import PinState
from pynetlink.dpll.constants import PinType
from pynetlink.dpll.devices import DpllDevice
from pynetlink.dpll.devices import DpllDevices
from pynetlink.dpll.pins import DpllPin
from pynetlink.dpll.pins import DpllPins


def _make_raw_device(dev_id=1, clock_id=100):
    """Helper to create raw device dict."""
    return {
        'id': dev_id,
        'clock-id': clock_id,
        'module-name': 'ice',
        'mode': 'automatic',
        'mode-supported': ['manual', 'automatic'],
        'type': 'eec',
        'lock-status': 'locked-ho-acq',
        'lock-status-error': 'none',
    }


def _make_raw_pin_parent_device(pin_id=10, parent_id=1):
    """Helper to create raw pin with parent-device."""
    return {
        'id': pin_id,
        'board-label': 'SMA1',
        'panel-label': 'panel-1',
        'package-label': 'pkg-1',
        'type': 'ext',
        'parent-device': [
            {
                'parent-id': parent_id,
                'state': 'connected',
                'prio': 5,
                'direction': 'input',
                'phase-offset': 100,
            }
        ],
    }


def _make_raw_pin_parent_id(pin_id=11, parent_id=1):
    """Helper to create raw pin with parent-id."""
    return {
        'id': pin_id,
        'board-label': 'SMA2',
        'panel-label': 'panel-2',
        'package-label': 'pkg-2',
        'type': 'gnss',
        'parent-id': parent_id,
        'state': 'selectable',
        'prio': 3,
        'direction': 'output',
        'phase-offset': 50,
    }


class TestDpllPinLoadPinParentDevice(unittest.TestCase):
    """Tests for DpllPin.loadPin with parent-device field."""

    def setUp(self):
        """Create a test device."""
        self.device = DpllDevice.loadDevice(_make_raw_device(dev_id=1))

    def test_load_pin_parent_device(self):
        """Load pin with parent-device field."""
        raw_pin = _make_raw_pin_parent_device(pin_id=10, parent_id=1)
        pin = DpllPin.loadPin(self.device, raw_pin)
        self.assertEqual(pin.pin_id, 10)
        self.assertEqual(pin.dev_id, 1)
        self.assertEqual(pin.pin_board_label, 'SMA1')
        self.assertEqual(pin.pin_panel_label, 'panel-1')
        self.assertEqual(pin.pin_package_label, 'pkg-1')
        self.assertEqual(pin.pin_type, PinType.EXT)
        self.assertEqual(pin.pin_state, PinState.CONNECTED)
        self.assertEqual(pin.pin_priority, 5)
        self.assertEqual(pin.pin_direction, PinDirection.INPUT)
        self.assertEqual(pin.pin_phase_offset, 100)

    def test_load_pin_no_parent_match_raises(self):
        """Loading pin with no matching parent-id raises ValueError."""
        raw_pin = _make_raw_pin_parent_device(pin_id=10, parent_id=999)
        with self.assertRaises(ValueError):
            DpllPin.loadPin(self.device, raw_pin)

    def test_load_pin_none_device_raises(self):
        """Loading pin with None device raises ValueError."""
        raw_pin = _make_raw_pin_parent_device()
        with self.assertRaises(ValueError):
            DpllPin.loadPin(None, raw_pin)

    def test_load_pin_none_pin_raises(self):
        """Loading pin with None pin raises ValueError."""
        with self.assertRaises(ValueError):
            DpllPin.loadPin(self.device, None)


class TestDpllPinLoadPinParentId(unittest.TestCase):
    """Tests for DpllPin.loadPin with parent-id field."""

    def setUp(self):
        """Create a test device."""
        self.device = DpllDevice.loadDevice(_make_raw_device(dev_id=1))

    def test_load_pin_parent_id(self):
        """Load pin with parent-id field."""
        raw_pin = _make_raw_pin_parent_id(pin_id=11, parent_id=1)
        pin = DpllPin.loadPin(self.device, raw_pin)
        self.assertEqual(pin.pin_id, 11)
        self.assertEqual(pin.pin_type, PinType.GNSS)
        self.assertEqual(pin.pin_state, PinState.SELECTABLE)
        self.assertEqual(pin.pin_priority, 3)
        self.assertEqual(pin.pin_direction, PinDirection.OUTPUT)

    def test_load_pin_no_reference_raises(self):
        """Pin without parent-device or parent-id raises ValueError."""
        raw_pin = {'id': 20, 'type': 'ext'}
        with self.assertRaises(ValueError):
            DpllPin.loadPin(self.device, raw_pin)

    def test_load_pin_optional_labels_missing(self):
        """Pin without optional labels gets None defaults."""
        raw_pin = {
            'id': 30,
            'type': 'ext',
            'parent-id': 1,
        }
        pin = DpllPin.loadPin(self.device, raw_pin)
        self.assertIsNone(pin.pin_board_label)
        self.assertIsNone(pin.pin_panel_label)
        self.assertIsNone(pin.pin_package_label)

    def test_load_pin_default_state(self):
        """Pin without state gets UNDEFINED default."""
        raw_pin = {
            'id': 31,
            'type': 'ext',
            'parent-id': 1,
        }
        pin = DpllPin.loadPin(self.device, raw_pin)
        self.assertEqual(pin.pin_state, PinState.UNDEFINED)

    def test_load_pin_default_direction(self):
        """Pin without direction gets UNDEFINED default."""
        raw_pin = {
            'id': 32,
            'type': 'ext',
            'parent-id': 1,
        }
        pin = DpllPin.loadPin(self.device, raw_pin)
        self.assertEqual(pin.pin_direction, PinDirection.UNDEFINED)

    def test_pin_is_frozen(self):
        """Verify DpllPin is immutable."""
        raw_pin = _make_raw_pin_parent_id()
        pin = DpllPin.loadPin(self.device, raw_pin)
        with self.assertRaises(AttributeError):
            pin.pin_id = 999  # pylint: disable=assigning-non-slot

    def test_pin_inherits_device_fields(self):
        """Verify pin inherits device fields."""
        raw_pin = _make_raw_pin_parent_id()
        pin = DpllPin.loadPin(self.device, raw_pin)
        self.assertEqual(pin.dev_clock_id, 100)
        self.assertEqual(pin.dev_module_name, 'ice')


class TestDpllPinsLoadPins(unittest.TestCase):
    """Tests for DpllPins.loadPins class method."""

    def setUp(self):
        """Create test devices and pins."""
        self.devices = [
            _make_raw_device(dev_id=1, clock_id=100),
            _make_raw_device(dev_id=2, clock_id=200),
        ]

    def test_load_pins_parent_device(self):
        """Load pins with parent-device references."""
        pins = [_make_raw_pin_parent_device(pin_id=10, parent_id=1)]
        result = DpllPins.loadPins(self.devices, pins)
        self.assertEqual(len(result), 1)

    def test_load_pins_parent_id(self):
        """Load pins with parent-id references."""
        pins = [_make_raw_pin_parent_id(pin_id=11, parent_id=1)]
        result = DpllPins.loadPins(self.devices, pins)
        self.assertEqual(len(result), 1)

    def test_load_pins_skips_parent_pin(self):
        """Pins with parent-pin field are skipped."""
        pins = [{
            'id': 20, 'type': 'ext',
            'parent-pin': [{'parent-id': 1}]
        }]
        result = DpllPins.loadPins(self.devices, pins)
        self.assertEqual(len(result), 0)

    def test_load_pins_empty(self):
        """Loading empty pins list returns empty DpllPins."""
        result = DpllPins.loadPins(self.devices, [])
        self.assertEqual(len(result), 0)

    def test_load_pins_multiple_parent_devices(self):
        """Pin with multiple parent-device entries.

        Creates multiple DpllPin objects.
        """
        pin = {
            'id': 10,
            'board-label': 'SMA1',
            'type': 'ext',
            'parent-device': [
                {
                    'parent-id': 1,
                    'state': 'connected',
                    'direction': 'input'
                },
                {
                    'parent-id': 2,
                    'state': 'selectable',
                    'direction': 'output'
                },
            ],
        }
        result = DpllPins.loadPins(self.devices, [pin])
        self.assertEqual(len(result), 2)


class TestDpllPinsFilters(unittest.TestCase):
    """Tests for DpllPins filter methods."""

    def setUp(self):
        """Create test pins."""
        devices = [
            _make_raw_device(dev_id=1, clock_id=100),
            _make_raw_device(dev_id=2, clock_id=200),
        ]
        pins_raw = [
            {
                'id': 10, 'board-label': 'SMA1', 'panel-label': 'P1',
                'package-label': 'PKG1', 'type': 'ext',
                'parent-device': [
                    {'parent-id': 1, 'state': 'connected',
                     'prio': 5, 'direction': 'input'}
                ],
            },
            {
                'id': 11, 'board-label': 'SMA2', 'panel-label': 'P2',
                'package-label': 'PKG2', 'type': 'gnss',
                'parent-device': [
                    {'parent-id': 2, 'state': 'selectable',
                     'prio': 3, 'direction': 'output'}
                ],
            },
            {
                'id': 12, 'board-label': 'SMA1', 'panel-label': 'P1',
                'package-label': 'PKG1', 'type': 'synce-eth-port',
                'parent-device': [
                    {'parent-id': 1, 'state': 'disconnected',
                     'prio': 1, 'direction': 'input'}
                ],
            },
        ]
        self.pins = DpllPins.loadPins(devices, pins_raw)

    def test_filter_by_pin_id_found(self):
        """Filter by pin id returns matching pin."""
        result = self.pins.filter_by_pin_id(10)
        self.assertIsNotNone(result)
        self.assertEqual(result.pin_id, 10)

    def test_filter_by_pin_id_not_found(self):
        """Filter by non-existent pin id returns None."""
        result = self.pins.filter_by_pin_id(999)
        self.assertIsNone(result)

    def test_filter_by_pin_direction(self):
        """Filter by pin direction."""
        result = self.pins.filter_by_pin_direction(PinDirection.INPUT)
        self.assertEqual(len(result), 2)

    def test_filter_by_pin_directions(self):
        """Filter by multiple pin directions."""
        result = self.pins.filter_by_pin_directions(
            [PinDirection.INPUT, PinDirection.OUTPUT])
        self.assertEqual(len(result), 3)

    def test_filter_by_pin_board_label(self):
        """Filter by board label."""
        result = self.pins.filter_by_pin_board_label('SMA1')
        self.assertEqual(len(result), 2)

    def test_filter_by_pin_board_labels(self):
        """Filter by multiple board labels."""
        result = self.pins.filter_by_pin_board_labels(['SMA1', 'SMA2'])
        self.assertEqual(len(result), 3)

    def test_filter_by_pin_panel_label(self):
        """Filter by panel label."""
        result = self.pins.filter_by_pin_panel_label('P1')
        self.assertEqual(len(result), 2)

    def test_filter_by_pin_panel_labels(self):
        """Filter by multiple panel labels."""
        result = self.pins.filter_by_pin_panel_labels(['P1', 'P2'])
        self.assertEqual(len(result), 3)

    def test_filter_by_pin_package_label(self):
        """Filter by package label."""
        result = self.pins.filter_by_pin_package_label('PKG1')
        self.assertEqual(len(result), 2)

    def test_filter_by_pin_package_labels(self):
        """Filter by multiple package labels."""
        result = self.pins.filter_by_pin_package_labels(
            ['PKG1', 'PKG2']
        )
        self.assertEqual(len(result), 3)

    def test_filter_by_pin_state(self):
        """Filter by pin state."""
        result = self.pins.filter_by_pin_state(PinState.CONNECTED)
        self.assertEqual(len(result), 1)

    def test_filter_by_pin_states(self):
        """Filter by multiple pin states."""
        result = self.pins.filter_by_pin_states(
            [PinState.CONNECTED, PinState.SELECTABLE])
        self.assertEqual(len(result), 2)

    def test_filter_by_pin_type(self):
        """Filter by pin type."""
        result = self.pins.filter_by_pin_type(PinType.EXT)
        self.assertEqual(len(result), 1)

    def test_filter_by_pin_types(self):
        """Filter by multiple pin types."""
        result = self.pins.filter_by_pin_types(
            [PinType.EXT, PinType.GNSS]
        )
        self.assertEqual(len(result), 2)

    def test_order_by_pin_priority_ascending(self):
        """Order pins by priority ascending."""
        result = self.pins.order_by_pin_priority()
        priorities = [p.pin_priority for p in result]
        non_none = [p for p in priorities if p is not None]
        self.assertEqual(non_none, sorted(non_none))

    def test_order_by_pin_priority_descending(self):
        """Order pins by priority descending."""
        result = self.pins.order_by_pin_priority(reverse=True)
        self.assertIsInstance(result, list)

    def test_filter_returns_dpll_pins_type(self):
        """Verify filter methods return DpllPins instances."""
        result = self.pins.filter_by_pin_direction(PinDirection.INPUT)
        self.assertIsInstance(result, DpllPins)

    def test_filter_by_device_clock_id_inherited(self):
        """Verify inherited filter_by_device_clock_id works on pins."""
        result = self.pins.filter_by_device_clock_id(100)
        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
