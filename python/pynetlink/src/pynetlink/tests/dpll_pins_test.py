#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module tests the DpllPin and DpllPins classes"""

import json
import os
from unittest import TestCase
from ..dpll import DpllPins
from ..dpll import DpllPin
from ..dpll import PinFields
from ..dpll import PinParentFields
from ..dpll import PinDirection
from ..dpll import PinState
from ..dpll import PinType
from ..dpll import DpllDevice
from ..dpll import DeviceMode
from ..dpll import DeviceType
from ..dpll import LockStatus
from ..dpll import LockStatusError


class DpllPinTestCase(TestCase):

    def assert_device_fields(self, pin: DpllPin, device: DpllDevice):

        self.assertEqual(
            pin.dev_id,
            device.dev_id,
            f'Device id does not match: {pin.dev_id} != {device.dev_id}')
        self.assertEqual(
            pin.dev_clock_id,
            device.dev_clock_id,
            f'Device clock id does not match: {pin.dev_clock_id} != {device.dev_clock_id}')
        self.assertEqual(
            pin.dev_mode,
            device.dev_mode,
            f'Device mode does not match: {pin.dev_mode} != {device.dev_mode}')
        self.assertListEqual(
            pin.dev_mode_supported,
            device.dev_mode_supported,
            f'Device mode supported does not match: {pin.dev_mode_supported} != {device.dev_mode_supported}')
        self.assertEqual(
            pin.dev_module_name,
            device.dev_module_name,
            f'Device module name does not match: {pin.dev_module_name} != {device.dev_module_name}')
        self.assertEqual(
            pin.dev_pad,
            device.dev_pad,
            f'Device pad does not match: {pin.dev_pad} != {device.dev_pad}')
        self.assertEqual(
            pin.dev_type,
            device.dev_type,
            f'Device type does not match: {pin.dev_type} != {device.dev_type}')
        self.assertEqual(
            pin.lock_status,
            device.lock_status,
            f'Device lock status does not match: {pin.lock_status} != {device.lock_status}')
        self.assertEqual(
            pin.lock_status_error,
            device.lock_status_error,
            f'Device lock status error does not match: {pin.lock_status_error} != {device.lock_status_error}')

    def test_create_new_pin_instance_using_all_fields(self):

        dev_id = 1
        dev_clock_id = 'clock-id'
        dev_clock_quality_level = 'itu-opt1-prc'
        dev_mode = DeviceMode.AUTO
        dev_mode_supported = [DeviceMode.AUTO]
        dev_module_name = 'module'
        dev_pad = 'pad'
        dev_type = DeviceType.PPS
        pin_id = 101
        pin_board_label = 'board-label'
        pin_panel_label = 'panel-label'
        pin_package_label = 'package-label'
        pin_type = PinType.EXT
        pin_state = PinState.DISCONNECTED
        pin_priority = 2
        pin_phase_offset = 10101010
        pin_direction = PinDirection.OUTPUT
        lock_status = LockStatus.UNLOCKED
        lock_status_error = LockStatusError.FFO_TOO_HIGH

        pin = DpllPin(
            dev_id=dev_id,
            dev_clock_id=dev_clock_id,
            dev_clock_quality_level=dev_clock_quality_level,
            dev_mode=dev_mode,
            dev_mode_supported=dev_mode_supported,
            dev_module_name=dev_module_name,
            dev_pad=dev_pad,
            dev_type=dev_type,
            pin_id=pin_id,
            pin_board_label=pin_board_label,
            pin_panel_label=pin_panel_label,
            pin_package_label=pin_package_label,
            pin_type=pin_type,
            pin_state=pin_state,
            pin_priority=pin_priority,
            pin_phase_offset=pin_phase_offset,
            pin_direction=pin_direction,
            lock_status=lock_status,
            lock_status_error=lock_status_error,
        )

        self.assertEqual(
            pin.dev_id,
            dev_id,
            f'Device id does not match: {pin.dev_id} != {dev_id}')
        self.assertEqual(
            pin.dev_clock_id,
            dev_clock_id,
            f'Device clock id does not match: {pin.dev_clock_id} != {dev_clock_id}')
        self.assertEqual(
            pin.dev_clock_quality_level,
            dev_clock_quality_level,
            f'Device clock quality level does not match: {pin.dev_clock_quality_level} != {dev_clock_quality_level}')
        self.assertEqual(
            pin.dev_mode,
            dev_mode,
            f'Device mode does not match: {pin.dev_mode} != {dev_mode}')
        self.assertListEqual(
            pin.dev_mode_supported,
            dev_mode_supported,
            f'Device mode supported does not match: {pin.dev_mode_supported} != {dev_mode_supported}')
        self.assertEqual(
            pin.dev_module_name,
            dev_module_name,
            f'Device module name does not match: {pin.dev_module_name} != {dev_module_name}')
        self.assertEqual(
            pin.dev_pad,
            dev_pad,
            f'Device pad does not match: {pin.dev_pad} != {dev_pad}')
        self.assertEqual(
            pin.dev_type,
            dev_type,
            f'Device type does not match: {pin.dev_type} != {dev_type}')
        self.assertEqual(
            pin.pin_id,
            pin_id,
            f'Pin id does not match: {pin.pin_id} != {pin_id}')
        self.assertEqual(
            pin.pin_board_label,
            pin_board_label,
            f'Pin board label does not match: {pin.pin_board_label} != {pin_board_label}')
        self.assertEqual(
            pin.pin_panel_label,
            pin_panel_label,
            f'Pin panel label does not match: {pin.pin_panel_label} != {pin_panel_label}')
        self.assertEqual(
            pin.pin_package_label,
            pin_package_label,
            f'Pin package label does not match: {pin.pin_package_label} != {pin_package_label}')
        self.assertEqual(
            pin.pin_type,
            pin_type,
            f'Pin type does not match: {pin.pin_type} != {pin_type}')
        self.assertEqual(
            pin.pin_state,
            pin_state,
            f'Pin state does not match: {pin.pin_state} != {pin_state}')
        self.assertEqual(
            pin.pin_priority,
            pin_priority,
            f'Pin priority does not match: {pin.pin_priority} != {pin_priority}')
        self.assertEqual(
            pin.pin_phase_offset,
            pin_phase_offset,
            f'Pin phase offset does not match: {pin.pin_phase_offset} != {pin_phase_offset}')
        self.assertEqual(
            pin.pin_direction,
            pin_direction,
            f'Pin direction does not match: {pin.pin_direction} != {pin_direction}')
        self.assertEqual(
            pin.lock_status,
            lock_status,
            f'Device lock status does not match: {pin.lock_status} != {lock_status}')
        self.assertEqual(
            pin.lock_status_error,
            lock_status_error,
            f'Device lock status error does not match: {pin.lock_status_error} != {lock_status_error}')

    def test_create_new_pin_instance_using_only_required_fields(self):

        dev_id = 4
        dev_clock_id = 'clock-id/4'
        pin_id = 44
        pin_type = PinType.OCXO

        pin = DpllPin(
            dev_id=dev_id,
            dev_clock_id=dev_clock_id,
            pin_id=pin_id,
            pin_type=pin_type,
        )

        self.assertEqual(
            pin.dev_id,
            dev_id,
            f'Device id does not match: {pin.dev_id} != {dev_id}')
        self.assertEqual(
            pin.dev_clock_id,
            dev_clock_id,
            f'Device clock id does not match: {pin.dev_clock_id} != {dev_clock_id}')
        self.assertIsNone(
            pin.dev_clock_quality_level,
            f'Device clock quality level is not none: {pin.dev_clock_quality_level}')
        self.assertEqual(
            pin.dev_mode,
            DeviceMode.UNDEFINED,
            f'Device mode is not {DeviceMode.UNDEFINED}: {pin.dev_mode}')
        self.assertListEqual(
            pin.dev_mode_supported,
            list(),
            f'Device mode supported is not empty: {pin.dev_mode_supported}')
        self.assertIsNone(
            pin.dev_module_name,
            f'Device module name is not none: {pin.dev_module_name}')
        self.assertIsNone(
            pin.dev_pad,
            f'Device pad is not none: {pin.dev_pad}')
        self.assertEqual(
            pin.dev_type,
            DeviceType.UNDEFINED,
            f'Device type is not {DeviceType.UNDEFINED}: {pin.dev_pad}')
        self.assertEqual(
            pin.pin_id,
            pin_id,
            f'Pin id does not match: {pin.pin_id} != {pin_id}')
        self.assertIsNone(
            pin.pin_board_label,
            f'DPin board label is not none: {pin.pin_board_label}')
        self.assertIsNone(
            pin.pin_panel_label,
            f'Pin panel label is not none: {pin.pin_panel_label}')
        self.assertIsNone(
            pin.pin_package_label,
            f'Pin package label is not none: {pin.pin_package_label}')
        self.assertEqual(
            pin.pin_type,
            pin_type,
            f'Pin type does not match: {pin.pin_type} != {pin_type}')
        self.assertEqual(
            pin.pin_state,
            PinState.UNDEFINED,
            f'Pin state is not {PinState.UNDEFINED}: {pin.pin_state}')
        self.assertIsNone(
            pin.pin_priority,
            f'Pin priority is not none: {pin.pin_priority}')
        self.assertIsNone(
            pin.pin_phase_offset,
            f'Pin phase offset is not none: {pin.pin_phase_offset}')
        self.assertEqual(
            pin.pin_direction,
            PinDirection.UNDEFINED,
            f'Pin direction is not {PinDirection.UNDEFINED}: {pin.pin_direction}')
        self.assertEqual(
            pin.lock_status,
            LockStatus.UNDEFINED,
            f'Device lock status is not {LockStatus.UNDEFINED}: {pin.dev_pad}')
        self.assertEqual(
            pin.lock_status_error,
            LockStatusError.UNDEFINED,
            f'Device lock status error is not {LockStatusError.UNDEFINED}: {pin.lock_status_error}')

    def test_load_pin_raises_exception_when_device_is_none(self):

        with self.assertRaises(ValueError) as ctx:
            DpllPin.loadPin(None, {})

        self.assertIsInstance(ctx.exception, ValueError)
        self.assertEqual('Device parameter must be informed.', str(ctx.exception))

    def test_load_pin_raises_exception_when_pin_is_none(self):

        with self.assertRaises(ValueError) as ctx:
            DpllPin.loadPin(DpllDevice(1, 'clock-id1'), None)

        self.assertIsInstance(ctx.exception, ValueError)
        self.assertEqual('Pin parameter must be informed.', str(ctx.exception))

    def test_load_pin_from_dict_with_parent_device_and_all_fields_filled(self):

        device = DpllDevice(
            dev_id=1,
            dev_clock_id='5799633565437375000',
            dev_clock_quality_level='itu-opt1-eec1',
            dev_mode=DeviceMode.AUTO,
            dev_mode_supported=[DeviceMode.AUTO, DeviceMode.MANUAL],
            dev_module_name='module1',
            dev_pad='pad-value',
            dev_type=DeviceType.EEC,
            lock_status=LockStatus.LOCKED_AND_HOLDOVER,
            lock_status_error=LockStatusError.NONE,
        )

        pin_dict = {
            "id": 3,
            "board-label": "board-label1",
            "panel-label": "panel-label1",
            "package-label": "package-label1",
            "capabilities": ["state-can-change", "priority-can-change"],
            "clock-id": "5799633565437375000",
            "frequency": 1,
            "frequency-supported": [
                {
                    "frequency-max": 25000000,
                    "frequency-min": 1
                }
            ],
            "module-name": "module1",
            "parent-device": [
                {
                    "direction": "input",
                    "parent-id": 0,
                    "phase-offset": -346758571483350,
                    "prio": 3,
                    "state": "selectable"
                },
                {
                    "direction": "input",
                    "parent-id": 1,
                    "phase-offset": 349600,
                    "prio": 3,
                    "state": "connected"
                }
            ],
            "phase-adjust": 0,
            "phase-adjust-max": 559030611,
            "phase-adjust-min": -559030611,
            "type": "ext",
        }

        pin = DpllPin.loadPin(device, pin_dict)

        # Device
        self.assert_device_fields(pin, device)

        # Pin
        self.assertEqual(
            pin.pin_id,
            pin_dict[PinFields.ID],
            f'Pin id does not match: {pin.pin_id} != {pin_dict[PinFields.ID]}')
        self.assertEqual(
            pin.pin_board_label,
            pin_dict[PinFields.BOARD_LABEL],
            f'Pin board label does not match: {pin.pin_board_label} != {pin_dict[PinFields.BOARD_LABEL]}')
        self.assertEqual(
            pin.pin_panel_label,
            pin_dict[PinFields.PANEL_LABEL],
            f'Pin panel label does not match: {pin.pin_panel_label} != {pin_dict[PinFields.PANEL_LABEL]}')
        self.assertEqual(
            pin.pin_package_label,
            pin_dict[PinFields.PACKAGE_LABEL],
            f'Pin package label does not match: {pin.pin_package_label} != {pin_dict[PinFields.PACKAGE_LABEL]}')
        self.assertEqual(
            pin.pin_type,
            PinType(pin_dict[PinFields.TYPE]),
            f'Pin type does not match: {pin.pin_type} != {PinType(pin_dict[PinFields.TYPE])}')

        # Pin Parent Device
        pin_parent_dict = pin_dict[PinFields.PARENT_DEVICE][1]

        self.assertEqual(
            pin.pin_state,
            PinState(pin_parent_dict[PinParentFields.STATE]),
            f'Pin state does not match: {pin.pin_state} != {PinState(pin_parent_dict[PinParentFields.STATE])}')
        self.assertEqual(
            pin.pin_priority,
            pin_parent_dict[PinParentFields.PRIORITY],
            f'Pin priority does not match: {pin.pin_priority} != {pin_parent_dict[PinParentFields.PRIORITY]}')
        self.assertEqual(
            pin.pin_phase_offset,
            pin_parent_dict[PinParentFields.PHASE_OFFSET],
            f'Pin phase offset does not match: {pin.pin_phase_offset} != \
                                               {pin_parent_dict[PinParentFields.PHASE_OFFSET]}')
        self.assertEqual(
            pin.pin_direction,
            PinDirection(pin_parent_dict[PinParentFields.DIRECTION]),
            f'Pin direction does not match: {pin.pin_direction} != \
                                            {PinDirection(pin_parent_dict[PinParentFields.DIRECTION])}')

    def test_load_pin_from_dict_with_parent_device_and_only_required_fields(self):

        device = DpllDevice(
            dev_id=2,
            dev_clock_id='5799633565437375000',
        )

        pin_dict = {
            "id": 11,
            "type": "int-oscillator",
            "parent-device": [{"parent-id": 2}],
        }

        pin = DpllPin.loadPin(device, pin_dict)

        # Device
        self.assert_device_fields(pin, device)

        # Pin
        self.assertEqual(
            pin.pin_id,
            pin_dict[PinFields.ID],
            f'Pin id does not match: {pin.pin_id} != {pin_dict[PinFields.ID]}')
        self.assertIsNone(
            pin.pin_board_label,
            f'Pin board label is not none: {pin.pin_board_label}')
        self.assertIsNone(
            pin.pin_panel_label,
            f'Pin panel label is not none: {pin.pin_panel_label}')
        self.assertIsNone(
            pin.pin_package_label,
            f'Pin package label is not none: {pin.pin_package_label}')
        self.assertEqual(
            pin.pin_type,
            PinType(pin_dict[PinFields.TYPE]),
            f'Pin type does not match: {pin.pin_type} != {PinType(pin_dict[PinFields.TYPE])}')
        self.assertEqual(
            pin.pin_state,
            PinState.UNDEFINED,
            f'Pin state is not {PinState.UNDEFINED}: {pin.pin_state}')
        self.assertIsNone(
            pin.pin_priority,
            f'Pin priority is not none: {pin.pin_priority}')
        self.assertIsNone(
            pin.pin_phase_offset,
            f'Pin phase offset is not none: {pin.pin_phase_offset}')
        self.assertEqual(
            pin.pin_direction,
            PinDirection.UNDEFINED,
            f'Pin direction is not {PinDirection.UNDEFINED}: {pin.pin_direction}')

    def test_load_pin_from_dict_without_parent_device_and_all_fields_filled(self):

        device = DpllDevice(
            dev_id=0,
            dev_clock_id='13007330308713495000',
            dev_clock_quality_level='itu-opt1-eec1',
            dev_mode=DeviceMode.MANUAL,
            dev_mode_supported=[DeviceMode.AUTO, DeviceMode.MANUAL],
            dev_module_name='module1',
            dev_pad='pad-value',
            dev_type=DeviceType.EEC,
            lock_status=LockStatus.LOCKED,
            lock_status_error=LockStatusError.NONE,
        )

        pin_dict = {
            "id": 1,
            "board-label": "board-label1",
            "panel-label": "panel-label1",
            "package-label": "package-label1",
            "capabilities": ["state-can-change", "priority-can-change"],
            "clock-id": "13007330308713495000",
            "frequency": 156250000,
            "frequency-supported": [
                {
                    "frequency-max": 25000000,
                    "frequency-min": 1
                }
            ],
            "module-name": "module1",
            "parent-id": 0,
            "direction": "input",
            "phase-offset": -191040,
            "prio": 1,
            "state": "connected",
            "phase-adjust": 0,
            "phase-adjust-max": 480307,
            "phase-adjust-min": -480307,
            "type": "gnss",
        }

        pin = DpllPin.loadPin(device, pin_dict)

        # Device
        self.assert_device_fields(pin, device)

        # Pin
        self.assertEqual(
            pin.pin_id,
            pin_dict[PinFields.ID],
            f'Pin id does not match: {pin.pin_id} != {pin_dict[PinFields.ID]}')
        self.assertEqual(
            pin.pin_board_label,
            pin_dict[PinFields.BOARD_LABEL],
            f'Pin board label does not match: {pin.pin_board_label} != {pin_dict[PinFields.BOARD_LABEL]}')
        self.assertEqual(
            pin.pin_panel_label,
            pin_dict[PinFields.PANEL_LABEL],
            f'Pin panel label does not match: {pin.pin_panel_label} != {pin_dict[PinFields.PANEL_LABEL]}')
        self.assertEqual(
            pin.pin_package_label,
            pin_dict[PinFields.PACKAGE_LABEL],
            f'Pin package label does not match: {pin.pin_package_label} != {pin_dict[PinFields.PACKAGE_LABEL]}')
        self.assertEqual(
            pin.pin_type,
            PinType(pin_dict[PinFields.TYPE]),
            f'Pin type does not match: {pin.pin_type} != {PinType(pin_dict[PinFields.TYPE])}')
        self.assertEqual(
            pin.pin_state,
            PinState(pin_dict[PinFields.STATE]),
            f'Pin state does not match: {pin.pin_state} != {PinState(pin_dict[PinFields.STATE])}')
        self.assertEqual(
            pin.pin_priority,
            pin_dict[PinFields.PRIORITY],
            f'Pin priority does not match: {pin.pin_priority} != {pin_dict[PinFields.PRIORITY]}')
        self.assertEqual(
            pin.pin_phase_offset,
            pin_dict[PinFields.PHASE_OFFSET],
            f'Pin phase offset does not match: {pin.pin_phase_offset} != {pin_dict[PinFields.PHASE_OFFSET]}')
        self.assertEqual(
            pin.pin_direction,
            PinDirection(pin_dict[PinFields.DIRECTION]),
            f'Pin direction does not match: {pin.pin_direction} != {PinDirection(pin_dict[PinFields.DIRECTION])}')

    def test_load_pin_from_dict_using_only_required_fields(self):

        device = DpllDevice(
            dev_id=5,
            dev_clock_id='13007330308713495000',
        )

        pin_dict = {
            "id": 23,
            "type": "synce-eth-port",
            "parent-id": 5,
        }

        pin = DpllPin.loadPin(device, pin_dict)

        # Device
        self.assert_device_fields(pin, device)

        # Pin
        self.assertEqual(
            pin.pin_id,
            pin_dict[PinFields.ID],
            f'Pin id does not match: {pin.pin_id} != {pin_dict[PinFields.ID]}')
        self.assertIsNone(
            pin.pin_board_label,
            f'Pin board label is not none: {pin.pin_board_label}')
        self.assertIsNone(
            pin.pin_panel_label,
            f'Pin panel label is not none: {pin.pin_panel_label}')
        self.assertIsNone(
            pin.pin_package_label,
            f'Pin package label is not none: {pin.pin_package_label}')
        self.assertEqual(
            pin.pin_type,
            PinType(pin_dict[PinFields.TYPE]),
            f'Pin type does not match: {pin.pin_type} != {PinType(pin_dict[PinFields.TYPE])}')
        self.assertEqual(
            pin.pin_state, PinState.UNDEFINED,
            f'Pin state is not {PinState.UNDEFINED}: {pin.pin_state}')
        self.assertIsNone(
            pin.pin_priority,
            f'Pin priority is not none: {pin.pin_priority}')
        self.assertIsNone(
            pin.pin_phase_offset,
            f'Pin phase offset is not none: {pin.pin_phase_offset}')
        self.assertEqual(
            pin.pin_direction, PinDirection.UNDEFINED,
            f'Pin direction is not {PinDirection.UNDEFINED}: {pin.pin_direction}')

    def test_raises_exception_on_load_pin_from_dict_without_parent_device_and_parent_id(self):
        device = DpllDevice(
            dev_id=3,
            dev_clock_id='clock-id1',
            dev_clock_quality_level='itu-opt1-eec1',
            dev_mode=DeviceMode.AUTO,
            dev_mode_supported=[DeviceMode.AUTO, DeviceMode.MANUAL],
            dev_module_name='module1',
            dev_pad='pad-value',
            dev_type=DeviceType.EEC,
            lock_status=LockStatus.UNLOCKED,
            lock_status_error=LockStatusError.NONE,
        )

        pin_dict = {
            "id": 1,
            "board-label": "board-label1",
            "panel-label": "panel-label1",
            "package-label": "package-label1",
            "capabilities": ["state-can-change", "priority-can-change"],
            "clock-id": "clock-id1",
            "frequency": 0,
            "frequency-supported": [
                {
                    "frequency-max": 25000000,
                    "frequency-min": 1
                }
            ],
            "module-name": "module1",
            "phase-adjust": 0,
            "phase-adjust-max": 0,
            "phase-adjust-min": 0,
            "type": "mux",
        }

        with self.assertRaises(ValueError) as ctx:
            DpllPin.loadPin(device, pin_dict)

        self.assertIsInstance(ctx.exception, ValueError)
        self.assertEqual(f'No pin reference found for device id {device.dev_id}', str(ctx.exception))


class DpllPinsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):

        cur_path = os.path.dirname(__file__) + os.sep
        with open(cur_path + 'dump_get_pin.json', 'r', encoding='utf-8') as f_pin, \
             open(cur_path + 'dump_get_device.json', 'r', encoding='utf-8') as f_device:

            cls.dump_get_devices = json.load(f_device)
            cls.dump_get_pins = json.load(f_pin)

        cls.pins = DpllPins.loadPins(cls.dump_get_devices, cls.dump_get_pins)

    def test_load_pins_from_list_of_dicts(self):
        self.assertIsInstance(self.pins, DpllPins)
        self.assertTrue(len(self.pins) == 58,
                        f'Expected 58 devices. Got {len(self.pins)}')

    # ID
    def test_filter_pin_by_existing_id(self):
        pin_id = 27
        pin = self.pins.filter_by_pin_id(pin_id)

        self.assertIsNotNone(pin, 'Should not be none. Got {pin}')
        self.assertEqual(pin_id, pin.pin_id, f'Pin should have identifier {pin_id}')

    def test_filter_pin_by_not_existing_id(self):
        pin = self.pins.filter_by_device_id(99999)

        self.assertIsNone(pin, 'Should be none. Got {pin}')

    # Direction
    def test_filter_pins_by_existing_direction(self):
        direction = PinDirection.OUTPUT
        filtered_pins = self.pins.filter_by_pin_direction(direction)

        self.assertTrue(len(filtered_pins) == 26,
                        f'Expected 26 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertEqual(direction,
                             pin.pin_direction,
                             f'Contains invalid pin direction {pin.pin_direction}')

    def test_filter_pins_by_not_existing_direction(self):
        filtered_pins = self.pins.filter_by_pin_direction(PinDirection.UNDEFINED)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    def test_filter_pins_by_existing_directions(self):
        directions = [PinDirection.OUTPUT, PinDirection.INPUT]
        filtered_pins = self.pins.filter_by_pin_directions(directions)

        self.assertTrue(len(filtered_pins) == 58,
                        f'Expected 58 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertIn(pin.pin_direction,
                          directions,
                          f'Contains invalid pin direction {pin.pin_direction}')

    def test_filter_pins_by_not_existing_directions(self):
        invalid_directions = [PinDirection.UNDEFINED]
        filtered_pins = self.pins.filter_by_pin_direction(invalid_directions)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    # Board label
    def test_filter_pins_by_existing_board_label(self):
        board_label = 'SMA1'
        filtered_pins = self.pins.filter_by_pin_board_label(board_label)

        self.assertTrue(len(filtered_pins) == 4,
                        f'Expected 4 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertEqual(board_label,
                             pin.pin_board_label,
                             f'Contains invalid board label {pin.pin_board_label}')

    def test_filter_pins_by_not_existing_board_label(self):
        filtered_pins = self.pins.filter_by_pin_board_label('invalid-board-label')

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    def test_filter_pins_by_existing_board_labels(self):
        board_labels = ['SMA1', 'MAC-CLK']
        filtered_pins = self.pins.filter_by_pin_board_labels(board_labels)

        self.assertTrue(len(filtered_pins) == 8,
                        f'Expected 8 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertIn(pin.pin_board_label,
                          board_labels,
                          f'Contains invalid board label {pin.pin_board_label}')

    def test_filter_pins_by_not_existing_board_labels(self):
        invalid_board_labels = ['invalid-board-label1', 'invalid-board-label2']
        filtered_pins = self.pins.filter_by_pin_board_labels(invalid_board_labels)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    # Panel label
    def test_filter_pins_by_existing_panel_label(self):
        panel_label = 'PNL-SMA1'
        filtered_pins = self.pins.filter_by_pin_panel_label(panel_label)

        self.assertTrue(len(filtered_pins) == 4,
                        f'Expected 4 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertEqual(panel_label,
                             pin.pin_panel_label,
                             f'Contains invalid panel label {pin.pin_panel_label}')

    def test_filter_pins_by_not_existing_panel_label(self):
        filtered_pins = self.pins.filter_by_pin_panel_label('invalid-panel-label')

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    def test_filter_pins_by_existing_panel_labels(self):
        panel_labels = ['PNL-SMA1', 'PNL-MAC-CLK']
        filtered_pins = self.pins.filter_by_pin_panel_labels(panel_labels)

        self.assertTrue(len(filtered_pins) == 8,
                        f'Expected 8 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertIn(pin.pin_panel_label,
                          panel_labels,
                          f'Contains invalid panel label {pin.pin_panel_label}')

    def test_filter_pins_by_not_existing_panel_labels(self):
        invalid_panel_labels = ['invalid-panel-label1', 'invalid-panel-label2']
        filtered_pins = self.pins.filter_by_pin_panel_labels(invalid_panel_labels)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    # Package label
    def test_filter_pins_by_existing_package_label(self):
        package_label = 'PKG-SMA1'
        filtered_pins = self.pins.filter_by_pin_package_label(package_label)

        self.assertTrue(len(filtered_pins) == 4,
                        f'Expected 4 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertEqual(package_label,
                             pin.pin_package_label,
                             f'Contains invalid package label {pin.pin_package_label}')

    def test_filter_pins_by_not_existing_package_label(self):
        filtered_pins = self.pins.filter_by_pin_package_label('invalid-package-label')

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    def test_filter_pins_by_existing_package_labels(self):
        package_labels = ['PKG-SMA1', 'PKG-MAC-CLK']
        filtered_pins = self.pins.filter_by_pin_package_labels(package_labels)

        self.assertTrue(len(filtered_pins) == 8,
                        f'Expected 8 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertIn(pin.pin_package_label,
                          package_labels,
                          f'Contains invalid package label {pin.pin_package_label}')

    def test_filter_pins_by_not_existing_package_labels(self):
        invalid_package_labels = ['invalid-package-label1', 'invalid-package-label2']
        filtered_pins = self.pins.filter_by_pin_package_labels(invalid_package_labels)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    # Type
    def test_filter_pins_by_existing_type(self):
        pin_type = PinType.GNSS
        filtered_pins = self.pins.filter_by_pin_type(pin_type)

        self.assertTrue(len(filtered_pins) == 4,
                        f'Expected 4 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertEqual(pin_type,
                             pin.pin_type,
                             f'Contains invalid pin type {pin.pin_type}')

    def test_filter_pins_by_not_existing_type(self):
        filtered_pins = self.pins.filter_by_pin_type(PinType.UNDEFINED)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    def test_filter_pins_by_existing_types(self):
        types = [PinType.EXT, PinType.GNSS]
        filtered_pins = self.pins.filter_by_pin_types(types)

        self.assertTrue(len(filtered_pins) == 28,
                        f'Expected 28 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertIn(pin.pin_type,
                          types,
                          f'Contains invalid pin type {pin.pin_type}')

    def test_filter_pins_by_not_existing_types(self):
        invalid_types = [PinType.UNDEFINED]
        filtered_pins = self.pins.filter_by_pin_types(invalid_types)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    # State
    def test_filter_pins_by_existing_state(self):
        state = PinState.CONNECTED
        filtered_pins = self.pins.filter_by_pin_state(state)

        self.assertTrue(len(filtered_pins) == 17,
                        f'Expected 17 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertEqual(state,
                             pin.pin_state,
                             f'Contains invalid pin state {pin.pin_state}')

    def test_filter_pins_by_not_existing_state(self):
        filtered_pins = self.pins.filter_by_pin_state(PinState.UNDEFINED)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    def test_filter_pins_by_existing_states(self):
        states = [PinState.CONNECTED, PinState.SELECTABLE]
        filtered_pins = self.pins.filter_by_pin_states(states)

        self.assertTrue(len(filtered_pins) == 45,
                        f'Expected 45 pins. Got {len(filtered_pins)}')
        for pin in filtered_pins:
            self.assertIn(pin.pin_state,
                          states,
                          f'Contains invalid pin state {pin.pin_state}')

    def test_filter_pins_by_not_existing_states(self):
        invalid_states = [PinState.UNDEFINED]
        filtered_pins = self.pins.filter_by_pin_states(invalid_states)

        self.assertTrue(len(filtered_pins) == 0,
                        f'Should be empty. Got {len(filtered_pins)}')

    # Priority
    def test_order_pins_by_priority(self):
        ordered_pins = self.pins.order_by_pin_priority()

        self.assertEqual(
            len(ordered_pins),
            len(self.pins),
            f'Different sizes - Should be {len(self.pins)}. Got {len(ordered_pins)}')

        priority_ref: int = 0
        for pin in ordered_pins:
            priority = 999 if pin.pin_priority is None else pin.pin_priority

            self.assertGreaterEqual(
                priority,
                priority_ref,
                f'Out ot order: {pin.pin_priority} lower than {priority_ref}')

            priority_ref = priority

    def test_order_pins_by_reverse_priority(self):
        ordered_pins = self.pins.order_by_pin_priority(reverse=True)

        self.assertEqual(
            len(ordered_pins),
            len(self.pins),
            f'Different sizes - Should be {len(self.pins)}. Got {len(ordered_pins)}')

        priority_ref: int = 999
        for pin in ordered_pins:
            priority = 999 if pin.pin_priority is None else pin.pin_priority

            self.assertLessEqual(
                priority,
                priority_ref,
                f'Out ot order: {pin.pin_priority} greater than {priority_ref}')

            priority_ref = priority
