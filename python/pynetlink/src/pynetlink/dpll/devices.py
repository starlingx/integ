#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module contains classes related to DPLL devices."""

from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Union
from .constants import DeviceFields
from .constants import DeviceMode
from .constants import DeviceType
from .constants import LockStatus
from .constants import LockStatusError


@dataclass(frozen=True)
class DpllDevice:

    dev_id: int
    dev_clock_id: int = field(hash=False)
    dev_clock_quality_level: str = field(hash=False, default=None)
    dev_mode: DeviceMode = field(hash=False, default=DeviceMode.UNDEFINED)
    dev_mode_supported: list[DeviceMode] = field(hash=False, default_factory=list)
    dev_module_name: str = field(hash=False, default=None)
    dev_pad: str = field(hash=False, default=None)
    dev_type: DeviceType = field(hash=False, default=DeviceType.UNDEFINED)
    lock_status: LockStatus = field(hash=False, default=LockStatus.UNDEFINED)
    lock_status_error: LockStatusError = field(hash=False, default=LockStatusError.UNDEFINED)

    @classmethod
    def loadDevice(cls, device: dict) -> DpllDevice:
        """Parse DPLL device data returned from Netlink and creates a DPLLDevice class.

        The fields not specified in the list will be set to a default value.

        device: DPLL device data in raw format.
        """

        if device is None:
            raise ValueError('Device parameter must be informed.')

        return cls(
            dev_id=int(device[DeviceFields.ID]),
            dev_clock_id=int(device[DeviceFields.CLOCK_ID]),
            dev_clock_quality_level=device.get(DeviceFields.CLOCK_QUALITY),
            dev_mode=DeviceMode(device.get(DeviceFields.MODE, DeviceMode.UNDEFINED)),
            dev_mode_supported=[DeviceMode(x) for x in device.get(DeviceFields.MODE_SUPPORTED, DeviceMode.UNDEFINED)]
            if DeviceFields.MODE_SUPPORTED in device else list(),
            dev_module_name=str(device[DeviceFields.MODULE_NAME])
            if DeviceFields.MODULE_NAME in device else None,
            dev_pad=str(device[DeviceFields.PAD]) if DeviceFields.PAD in device else None,
            dev_type=DeviceType(device.get(DeviceFields.TYPE, DeviceType.UNDEFINED)),
            lock_status=LockStatus(device.get(DeviceFields.LOCK_STATUS, LockStatus.UNDEFINED)),
            lock_status_error=LockStatusError(
                device.get(DeviceFields.LOCK_STATUS_ERROR, LockStatusError.UNDEFINED)),
        )


class DpllDevices(set):

    @classmethod
    def loadDevices(cls, devices: list[dict]) -> DpllDevices:
        """Parses a list of DPLL devices returned from Netlink and creates the DPLLDevices class.

        The fields not specified will be set to the default value.

        devices: list of DPLL devices in raw format.
        """

        instance = cls()

        for device in devices:
            instance.add(DpllDevice.loadDevice(device))

        return instance

    def filter_by_device_clock_id(self, clock_id: int) -> DpllDevices:
        """Returns a new instance containing only items with the given clock id.

        clock_id: clock identifier to be filtered.
        """

        return self.__class__(filter(lambda x: x.dev_clock_id == clock_id, self))

    def filter_by_device_clock_ids(self, clock_ids: list[int]) -> DpllDevices:
        """Returns a new instance containing only items with the given clocks.

        clock_ids: list of the clock identifier to be filtered.
        """

        return self.__class__(filter(lambda x: x.dev_clock_id in clock_ids, self))

    def filter_by_device_id(self, device_id: int) -> Union[DpllDevice, None]:
        """Searches for the device identifier and returns a DpllPin instance.

        If not found, returns None.

        device_id: device id to be searched
        """

        return next((filter(lambda x: x.dev_id == device_id, self)), None)

    def filter_by_device_type(self, device_type: DeviceType) -> DpllDevices:
        """Returns a new instance containing only items with the given device type.

        device_type: device type enumeration to be filtered.
        """

        return self.__class__(filter(lambda x: x.dev_type == device_type, self))

    def filter_by_device_types(self, device_types: list[DeviceType]) -> DpllDevices:
        """Returns a new instance containing only items with the given devices types.

        device_types: list with the device type enumerations to be filtered.
        """

        return self.__class__(filter(lambda x: x.dev_type in device_types, self))

    def filter_by_device_mode(self, device_mode: DeviceMode) -> DpllDevices:
        """Returns a new instance containing only items with the given device mode.

        device_type: device type enumeration to be filtered.
        """

        return self.__class__(filter(lambda x: x.dev_mode == device_mode, self))

    def filter_by_device_mode_supported(self, mode_supported: DeviceMode) -> DpllDevices:
        """Returns a new instance containing only items with the given device mode.

        device_type: device type enumeration to be filtered.
        """

        return self.__class__(filter(lambda x: mode_supported in x.dev_mode_supported, self))

    def filter_by_device_lock_status(self, lock_status: LockStatus) -> DpllDevices:
        """Returns a new instance containing only items with the given device lock status.

        lock_status: lock status to be filtered.
        """

        return self.__class__(filter(lambda x: x.lock_status == lock_status, self))

    def filter_by_device_lock_statuses(self, lock_statuses: list[LockStatus]) -> DpllDevices:
        """Returns a new instance containing only items with the given lock statuses.

        lock_statuses: list with the lock status enumerations to be filtered.
        """

        return self.__class__(filter(lambda x: x.lock_status in lock_statuses, self))

    def filter_by_device_lock_status_error(self, lock_status_error: LockStatusError) -> DpllDevices:
        """Returns a new instance containing only items with the given device lock status error.

        lock_status_error: error status to be filtered.
        """

        return self.__class__(filter(lambda x: x.lock_status_error == lock_status_error, self))

    def filter_by_device_lock_status_errors(self, lock_status_errors: list[LockStatusError]) -> DpllDevices:
        """Returns a new instance containing only items with the given lock status errors.

        lock_status_errors: list with the error status enumerations to be filtered.
        """

        return self.__class__(filter(lambda x: x.lock_status_error in lock_status_errors, self))
