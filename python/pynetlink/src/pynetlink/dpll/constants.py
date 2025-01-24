#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module has the constants and enumerators used by other dpll modules."""

from enum import Enum
from enum import unique


class DeviceFields:
    """List of possible field names returned in device structure."""

    __slots__ = ()
    CLOCK_ID = 'clock-id'
    CLOCK_QUALITY = 'clock-quality-level'
    ID = 'id'
    MODE = 'mode'
    MODE_SUPPORTED = 'mode-supported'
    MODULE_NAME = 'module-name'
    PAD = 'pad'
    TYPE = 'type'
    LOCK_STATUS = 'lock-status'
    LOCK_STATUS_ERROR = 'lock-status-error'


class PinFields:
    """List of possible field names returned in pin structure."""

    __slots__ = ()
    BOARD_LABEL = 'board-label'
    CAPABILITIES = 'capabilities'
    CLOCK_ID = 'clock-id'
    DIRECTION = 'direction'
    FREQUENCY = 'frequency'
    FREQUENCY_SUPPORTED = 'frequency-supported'
    FREQUENCY_MAX = 'frequency-max'
    FREQUENCY_MIN = 'frequency-min'
    ID = 'id'
    MODULE_NAME = 'module-name'
    PACKAGE_LABEL = 'package-label'
    PANEL_LABEL = 'panel-label'
    PARENT_ID = 'parent-id'
    PARENT_DEVICE = 'parent-device'
    PARENT_PIN = 'parent-pin'
    PHASE_ADJUST = 'phase-adjust'
    PHASE_ADJUST_MAX = 'phase-adjust-max'
    PHASE_ADJUST_MIN = 'phase-adjust-min'
    PHASE_OFFSET = 'phase-offset'
    PRIORITY = 'prio'
    STATE = 'state'
    TYPE = 'type'


class PinParentFields:
    """List of possible field names returned in the nested structure 'parent-device'."""

    __slots__ = ()
    DIRECTION = 'direction'
    PARENT_ID = 'parent-id'
    PHASE_OFFSET = 'phase-offset'
    PRIORITY = 'prio'
    STATE = 'state'


class DpllEnum(Enum):

    def __repr__(self):
        return self.value


@unique
class DeviceType(DpllEnum):
    """Enumeration for dev_type field."""

    UNDEFINED = 'undefined'     # undefined
    EEC = 'eec'                 # Ethernet Equipment Clock
    PPS = 'pps'                 # Pulse-Per-Second signal


@unique
class DeviceMode(DpllEnum):
    """Enumeration for dev_mode and dev_mode_supported fields."""

    UNDEFINED = 'undefined'     # undefined
    MANUAL = 'manual'           # input can be only selected by sending a request to dpll
    AUTO = 'automatic'          # highest prio input pin auto selected by dpll


@unique
class LockStatus(DpllEnum):
    """Enumeration for lock_status field."""

    UNDEFINED = 'undefined'                 # dpll lock status not set
    HOLDOVER = 'holdover'                   # dpll is in holdover state
    LOCKED = 'locked'                       # dpll is locked to a valid signal, but no holdover available
    LOCKED_AND_HOLDOVER = 'locked-ho-acq'   # dpll is locked and holdover acquired
    UNLOCKED = 'unlocked'                   # dpll was not yet locked to any valid input


@unique
class LockStatusError(DpllEnum):
    """Enumeration for lock_status_error field."""

    # the FFO (Fractional Frequency Offset) between the RX and TX symbol rate on the media got too high.
    FFO_TOO_HIGH = 'fractional-frequency-offset-too-high'
    MEDIA_DOWN = 'media-down'   # dpll device lock status was changed because of associated media got down
    NONE = 'none'               # pll device lock status was changed without any error
    UNDEFINED = 'undefined'     # dpll device lock status was changed due to undefined error


@unique
class PinType(DpllEnum):
    """Enumeration for pin_type field."""

    UNDEFINED = 'undefined'     # undefined
    EXT = 'ext'                 # external input
    GNSS = 'gnss'               # GNSS recovered clock
    MUX = 'mux'                 # Aggregates another layer of selectable pins
    OCXO = 'int-oscillator'     # device internal oscillator
    SYNCE = 'synce-eth-port'    # ethernet port PHY’s recovered clock


@unique
class PinState(DpllEnum):
    """Enumeration for pin_state field."""

    UNDEFINED = 'undefined'         # undefined
    CONNECTED = 'connected'         # pin connected, active input of phase locked loop
    DISCONNECTED = 'disconnected'   # pin disconnected, not considered as a valid input
    SELECTABLE = 'selectable'       # pin enabled for automatic input selection


@unique
class PinDirection(DpllEnum):
    """Enumeration for pin_direction field."""

    UNDEFINED = 'undefined'     # undefined
    INPUT = 'input'             # pin used as a input of a signal
    OUTPUT = 'output'           # pin used to output the signal
