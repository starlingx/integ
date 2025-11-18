# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module defines and implements the DPLL interface for netlink"""

from __future__ import annotations
from ..base import NlError
from ..common import NetlinkException
from ..common import NetlinkFactory
from .constants import DeviceFields
from .constants import PinFields
from .constants import PinParentFields
from .devices import DpllDevice
from .devices import DpllDevices
from .pins import DpllPins


class DPLLCommands:
    """List of Netlink operation for DPLL."""
    __slots__ = ()
    DEVICE_GET = 'device-get'
    PIN_GET = 'pin-get'
    PIN_SET = 'pin-set'


class NetlinkDPLL:

    _ynl = NetlinkFactory.get_dpll_instance()

    def __init__(self, multi_instance: bool = False):
        """Get a DPLL instance.

        By default, a single YNL instance is shared by all DPLL instances, avoiding
        loading and parsing spec/schema YAML files on each new instance. If simultaneous
        access is required, you can create dedicated instances by setting the multi_instance
        option to True.

        multi_instance: if true creates a dedicated instance.
        """

        if multi_instance:
            self._ynl = NetlinkFactory.get_dpll_instance()

    def _get_device_by_id(self, dev_id: int) -> dict:
        """Returns a dict containing the details of the device.

        The returned dict has all the fields returned by Netlink.
        Raises NetlinkException class in case of error.

        dev_id: Netlink device identifier.
        """

        try:
            dev_info = self._ynl.do(
                DPLLCommands.DEVICE_GET,
                {DeviceFields.ID: dev_id})

            return dev_info

        except NlError as e:
            raise NetlinkException(e)

    def get_device_by_id(self, dev_id: int) -> DpllDevice:
        """Returns a DpllDevice instance with the device information.

        Raises NetlinkException class in case of error.

        dev_id: Netlink device identifier.
        """

        return DpllDevice.loadDevice(self._get_device_by_id(dev_id))

    def get_devices_by_clock_id(self, clock_id: int) -> DpllDevices:
        """Returns a list of devices with their settings for a specific clock device.

        Raises NetlinkException class in case of error.

        clock_id: Clock device identifier.
        """

        return self.get_all_devices().filter_by_device_clock_id(clock_id)

    def _get_all_devices(self) -> list[dict]:
        """Obtain all DPLL devices in raw format.

        Returns a list of devices available in the system in raw format (keeps
        the same fields and structure returned by Netlink).

        Raises NetlinkException class in case of error.
        """

        try:
            dev_info_list = self._ynl.dump(DPLLCommands.DEVICE_GET, {})

            return dev_info_list

        except NlError as e:
            raise NetlinkException(e)

    def get_all_devices(self) -> DpllDevices:
        """Obtain all DPLL devices.

        Loads and parses all DPLL information found in the system returned by get_all_devices
        method and creates a DpllDevices instance. No pins information is included.
        See DPllDevices.load() method.

        Raises NetlinkException class in case of error.
        """

        return DpllDevices.loadDevices(self._get_all_devices())

    def _get_pin_by_id(self, pin_id: int) -> dict:
        """Returns a dict containing the details of the DPLL device pin.

        Keeps the same format and fields returned by Netlink.
        Raises NetlinkException class in case of error.

        pin_id: Device pin id.
        """

        try:
            pin_info = self._ynl.do(
                DPLLCommands.PIN_GET, {PinFields.ID: pin_id})

            return pin_info

        except NlError as e:
            raise NetlinkException(e)

    def get_pins_by_id(self, pin_id: int) -> DpllPins:
        """Returns a DpllPins instance with all pins of the DPLL device.

        Raises NetlinkException class in case of error.

        pin_id: Device pin id.
        """

        return DpllPins.loadPins(self._get_all_devices(), [self._get_pin_by_id(pin_id)])

    def get_pins_by_clock_id(self, clock_id: int) -> DpllPins:
        """Returns a list of all pins and their settings for the given clock device.

        Raises NetlinkException class in case of error.

        clock_id: Clock device identifier.
        """

        return self.get_all_pins().filter_by_device_clock_id(clock_id)

    def _get_all_pins(self) -> list[dict]:
        """Obtain all DPLL pins in raw format.

        Returns a list of all pins from all devices available in the system in raw
        format (keeps the same fields and structure returned by Netlink).

        Raises NetlinkException class in case of error.
        """

        try:
            pins_info = self._ynl.dump(DPLLCommands.PIN_GET, {})

            return pins_info

        except NlError as e:
            raise NetlinkException(e)

    def get_all_pins(self) -> DpllPins:
        """Obtain all DPLL pins.

        Loads and parses all DPLL information found in the system returned by
        get_all_devices and get_all_pins methods and creates a DpllPins instance.
        See DPllPins.load() method.

        Raises NetlinkException class in case of error.
        """

        return DpllPins.loadPins(self._get_all_devices(), self._get_all_pins())

    def _set_pin(self, pin_info: dict):
        """Change the pin configuration.

        Changes the pin configuration according to the given pin information.
        Not all pin field are mutable, use _get_pin_by_id() to print the pin
        capabilities, and check which pin fields can be changed.

        Raises NetlinkException class in case of error.
        """

        try:
            result = self._ynl.do(DPLLCommands.PIN_SET, pin_info)

            return result

        except NlError as e:
            raise NetlinkException(e)

    def set_pin_direction(self, pin_id: int, pin_direction: int):
        """Change pin direction.

        Change the pin direction. All pin parents are changed at the same time.

        Raises NetlinkException class in case of error.
        """

        pin_info = {
            PinFields.ID: pin_id,
            PinFields.PARENT_DEVICE: []
        }

        # get pin's parent ids, and set the direction in all of them.
        pins = self.get_pins_by_id(pin_id)
        parent_ids = list(pin.dev_id for pin in pins)
        for parent_id in parent_ids:
            pin_info[PinFields.PARENT_DEVICE].append(
                {
                    PinParentFields.PARENT_ID: parent_id,
                    PinParentFields.DIRECTION: pin_direction
                }
            )

        return self._set_pin(pin_info)

    def set_pin_priority(self, pin_id: int, pin_priority: int):
        """Change pin priority

        Change the pin priority. All pin parents are changed at the same time.

        Raises NetlinkException class in case of error.
        """

        pin_info = {
            PinFields.ID: pin_id,
            PinFields.PARENT_DEVICE: []
        }

        # get pin's parent ids, and set the priority in all of them.
        pins = self.get_pins_by_id(pin_id)
        parent_ids = list(pin.dev_id for pin in pins)
        for parent_id in parent_ids:
            pin_info[PinFields.PARENT_DEVICE].append(
                {
                    PinParentFields.PARENT_ID: parent_id,
                    PinParentFields.PRIORITY: pin_priority
                }
            )

        return self._set_pin(pin_info)
