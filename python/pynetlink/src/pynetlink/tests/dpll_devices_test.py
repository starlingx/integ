#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module tests the DpllDevice and DpllDevices classes"""

import json
import os
from unittest import TestCase
from ..dpll import DpllDevices
from ..dpll import DpllDevice
from ..dpll import DeviceFields
from ..dpll import DeviceType
from ..dpll import DeviceMode
from ..dpll import LockStatus
from ..dpll import LockStatusError


class DpllDeviceTestCase(TestCase):

    def test_create_new_device_instance_using_all_fields(self):

        dev_id = 1
        dev_clock_id = 111111122222222
        dev_clock_quality_level = 'itu-opt1-prc'
        dev_mode = DeviceMode.AUTO
        dev_mode_supported = [DeviceMode.AUTO]
        dev_module_name = 'module'
        dev_pad = 'pad'
        dev_type = DeviceType.PPS
        lock_status = LockStatus.UNLOCKED
        lock_status_error = LockStatusError.FFO_TOO_HIGH

        device = DpllDevice(
            dev_id=dev_id,
            dev_clock_id=dev_clock_id,
            dev_clock_quality_level=dev_clock_quality_level,
            dev_mode=dev_mode,
            dev_mode_supported=dev_mode_supported,
            dev_module_name=dev_module_name,
            dev_pad=dev_pad,
            dev_type=dev_type,
            lock_status=lock_status,
            lock_status_error=lock_status_error,
        )

        self.assertEqual(
            device.dev_id,
            dev_id,
            f'Device id does not match: {device.dev_id} != {dev_id}')
        self.assertEqual(
            device.dev_clock_id,
            dev_clock_id,
            f'Device clock id does not match: {device.dev_clock_id} != {dev_clock_id}')
        self.assertEqual(
            device.dev_clock_quality_level,
            dev_clock_quality_level,
            f'Device clock quality level does not match: {device.dev_clock_quality_level} != {dev_clock_quality_level}')
        self.assertEqual(
            device.dev_mode,
            dev_mode,
            f'Device mode does not match: {device.dev_mode} != {dev_mode}')
        self.assertListEqual(
            device.dev_mode_supported,
            dev_mode_supported,
            f'Device mode supported does not match: {device.dev_mode_supported} != {dev_mode_supported}')
        self.assertEqual(
            device.dev_module_name,
            dev_module_name,
            f'Device module name does not match: {device.dev_module_name} != {dev_module_name}')
        self.assertEqual(
            device.dev_pad,
            dev_pad,
            f'Device pad does not match: {device.dev_pad} != {dev_pad}')
        self.assertEqual(
            device.dev_type,
            dev_type,
            f'Device type does not match: {device.dev_type} != {dev_type}')
        self.assertEqual(
            device.lock_status,
            lock_status,
            f'Device lock status does not match: {device.lock_status} != {lock_status}')
        self.assertEqual(
            device.lock_status_error,
            lock_status_error,
            f'Device lock status error does not match: {device.lock_status_error} != {lock_status_error}')

    def test_create_new_device_instance_using_only_required_fields(self):

        dev_id = 199
        dev_clock_id = 9999999999999999999999999999

        device = DpllDevice(dev_id=dev_id, dev_clock_id=dev_clock_id)

        self.assertEqual(
            device.dev_id,
            dev_id,
            f'Device id does not match: {device.dev_id} != {dev_id}')
        self.assertEqual(
            device.dev_clock_id,
            dev_clock_id,
            f'Device clock id does not match: {device.dev_clock_id} != {dev_clock_id}')
        self.assertIsNone(
            device.dev_clock_quality_level,
            f'Device clock quality level is not none: {device.dev_clock_quality_level}')
        self.assertEqual(
            device.dev_mode,
            DeviceMode.UNDEFINED,
            f'Device mode is not {DeviceMode.UNDEFINED}: {device.dev_mode}')
        self.assertListEqual(
            device.dev_mode_supported,
            list(),
            f'Device mode supported is not empty: {device.dev_mode_supported}')
        self.assertIsNone(
            device.dev_module_name,
            f'Device module name is not none: {device.dev_module_name}')
        self.assertIsNone(
            device.dev_pad,
            f'Device pad is not none: {device.dev_pad}')
        self.assertEqual(
            device.dev_type,
            DeviceType.UNDEFINED,
            f'Device type is not {DeviceType.UNDEFINED}: {device.dev_pad}')
        self.assertEqual(
            device.lock_status,
            LockStatus.UNDEFINED,
            f'Device lock status is not {LockStatus.UNDEFINED}: {device.dev_pad}')
        self.assertEqual(
            device.lock_status_error,
            LockStatusError.UNDEFINED,
            f'Device lock status error is not {LockStatusError.UNDEFINED}: {device.lock_status_error}')

    def test_load_device_raises_exception_when_device_is_none(self):

        with self.assertRaises(ValueError) as ctx:
            DpllDevice.loadDevice(None)

        self.assertIsInstance(ctx.exception, ValueError)
        self.assertEqual('Device parameter must be informed.', str(ctx.exception))

    def test_load_device_from_dict_with_all_fields_filled(self):

        device_dict = {
            "id": 1,
            "clock-id": 13007330308713495000,
            "clock-quality-level": "itu-opt1-eec1",
            "mode": "automatic",
            "mode-supported": ["automatic", "manual"],
            "module-name": "module1",
            "pad": "pad-value",
            "type": "eec",
            "lock-status": "unlocked",
            "lock-status-error": "none",
        }

        device = DpllDevice.loadDevice(device_dict)

        self.assertEqual(
            device.dev_id,
            device_dict[DeviceFields.ID],
            f'Device id does not match: {device.dev_id} != {device_dict[DeviceFields.ID]}')
        self.assertEqual(
            device.dev_clock_id,
            device_dict[DeviceFields.CLOCK_ID],
            f'Device clock id does not match: {device.dev_clock_id} != {device_dict[DeviceFields.CLOCK_ID]}')
        self.assertEqual(
            device.dev_clock_quality_level,
            device_dict[DeviceFields.CLOCK_QUALITY],
            f'Device clock quality level does not match: {device.dev_clock_quality_level} != \
                                                         {device_dict[DeviceFields.CLOCK_QUALITY]}')
        self.assertEqual(
            device.dev_mode,
            DeviceMode(device_dict[DeviceFields.MODE]),
            f'Device mode does not match: {device.dev_mode} != {device_dict[DeviceFields.MODE]}')
        self.assertListEqual(
            device.dev_mode_supported,
            [DeviceMode(x) for x in device_dict[DeviceFields.MODE_SUPPORTED]],
            f'Device mode supported does not match: {device.dev_mode_supported} != \
                                                    {device_dict[DeviceFields.MODE_SUPPORTED]}')
        self.assertEqual(
            device.dev_module_name,
            device_dict[DeviceFields.MODULE_NAME],
            f'Device module name does not match: {device.dev_module_name} != {device_dict[DeviceFields.MODULE_NAME]}')
        self.assertEqual(
            device.dev_pad,
            device_dict[DeviceFields.PAD],
            f'Device pad does not match: {device.dev_pad} != {device_dict[DeviceFields.PAD]}')
        self.assertEqual(
            device.dev_type,
            DeviceType(device_dict[DeviceFields.TYPE]),
            f'Device type does not match: {device.dev_type} != {device_dict[DeviceFields.TYPE]}')
        self.assertEqual(
            device.lock_status,
            LockStatus(device_dict[DeviceFields.LOCK_STATUS]),
            f'Device lock status does not match: {device.lock_status} != {device_dict[DeviceFields.LOCK_STATUS]}')
        self.assertEqual(
            device.lock_status_error,
            LockStatusError(device_dict[DeviceFields.LOCK_STATUS_ERROR]),
            f'Device lock status error does not match: {device.lock_status_error} != \
                                                       {device_dict[DeviceFields.LOCK_STATUS_ERROR]}')

    def test_load_device_from_dict_with_only_required_fields(self):

        device_dict = {
            "id": 2,
            "clock-id": 12345678901234567889,
        }

        device = DpllDevice.loadDevice(device_dict)

        self.assertEqual(
            device.dev_id,
            device_dict[DeviceFields.ID],
            f'Device id does not match: {device.dev_id} != {device_dict[DeviceFields.ID]}')
        self.assertEqual(
            device.dev_clock_id,
            device_dict[DeviceFields.CLOCK_ID],
            f'Device clock id does not match: {device.dev_clock_id} != {device_dict[DeviceFields.CLOCK_ID]}')
        self.assertIsNone(
            device.dev_clock_quality_level,
            f'Device clock quality level is not none: {device.dev_clock_quality_level}')
        self.assertEqual(
            device.dev_mode,
            DeviceMode.UNDEFINED,
            f'Device mode is not {DeviceMode.UNDEFINED}: {device.dev_mode}')
        self.assertListEqual(
            device.dev_mode_supported,
            list(),
            f'Device mode supported is not empty: {device.dev_mode_supported}')
        self.assertIsNone(
            device.dev_module_name,
            f'Device module name is not none: {device.dev_module_name}')
        self.assertIsNone(
            device.dev_pad,
            f'Device pad is not none: {device.dev_pad}')
        self.assertEqual(
            device.dev_type,
            DeviceType.UNDEFINED,
            f'Device type is not {DeviceType.UNDEFINED}: {device.dev_pad}')
        self.assertEqual(
            device.lock_status,
            LockStatus.UNDEFINED,
            f'Device lock status is not {LockStatus.UNDEFINED}: {device.dev_pad}')
        self.assertEqual(
            device.lock_status_error,
            LockStatusError.UNDEFINED,
            f'Device lock status error is not {LockStatusError.UNDEFINED}: {device.lock_status_error}')


