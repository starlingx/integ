#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module contains classes related to DPLL device pins."""

from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Union
from .constants import PinDirection
from .constants import PinFields
from .constants import PinParentFields
from .constants import PinState
from .constants import PinType
from .devices import DpllDevice
from .devices import DpllDevices


@dataclass(frozen=True, init=False)
class DpllPin(DpllDevice):

    pin_id: int
    pin_board_label: str = field(hash=False)
    pin_panel_label: str = field(hash=False)
    pin_package_label: str = field(hash=False)
    pin_type: PinType = field(hash=False)
    pin_state: PinState = field(hash=False)
    pin_priority: int = field(hash=False)
    pin_phase_offset: int = field(hash=False)
    pin_direction: PinDirection = field(hash=False)

    def __init__(self, **kwargs):
        # Python 3.9 doesn't support kw_only option of dataclasses.
        # The init method has been overwritten to allow having fields with default values in
        # the parent class (DpllDevice) and having other mandatory fields in child class (DpllPin)
        super().__init__(**{k: v for k, v in kwargs.items() if k in DpllDevice.__annotations__})

        super().__setattr__('pin_id', kwargs['pin_id'])
        super().__setattr__('pin_board_label', kwargs.get('pin_board_label', None))
        super().__setattr__('pin_panel_label', kwargs.get('pin_panel_label', None))
        super().__setattr__('pin_package_label', kwargs.get('pin_package_label', None))
        super().__setattr__('pin_type', kwargs.get('pin_type', PinType.UNDEFINED))
        super().__setattr__('pin_state', kwargs.get('pin_state', PinState.UNDEFINED))
        super().__setattr__('pin_priority', kwargs.get('pin_priority', None))
        super().__setattr__('pin_phase_offset', kwargs.get('pin_phase_offset', None))
        super().__setattr__('pin_direction', kwargs.get('pin_direction', PinDirection.UNDEFINED))

    @classmethod
    def loadPin(cls, device: DpllDevice, pin: dict) -> DpllPin:
        """Correlates DPLL device and pin data returned from Netlink and creates a DpllPin class.

        The fields not specified in the list will be set to a default value.

        device: DPLL device data in raw format.
        pin: DPLL device pin data in raw format.
        """

        if device is None:
            raise ValueError('Device parameter must be informed.')
        elif pin is None:
            raise ValueError('Pin parameter must be informed.')

        if PinFields.PARENT_ID in pin:
            return DpllPin(
                **asdict(device),
                pin_id=int(pin[PinFields.ID]),
                pin_board_label=str(pin[PinFields.BOARD_LABEL]) if PinFields.BOARD_LABEL in pin else None,
                pin_panel_label=str(pin[PinFields.PANEL_LABEL]) if PinFields.PANEL_LABEL in pin else None,
                pin_package_label=str(pin[PinFields.PACKAGE_LABEL]) if PinFields.PACKAGE_LABEL in pin else None,
                pin_type=PinType(pin[PinFields.TYPE]),
                pin_state=PinState(pin.get(PinFields.STATE, PinState.UNDEFINED)),
                pin_priority=pin.get(PinFields.PRIORITY),
                pin_phase_offset=pin.get(PinFields.PHASE_OFFSET),
                pin_direction=PinDirection(pin.get(PinFields.DIRECTION,
                                                   PinDirection.UNDEFINED)),
            )

        elif PinFields.PARENT_DEVICE in pin:
            parent_pin = next((x for x in pin[PinFields.PARENT_DEVICE]
                               if x.get(PinParentFields.PARENT_ID) == device.dev_id), None)

            if parent_pin is None:
                raise ValueError(f'No pin parent reference found for device id {device.dev_id}')

            return DpllPin(
                **asdict(device),
                pin_id=int(pin[PinFields.ID]),
                pin_board_label=str(pin[PinFields.BOARD_LABEL]) if PinFields.BOARD_LABEL in pin else None,
                pin_panel_label=str(pin[PinFields.PANEL_LABEL]) if PinFields.PANEL_LABEL in pin else None,
                pin_package_label=str(pin[PinFields.PACKAGE_LABEL]) if PinFields.PACKAGE_LABEL in pin else None,
                pin_type=PinType(pin[PinFields.TYPE]),
                pin_state=PinState(parent_pin.get(PinParentFields.STATE,
                                                  PinState.UNDEFINED)),
                pin_priority=parent_pin.get(PinParentFields.PRIORITY),
                pin_phase_offset=parent_pin.get(PinParentFields.PHASE_OFFSET),
                pin_direction=PinDirection(parent_pin.get(PinParentFields.DIRECTION,
                                                          PinDirection.UNDEFINED)),
            )

        else:
            raise ValueError(f'No pin reference found for device id {device.dev_id}')


