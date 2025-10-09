#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module tests the NetlinkDPLL class"""

import json
import os
import random
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch
from ..base import YnlFamily
from ..dpll import NetlinkDPLL
from ..dpll import DPLLCommands
from ..dpll import DpllDevices
from ..dpll import DpllDevice
from ..dpll import DeviceFields
from ..dpll import DpllPins
from ..dpll import PinFields
from ..dpll import PinParentFields


class NetlinkDPLLTestCase(TestCase):

    @classmethod
    def setUpClass(cls):

        cur_path = os.path.dirname(__file__) + os.sep
        with open(cur_path + 'dump_get_pin.json', 'r', encoding='utf-8') as f_pin,\
             open(cur_path + 'dump_get_device.json', 'r', encoding='utf-8') as f_device:

            cls.dump_get_pins = json.load(f_pin)
            cls.dump_get_devices = json.load(f_device)

    def test_get_shared_dpll_instance(self):
        dpll_shared1 = NetlinkDPLL()
        dpll_shared2 = NetlinkDPLL()
        self.assertIs(dpll_shared1._ynl,    # pylint: disable=W0212
                      dpll_shared2._ynl,    # pylint: disable=W0212
                      'DPLL instances share the same YNL instance')

    def test_get_dedicated_dpll_instance(self):

        dpll_dedicated1 = NetlinkDPLL(True)
        dpll_dedicated2 = NetlinkDPLL(True)

        self.assertIsNot(dpll_dedicated1._ynl,  # pylint: disable=W0212
                         dpll_dedicated2._ynl,  # pylint: disable=W0212
                         'DPLL instances use dedicated YNL instances')

        self.assertIsNot(NetlinkDPLL._ynl,      # pylint: disable=W0212
                         dpll_dedicated1._ynl,  # pylint: disable=W0212
                         'DPLL shared and dedicated instances use different YNL instances')

    @patch.object(YnlFamily, 'dump')
    def test_list_all_clock_devices_available_in_raw_format(self, mock_ynl_dump: Mock):

        mock_ynl_dump.return_value = self.dump_get_devices

        dpll = NetlinkDPLL()
        devices_dict = dpll._get_all_devices()  # pylint: disable=W0212

        self.assertEqual(devices_dict,
                         self.dump_get_devices,
                         'List of devices should be identical')

        mock_ynl_dump.assert_called_once_with(DPLLCommands.DEVICE_GET, {})

    @patch.object(YnlFamily, 'dump')
    def test_list_all_devices_available(self, mock_ynl_dump: Mock):

        expected_device_ids = list(map(lambda dev: dev[DeviceFields.ID], self.dump_get_devices))

        mock_ynl_dump.return_value = self.dump_get_devices

        dpll = NetlinkDPLL()
        devices = dpll.get_all_devices()

        self.assertIsInstance(devices,
                              DpllDevices,
                              f'Should return DpllDevices instance - Got {type(devices)}')

        self.assertEqual(len(devices),
                         len(self.dump_get_devices),
                         f'#items: Should be {len(self.dump_get_devices)} Got {len(devices)}')

        for device in devices:
            self.assertIn(device.dev_id,
                          expected_device_ids,
                          f'Contains wrong device: {device.dev_id}')

        mock_ynl_dump.assert_called_once_with(DPLLCommands.DEVICE_GET, {})

    @patch.object(YnlFamily, 'do')
    def test_get_device_with_specific_id_in_raw_format(self, mock_ynl_do: Mock):

        dev_id = random.randint(0, len(self.dump_get_devices) - 1)
        expected_result = self.dump_get_devices[dev_id]

        mock_ynl_do.return_value = expected_result

        dpll = NetlinkDPLL()
        device_dict = dpll._get_device_by_id(dev_id)    # pylint: disable=W0212

        self.assertEqual(device_dict,
                         expected_result,
                         f'Wrong device ID: Expected {dev_id}. Got {device_dict[DeviceFields.ID]}')

        mock_ynl_do.assert_called_once_with(DPLLCommands.DEVICE_GET, {DeviceFields.ID: dev_id})

    @patch.object(YnlFamily, 'do')
    def test_get_device_with_specific_id(self, mock_ynl_do: Mock):

        dev_id = random.randint(0, len(self.dump_get_devices) - 1)
        expected_result = self.dump_get_devices[dev_id]

        mock_ynl_do.return_value = expected_result

        dpll = NetlinkDPLL()
        device = dpll.get_device_by_id(dev_id)

        self.assertIsInstance(device,
                              DpllDevice,
                              f'Should return DpllDevices instance - Got {type(device)}')

        self.assertEqual(device.dev_id,
                         dev_id,
                         f'Wrong device ID: Expected {dev_id}. Got {device.dev_id}')

        mock_ynl_do.assert_called_once_with(DPLLCommands.DEVICE_GET, {DeviceFields.ID: dev_id})

    @patch.object(YnlFamily, 'dump')
    def test_get_clock_device_using_clock_id(self, mock_ynl_dump: Mock):

        clock_id = 5799633565437375000
        expected_device_ids = list(
            map(lambda dev: dev[DeviceFields.ID],
                filter(lambda item: item[DeviceFields.CLOCK_ID] == clock_id,
                       self.dump_get_devices)))

        mock_ynl_dump.return_value = self.dump_get_devices

        dpll = NetlinkDPLL()
        devices = dpll.get_devices_by_clock_id(clock_id)

        self.assertIsInstance(devices,
                              DpllDevices,
                              f'Should return DpllDevices instance - Got {type(devices)}')

        self.assertEqual(len(devices),
                         len(expected_device_ids),
                         f'#items: Should be {len(expected_device_ids)} Got {len(devices)}')

        for device in devices:
            self.assertEqual(device.dev_clock_id,
                             clock_id,
                             f"Wrong clock ID: Expected {clock_id}. Got {device.dev_clock_id}")
            self.assertIn(device.dev_id,
                          expected_device_ids,
                          f'Contains wrong device: {device.dev_id}')

        mock_ynl_dump.assert_called_once_with(DPLLCommands.DEVICE_GET, {})

    @patch.object(YnlFamily, 'dump')
    def test_returns_empty_DpllDevices_when_device_clock_id_is_not_found(self, mock_ynl_dump: Mock):

        clock_id = 0
        mock_ynl_dump.return_value = self.dump_get_devices

        dpll = NetlinkDPLL()
        devices = dpll.get_devices_by_clock_id(clock_id)

        self.assertIsInstance(devices,
                              DpllDevices,
                              f'Should return DpllDevices instance. Got {type(devices)}')

        self.assertTrue(len(devices) == 0, f'Should have no device. Got {len(devices)}')

        mock_ynl_dump.assert_called_once_with(DPLLCommands.DEVICE_GET, {})

    @patch.object(YnlFamily, 'dump')
    def test_list_all_pins_available_in_raw_format(self, mock_ynl_dump: Mock):

        mock_ynl_dump.return_value = self.dump_get_pins

        dpll = NetlinkDPLL()
        pins_dict = dpll._get_all_pins()    # pylint: disable=W0212

        self.assertListEqual(pins_dict,
                             self.dump_get_pins,
                             'List of pins should be identical')

        mock_ynl_dump.assert_called_once_with(DPLLCommands.PIN_GET, {})

    @patch.object(YnlFamily, 'dump')
    def test_list_all_pins_available(self, mock_ynl_dump: Mock):

        expected_pin_ids = list(
            map(lambda pin: pin[PinFields.ID],
                filter(lambda item: PinFields.PARENT_PIN not in item,
                       self.dump_get_pins)))

        mock_ynl_dump.side_effect = [self.dump_get_devices, self.dump_get_pins]

        dpll = NetlinkDPLL()
        pins = dpll.get_all_pins()

        self.assertIsInstance(pins,
                              DpllPins,
                              f'Should return DpllPins instance. Got {type(pins)}')

        for pin in pins:
            self.assertIn(pin.pin_id,
                          expected_pin_ids,
                          f'Contains wrong pin: {pin.pin_id}')

        mock_ynl_dump.assert_has_calls([
            call(DPLLCommands.DEVICE_GET, {}),
            call(DPLLCommands.PIN_GET, {})
        ])

    @patch.object(YnlFamily, 'do')
    def test_get_pin_with_specific_id_in_raw_format(self, mock_ynl_do: Mock):

        pin_id = random.randint(0, len(self.dump_get_pins) - 1)
        expected_pin = self.dump_get_pins[pin_id]

        mock_ynl_do.return_value = expected_pin

        dpll = NetlinkDPLL()
        pin_dict = dpll._get_pin_by_id(pin_id)  # pylint: disable=W0212

        self.assertEqual(pin_dict,
                         expected_pin,
                         f'Wrong pin ID: Expected {pin_id}. Got {pin_dict[PinFields.ID]}')

        mock_ynl_do.assert_called_once_with(DPLLCommands.PIN_GET, {PinFields.ID: pin_id})

    @patch.object(YnlFamily, 'do')
    @patch.object(YnlFamily, 'dump')
    def test_get_pins_with_specific_id(self, mock_ynl_dump: Mock, mock_ynl_do: Mock):

        pin_dict_idx = random.randint(0, 8)
        pin_dict = self.dump_get_pins[pin_dict_idx]
        pin_id = pin_dict[PinFields.ID]

        mock_ynl_dump.return_value = self.dump_get_devices
        mock_ynl_do.return_value = pin_dict

        dpll = NetlinkDPLL()
        pins = dpll.get_pins_by_id(pin_id)

        self.assertIsInstance(pins,
                              DpllPins,
                              f'Should return DpllPins instance. Got {type(pins)}')

        for pin in pins:
            self.assertEqual(pin.pin_id,
                             pin_id,
                             f'Wrong pin ID: Expected {pin_id}. Got {pin.pin_id}')

        mock_ynl_dump.assert_called_once_with(DPLLCommands.DEVICE_GET, {})
        mock_ynl_do.assert_called_once_with(DPLLCommands.PIN_GET, {PinFields.ID: pin_id})

    @patch.object(YnlFamily, 'dump')
    def test_get_pins_from_clock_id(self, mock_ynl_dump: Mock):

        clock_id: int = 5799633565437375000
        expected_pin_ids = list(
            map(lambda pin: pin[PinFields.ID],
                filter(lambda item: item[PinFields.CLOCK_ID] == clock_id,
                       self.dump_get_pins)))

        mock_ynl_dump.side_effect = [self.dump_get_devices, self.dump_get_pins]

        dpll = NetlinkDPLL()
        pins = dpll.get_pins_by_clock_id(clock_id)

        self.assertIsInstance(pins,
                              DpllPins,
                              f'Should return DpllPins instance. Got {type(pins)}')

        for pin in pins:
            self.assertEqual(pin.dev_clock_id,
                             clock_id,
                             f"Wrong clock ID: Expected {clock_id}. Got {pin.dev_clock_id}")
            self.assertIn(pin.pin_id,
                          expected_pin_ids,
                          f'Contains wrong pin: {pin.pin_id}')

        mock_ynl_dump.assert_has_calls([
            call(DPLLCommands.DEVICE_GET, {}),
            call(DPLLCommands.PIN_GET, {})
        ])

    @patch.object(YnlFamily, 'dump')
    def test_returns_empty_DpllPins_when_device_clock_id_is_not_found(self, mock_ynl_dump: Mock):

        clock_id: int = 0
        mock_ynl_dump.side_effect = [self.dump_get_devices, self.dump_get_pins]

        dpll = NetlinkDPLL()
        pins = dpll.get_pins_by_clock_id(clock_id)

        self.assertIsInstance(pins,
                              DpllPins,
                              f'Should return DpllPins instance. Got {type(pins)}')

        self.assertTrue(len(pins) == 0, f'Should have no pin. Got {len(pins)}')

        mock_ynl_dump.assert_has_calls([
            call(DPLLCommands.DEVICE_GET, {}),
            call(DPLLCommands.PIN_GET, {})
        ])

    @patch.object(YnlFamily, 'do')
    def test_set_pin(self, mock_ynl_do: Mock):

        expected_result = None
        mock_ynl_do.return_value = expected_result
        pin_info = {
            'id': 34,
            'parent-device': [
                {
                    'parent-id': 2,
                    'direction': 1,
                    'priority': 2
                },
                {
                    'parent-id': 3,
                    'direction': 1,
                    'priority': 2
                }
            ]
        }

        dpll = NetlinkDPLL()
        result = dpll._set_pin(pin_info)    # pylint: disable=W0212

        self.assertEqual(expected_result,
                         result,
                         f'Wrong _set_pin result: '
                         f'Expected {expected_result}. Got {result}')

        mock_ynl_do.assert_called_once_with(DPLLCommands.PIN_SET, pin_info)

    @patch.object(YnlFamily, 'do')
    @patch.object(YnlFamily, 'dump')
    def test_set_pin_direction(self, mock_ynl_dump: Mock, mock_ynl_do: Mock):

        pin_dict_idx = random.randint(0, 8)
        pin_dict = self.dump_get_pins[pin_dict_idx]
        pin_id = pin_dict[PinFields.ID]
        pin_direction = random.randint(0, 2)
        parent_ids = list(parent[PinParentFields.PARENT_ID]
                          for parent in pin_dict[PinFields.PARENT_DEVICE])
        expected_result = None

        mock_ynl_dump.return_value = self.dump_get_devices
        mock_ynl_do.side_effect = [pin_dict, None]

        dpll = NetlinkDPLL()
        result = dpll.set_pin_direction(pin_id, pin_direction)

        self.assertEqual(expected_result,
                         result,
                         f'Wrong _set_pin result: '
                         f'Expected {expected_result}. Got {result}')

        mock_ynl_dump.assert_called_once_with(DPLLCommands.DEVICE_GET, {})

        # Verify the do pin-set command call.
        args, _ = mock_ynl_do.call_args
        call_command = args[0]
        self.assertEqual(DPLLCommands.PIN_SET,
                         call_command,
                         f'Wrong do command: '
                         f'Expected {DPLLCommands.PIN_SET}. Got {call_command}')

        call_args = args[1]
        sorted_call_args = {
            PinFields.ID: call_args[PinFields.ID],
            PinFields.PARENT_DEVICE: sorted(
                call_args[PinFields.PARENT_DEVICE],
                key=lambda x: x[PinParentFields.PARENT_ID]
            )
        }
        expected_call_args = {
            PinFields.ID: pin_id,
            PinFields.PARENT_DEVICE: list(
                {
                    PinParentFields.PARENT_ID: id,
                    PinParentFields.DIRECTION: pin_direction
                }
                for id in sorted(parent_ids)
            )
        }
        self.assertDictEqual(sorted_call_args,
                             expected_call_args,
                             f'Wrong call arguments: '
                             f'Expected {expected_call_args}. Got {sorted_call_args}')

    @patch.object(YnlFamily, 'do')
    @patch.object(YnlFamily, 'dump')
    def test_set_pin_priority(self, mock_ynl_dump: Mock, mock_ynl_do: Mock):

        pin_dict_idx = random.randint(0, 8)
        pin_dict = self.dump_get_pins[pin_dict_idx]
        pin_id = pin_dict[PinFields.ID]
        pin_priority = random.randint(0, 7)
        pin_info = {
            PinFields.ID: pin_id,
            PinFields.PARENT_DEVICE: []
        }
        parent_ids = list(parent[PinParentFields.PARENT_ID]
                          for parent in pin_dict[PinFields.PARENT_DEVICE])
        for parent_id in parent_ids:
            pin_info[PinFields.PARENT_DEVICE].append(
                {
                    PinParentFields.PARENT_ID: parent_id,
                    PinParentFields.PRIORITY: pin_priority
                }
            )
        expected_result = None

        mock_ynl_dump.return_value = self.dump_get_devices
        mock_ynl_do.side_effect = [pin_dict, None]

        dpll = NetlinkDPLL()
        result = dpll.set_pin_priority(pin_id, pin_priority)

        self.assertEqual(expected_result,
                         result,
                         f'Wrong _set_pin result: '
                         f'Expected {expected_result}. Got {result}')

        mock_ynl_dump.assert_called_once_with(DPLLCommands.DEVICE_GET, {})

        # Verify the do pin-set command call.
        args, _ = mock_ynl_do.call_args
        call_command = args[0]
        # Verify the command is pin-set
        self.assertEqual(DPLLCommands.PIN_SET,
                         call_command,
                         f'Wrong do command: '
                         f'Expected {DPLLCommands.PIN_SET}. Got {call_command}')
        # Verify the pin id
        call_args = args[1]
        sorted_call_args = {
            PinFields.ID: call_args[PinFields.ID],
            PinFields.PARENT_DEVICE: sorted(
                call_args[PinFields.PARENT_DEVICE],
                key=lambda x: x[PinParentFields.PARENT_ID]
            )
        }
        expected_call_args = {
            PinFields.ID: pin_id,
            PinFields.PARENT_DEVICE: list(
                {
                    PinParentFields.PARENT_ID: id,
                    PinParentFields.PRIORITY: pin_priority
                }
                for id in sorted(parent_ids)
            )
        }
        self.assertDictEqual(sorted_call_args,
                             expected_call_args,
                             f'Wrong call arguments: '
                             f'Expected {expected_call_args}. Got {sorted_call_args}')