class DpllDevicesTestCase(TestCase):

    @classmethod
    def setUpClass(cls):

        device_json = os.path.dirname(__file__) + os.sep + 'dump_get_device.json'
        with open(device_json, 'r', encoding='utf-8') as f_device:
            cls.dump_get_devices = json.load(f_device)

        cls.devices = DpllDevices.loadDevices(cls.dump_get_devices)

    def test_load_devices_from_list_of_dicts(self):
        self.assertIsInstance(self.devices, DpllDevices)
        self.assertEqual(4, len(self.devices),
                         f'Expected 4 devices. Got {len(self.devices)}')

    # ID
    def test_filter_device_by_existing_id(self):
        dev_id = 1
        device = self.devices.filter_by_device_id(dev_id)

        self.assertEqual(dev_id, device.dev_id, f'Device should have identifier {dev_id}')

    def test_filter_device_by_not_existing_id(self):
        device = self.devices.filter_by_device_id(99999)

        self.assertIsNone(device, 'Should be none. Got {device}')

    # Clock id
    def test_filter_device_by_existing_clock_id(self):
        clock_id = 13007330308713495000
        filtered_devices = self.devices.filter_by_device_clock_id(clock_id)

        self.assertTrue(len(filtered_devices) == 2,
                        f'Expected 2 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertEqual(clock_id, device.dev_clock_id,
                             f'Should have clock identifier {clock_id}')

    def test_filter_device_by_not_existing_clock_id(self):
        filtered_devices = self.devices.filter_by_device_clock_id(0)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    def test_filter_device_by_existing_clock_ids(self):
        clock_ids = [13007330308713495000, 5799633565437375000]
        filtered_devices = self.devices.filter_by_device_clock_ids(clock_ids)

        self.assertTrue(len(filtered_devices) == 4,
                        f'Expected 4 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertIn(device.dev_clock_id, clock_ids,
                          f'Contains invalid clock identifier {device.dev_clock_id}')

    def test_filter_device_by_not_existing_clock_ids(self):
        invalid_clock_ids = [0, 9999999999999999999999]
        filtered_devices = self.devices.filter_by_device_clock_ids(invalid_clock_ids)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    # Type
    def test_filter_device_by_existing_type(self):
        dev_type = DeviceType.EEC
        filtered_devices = self.devices.filter_by_device_type(dev_type)

        self.assertTrue(len(filtered_devices) == 2,
                        f'Expected 2 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertEqual(dev_type, device.dev_type,
                             f'Should have lock status {type}')

    def test_filter_device_by_not_existing_type(self):
        filtered_devices = self.devices.filter_by_device_type(DeviceType.UNDEFINED)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    def test_filter_device_by_existing_types(self):
        types = [DeviceType.EEC, DeviceType.PPS]
        filtered_devices = self.devices.filter_by_device_types(types)

        self.assertTrue(len(filtered_devices) == 4,
                        f'Expected 4 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertIn(device.dev_type, types,
                          f'Contains invalid lock status {device.dev_type}')

    def test_filter_device_by_not_existing_types(self):
        invalid_types = [DeviceType.UNDEFINED]
        filtered_devices = self.devices.filter_by_device_types(invalid_types)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    # Mode
    def test_filter_device_by_existing_mode(self):
        mode = DeviceMode.AUTO
        filtered_devices = self.devices.filter_by_device_mode(mode)

        self.assertTrue(len(filtered_devices) == 4,
                        f'Expected 4 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertEqual(mode, device.dev_mode,
                             f'Should have mode {mode}')

    def test_filter_device_by_not_existing_mode(self):
        filtered_devices = self.devices.filter_by_device_mode(DeviceMode.MANUAL)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    # Supported Mode
    def test_filter_device_by_existing_mode_supported(self):
        mode = DeviceMode.MANUAL
        filtered_devices = self.devices.filter_by_device_mode_supported(mode)

        self.assertTrue(len(filtered_devices) == 2,
                        f'Expected 2 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertIn(mode, device.dev_mode_supported,
                          f'Should have mode {mode}')

    def test_filter_device_by_not_existing_mode_supported(self):
        filtered_devices = self.devices.filter_by_device_mode_supported(DeviceMode.UNDEFINED)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    # Lock status
    def test_filter_device_by_existing_lock_status(self):
        status = LockStatus.LOCKED_AND_HOLDOVER
        filtered_devices = self.devices.filter_by_device_lock_status(status)

        self.assertTrue(len(filtered_devices) == 2,
                        f'Expected 2 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertEqual(status, device.lock_status,
                             f'Should have lock status {status}')

    def test_filter_device_by_not_existing_lock_status(self):
        filtered_devices = self.devices.filter_by_device_lock_status(LockStatus.HOLDOVER)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    def test_filter_device_by_existing_lock_statuses(self):
        statuses = [LockStatus.LOCKED_AND_HOLDOVER, LockStatus.UNLOCKED]
        filtered_devices = self.devices.filter_by_device_lock_statuses(statuses)

        self.assertTrue(len(filtered_devices) == 4,
                        f'Expected 4 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertIn(device.lock_status, statuses,
                          f'Contains invalid lock status {device.lock_status}')

    def test_filter_device_by_not_existing_lock_statuses(self):
        invalid_statuses = [LockStatus.HOLDOVER, LockStatus.LOCKED]
        filtered_devices = self.devices.filter_by_device_lock_statuses(invalid_statuses)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    # Lock status error
    def test_filter_device_by_existing_lock_status_error(self):
        status = LockStatusError.NONE
        filtered_devices = self.devices.filter_by_device_lock_status_error(status)

        self.assertTrue(len(filtered_devices) == 2,
                        f'Expected 2 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertEqual(status, device.lock_status_error,
                             f'Should have lock status error {status}')

    def test_filter_device_by_not_existing_lock_status_error(self):
        status = LockStatusError.MEDIA_DOWN
        filtered_devices = self.devices.filter_by_device_lock_status_error(status)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')

    def test_filter_device_by_existing_lock_status_errors(self):
        statuses = [LockStatusError.NONE, LockStatusError.UNDEFINED]
        filtered_devices = self.devices.filter_by_device_lock_status_errors(statuses)

        self.assertTrue(len(filtered_devices) == 4,
                        f'Expected 4 devices. Got {len(filtered_devices)}')
        for device in filtered_devices:
            self.assertIn(device.lock_status_error, statuses,
                          f'Contains invalid lock status error {device.lock_status_error}')

    def test_filter_device_by_not_existing_lock_status_errors(self):
        invalid_statuses = [LockStatusError.MEDIA_DOWN, LockStatusError.FFO_TOO_HIGH]
        filtered_devices = self.devices.filter_by_device_lock_statuses(invalid_statuses)

        self.assertTrue(len(filtered_devices) == 0,
                        f'Should be empty. Got {len(filtered_devices)}')