class DpllPins(DpllDevices):

    @classmethod
    def loadPins(cls, devices: list[dict], pins: list[dict]) -> DpllPins:
        """Correlates DPLL device and pins data and creates the DpllPins class.

        Both parameters are expect in the format returned by Netlink. The fields not specified
        will be set to the default value.

        devices: list of DPLL devices in raw format.
        pins: list of DPLL pins in raw format.
        """

        instance = cls()
        dpll_devices = DpllDevices.loadDevices(devices)

        for pin in pins:
            # Processes only pins without parent pin fields
            if PinFields.PARENT_PIN in pin:
                continue

            if PinFields.PARENT_DEVICE in pin:
                for pin_parent in pin[PinFields.PARENT_DEVICE]:
                    # Get the device reference
                    device = dpll_devices.filter_by_device_id(
                        pin_parent.get(PinParentFields.PARENT_ID))

                    instance.add(DpllPin.loadPin(device, pin))

            else:
                # Get the device reference
                device = dpll_devices.filter_by_device_id(
                    pin.get(PinFields.PARENT_ID))

                instance.add(DpllPin.loadPin(device, pin))

        return instance

    def filter_by_pin_id(self, pin_id: int) -> Union[DpllPin, None]:
        """Searches for the pin identifier and returns a DpllPin instance.

        If not found, returns None.

        pin_id: pin id to be filtered
        """

        return next((x for x in self if x.pin_id == pin_id), None)

    def filter_by_pin_direction(self, direction: PinDirection) -> DpllPins:
        """Returns a new instance containing only items with the given direction value.

        direction: direction enumeration to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_direction == direction, self))

    def filter_by_pin_directions(self, directions: list[PinDirection]) -> DpllPins:
        """Returns a new instance containing only items with the given direction value.

        directions: list with the direction enumerations to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_direction in directions, self))

    def filter_by_pin_board_label(self, board_label: str) -> DpllPins:
        """Returns a new instance containing only items with the given board label.

        board_label: label value to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_board_label == board_label, self))

    def filter_by_pin_board_labels(self, board_labels: list[str]) -> DpllPins:
        """Returns a new instance containing only items with the given board labels.

        board_labels: list of the labels to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_board_label in board_labels, self))

    def filter_by_pin_panel_label(self, panel_label: str) -> DpllPins:
        """Returns a new instance containing only items with the given panel label.

        panel_label: label value to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_panel_label == panel_label, self))

    def filter_by_pin_panel_labels(self, panel_labels: list[str]) -> DpllPins:
        """Returns a new instance containing only items with the given panel labels.

        panel_labels: list of the labels to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_panel_label in panel_labels, self))

    def filter_by_pin_package_label(self, package_label: str) -> DpllPins:
        """Returns a new instance containing only items with the given package label.

        package_label: label value to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_package_label == package_label, self))

    def filter_by_pin_package_labels(self, package_labels: list[str]) -> DpllPins:
        """Returns a new instance containing only items with the given package labels.

        package_labels: list of the labels to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_package_label in package_labels, self))

    def filter_by_pin_state(self, pin_state: PinState) -> DpllPins:
        """Returns a new instance containing only items with the given pin state.

        pin_state: state enumeration to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_state == pin_state, self))

    def filter_by_pin_states(self, pin_states: list[PinState]) -> DpllPins:
        """Returns a new instance containing only items with the given pin states.

        pin_states: list with the state enumerations to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_state in pin_states, self))

    def filter_by_pin_type(self, pin_type: PinType) -> DpllPins:
        """Returns a new instance containing only items with the given pin type.

        pin_type: type enumeration to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_type == pin_type, self))

    def filter_by_pin_types(self, pin_types: list[PinType]) -> DpllPins:
        """Returns a new instance containing only items with the given pin types.

        pin_types: list with the types enumeration to be filtered.
        """

        return self.__class__(filter(lambda x: x.pin_type in pin_types, self))

    def order_by_pin_priority(self, reverse: bool = False) -> list[DpllPin]:
        """Returns a list of sorted DPllPins.

        Sorts using the priority of DPLL pins in ascending order and returns a
        list of sorted DpllPin.

        reverse: sort in descending order.
        """

        return sorted(self,
                      key=lambda x: (x.pin_priority is None, x.pin_priority),
                      reverse=reverse)
