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

        pin_pict_idx = random.randint(0, 8)
        pin_dict = self.dump_get_pins[pin_pict_idx]
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
