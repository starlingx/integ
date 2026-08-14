#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Unit tests for pynetlink DPLL interface.

Covers dpll.py and common/netlink modules.
"""

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

# Path setup handled by conftest.py

from pynetlink.base.ynl import NlError
from pynetlink.common.netlink import NetlinkException
from pynetlink.dpll import dpll as dpll_module
from pynetlink.dpll.dpll import NetlinkDPLL
from pynetlink.dpll.devices import DpllDevice
from pynetlink.dpll.devices import DpllDevices
from pynetlink.dpll.pins import DpllPins


def _make_raw_device(dev_id=1, clock_id=100):
    """Helper to create raw device dict."""
    return {
        'id': dev_id,
        'clock-id': clock_id,
        'module-name': 'ice',
        'mode': 'automatic',
        'type': 'eec',
        'lock-status': 'locked-ho-acq',
        'lock-status-error': 'none',
    }


def _make_raw_pin(pin_id=10, parent_id=1):
    """Helper to create raw pin dict."""
    return {
        'id': pin_id,
        'board-label': 'SMA1',
        'type': 'ext',
        'parent-device': [
            {
                'parent-id': parent_id,
                'state': 'connected',
                'prio': 5,
                'direction': 'input',
            }
        ],
    }


class TestNetlinkException(unittest.TestCase):
    """Tests for NetlinkException class."""

    def test_exception_with_os_error(self):
        """Test NetlinkException with OS error code."""
        mock_nl_msg = MagicMock()
        mock_nl_msg.extack = 'test error'
        mock_nl_msg.error = -1
        mock_error = MagicMock()
        mock_error.error = 2  # ENOENT
        mock_error.nl_msg = mock_nl_msg
        exc = NetlinkException(mock_error)
        self.assertEqual(exc.os_code, 2)
        self.assertIn('No such file or directory', str(exc))

    def test_exception_with_netlink_error(self):
        """Test NetlinkException with netlink error code."""
        mock_nl_msg = MagicMock()
        mock_nl_msg.extack = 'netlink failure'
        mock_nl_msg.error = -100
        mock_error = MagicMock()
        mock_error.error = 0
        mock_error.nl_msg = mock_nl_msg
        exc = NetlinkException(mock_error)
        self.assertEqual(exc.os_code, 0)
        self.assertIn('Netlink error', str(exc))
        self.assertIn('netlink failure', str(exc))


@patch.object(dpll_module, 'NetlinkFactory')
class TestNetlinkDPLLDeviceMethods(unittest.TestCase):
    """Tests for NetlinkDPLL device-related methods."""

    def test_get_device_by_id(self, mock_factory):
        """Test get_device_by_id returns DpllDevice."""
        mock_ynl = MagicMock()
        mock_ynl.do.return_value = _make_raw_device(dev_id=1)
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        result = dpll.get_device_by_id(1)
        self.assertIsInstance(result, DpllDevice)
        self.assertEqual(result.dev_id, 1)

    def test_get_all_devices(self, mock_factory):
        """Test get_all_devices returns DpllDevices."""
        mock_ynl = MagicMock()
        mock_ynl.dump.return_value = [
            _make_raw_device(dev_id=1),
            _make_raw_device(dev_id=2),
        ]
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        result = dpll.get_all_devices()
        self.assertIsInstance(result, DpllDevices)
        self.assertEqual(len(result), 2)

    def test_get_devices_by_clock_id(self, mock_factory):
        """Test get_devices_by_clock_id filters correctly."""
        mock_ynl = MagicMock()
        mock_ynl.dump.return_value = [
            _make_raw_device(dev_id=1, clock_id=100),
            _make_raw_device(dev_id=2, clock_id=200),
        ]
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        result = dpll.get_devices_by_clock_id(100)
        self.assertEqual(len(result), 1)

    def test_get_device_by_id_nl_error(self, mock_factory):
        """Test get_device_by_id raises NetlinkException on NlError."""
        mock_nl_msg = MagicMock()
        mock_nl_msg.error = -2
        mock_nl_msg.extack = 'not found'
        nl_error = NlError(mock_nl_msg)

        mock_ynl = MagicMock()
        mock_ynl.do.side_effect = nl_error
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        with self.assertRaises(NetlinkException):
            dpll.get_device_by_id(999)

    def test_get_all_devices_nl_error(self, mock_factory):
        """Test _get_all_devices raises NetlinkException on NlError."""
        mock_nl_msg = MagicMock()
        mock_nl_msg.error = -1
        mock_nl_msg.extack = 'error'
        nl_error = NlError(mock_nl_msg)

        mock_ynl = MagicMock()
        mock_ynl.dump.side_effect = nl_error
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        with self.assertRaises(NetlinkException):
            dpll.get_all_devices()


@patch.object(dpll_module, 'NetlinkFactory')
class TestNetlinkDPLLPinMethods(unittest.TestCase):
    """Tests for NetlinkDPLL pin-related methods."""

    def test_get_all_pins(self, mock_factory):
        """Test get_all_pins returns DpllPins."""
        mock_ynl = MagicMock()
        mock_ynl.dump.side_effect = [
            [_make_raw_device(dev_id=1)],  # _get_all_devices
            [_make_raw_pin(pin_id=10, parent_id=1)],  # _get_all_pins
        ]
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        result = dpll.get_all_pins()
        self.assertIsInstance(result, DpllPins)

    def test_get_pins_by_id(self, mock_factory):
        """Test get_pins_by_id returns DpllPins."""
        mock_ynl = MagicMock()
        mock_ynl.dump.return_value = [_make_raw_device(dev_id=1)]
        mock_ynl.do.return_value = _make_raw_pin(pin_id=10, parent_id=1)
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        result = dpll.get_pins_by_id(10)
        self.assertIsInstance(result, DpllPins)

    def test_get_pins_by_clock_id(self, mock_factory):
        """Test get_pins_by_clock_id filters correctly."""
        mock_ynl = MagicMock()
        mock_ynl.dump.side_effect = [
            [_make_raw_device(dev_id=1, clock_id=100)],
            [_make_raw_pin(pin_id=10, parent_id=1)],
        ]
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        result = dpll.get_pins_by_clock_id(100)
        self.assertIsInstance(result, DpllPins)

    def test_get_pin_by_id_nl_error(self, mock_factory):
        """Test _get_pin_by_id raises NetlinkException on NlError."""
        mock_nl_msg = MagicMock()
        mock_nl_msg.error = -2
        mock_nl_msg.extack = 'not found'
        nl_error = NlError(mock_nl_msg)

        mock_ynl = MagicMock()
        mock_ynl.do.side_effect = nl_error
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        with self.assertRaises(NetlinkException):
            dpll._get_pin_by_id(999)  # pylint: disable=protected-access

    def test_get_all_pins_nl_error(self, mock_factory):
        """Test _get_all_pins raises NetlinkException on NlError."""
        mock_nl_msg = MagicMock()
        mock_nl_msg.error = -1
        mock_nl_msg.extack = 'error'
        nl_error = NlError(mock_nl_msg)

        mock_ynl = MagicMock()
        mock_ynl.dump.side_effect = nl_error
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        with self.assertRaises(NetlinkException):
            dpll._get_all_pins()  # pylint: disable=protected-access


@patch.object(dpll_module, 'NetlinkFactory')
class TestNetlinkDPLLSetPin(unittest.TestCase):
    """Tests for NetlinkDPLL set_pin methods."""

    def test_set_pin_direction(self, mock_factory):
        """Test set_pin_direction calls _set_pin correctly."""
        mock_ynl = MagicMock()
        # get_pins_by_id needs: dump (devices), do (pin)
        mock_ynl.dump.return_value = [_make_raw_device(dev_id=1)]
        mock_ynl.do.side_effect = [
            _make_raw_pin(pin_id=10, parent_id=1),  # _get_pin_by_id
            None,  # _set_pin
        ]
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        dpll.set_pin_direction(10, 'input')
        # Verify _set_pin was called (second do call)
        self.assertEqual(mock_ynl.do.call_count, 2)

    def test_set_pin_priority(self, mock_factory):
        """Test set_pin_priority calls _set_pin correctly."""
        mock_ynl = MagicMock()
        mock_ynl.dump.return_value = [_make_raw_device(dev_id=1)]
        mock_ynl.do.side_effect = [
            _make_raw_pin(pin_id=10, parent_id=1),
            None,
        ]
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        dpll.set_pin_priority(10, 3)
        self.assertEqual(mock_ynl.do.call_count, 2)

    def test_set_pin_nl_error(self, mock_factory):
        """Test _set_pin raises NetlinkException on NlError."""
        mock_nl_msg = MagicMock()
        mock_nl_msg.error = -1
        mock_nl_msg.extack = 'error'
        nl_error = NlError(mock_nl_msg)

        mock_ynl = MagicMock()
        mock_ynl.do.side_effect = nl_error
        mock_factory.get_dpll_instance.return_value = mock_ynl

        dpll = NetlinkDPLL(multi_instance=True)
        with self.assertRaises(NetlinkException):
            # pylint: disable=protected-access
            dpll._set_pin({'id': 10})


@patch.object(dpll_module, 'NetlinkFactory')
class TestNetlinkDPLLInit(unittest.TestCase):
    """Tests for NetlinkDPLL initialization."""

    def test_default_init_shares_instance(self, mock_factory):
        """Default init uses shared class-level YNL instance."""
        # multi_instance=False (default) should
        # NOT call get_dpll_instance
        # in __init__ (it's set at class level)
        dpll = NetlinkDPLL()
        # The class-level _ynl is set during class definition
        # pylint: disable=protected-access
        self.assertIsNotNone(dpll._ynl)

    def test_multi_instance_creates_new(self, mock_factory):
        """multi_instance=True creates a dedicated YNL instance."""
        dpll = NetlinkDPLL(multi_instance=True)
        mock_factory.get_dpll_instance.assert_called()
        # Verify the new instance was assigned
        self.assertEqual(
            dpll._ynl,  # pylint: disable=protected-access
            mock_factory.get_dpll_instance.return_value)


if __name__ == '__main__':
    unittest.main()
