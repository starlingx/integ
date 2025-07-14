#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module tests common Netlink class"""

from unittest import TestCase
from ..base import YnlFamily
from ..common import NetlinkFactory


class NetlinkUtilsTestCase(TestCase):

    def test_get_instance_with_default_params(self):

        new_instance = NetlinkFactory.get_instance('dpll.yaml')
        self.assertIsInstance(new_instance, YnlFamily)

    def test_get_instance_using_specific_params(self):

        new_instance = NetlinkFactory.get_instance('dpll.yaml', 'genetlink-legacy.yaml')
        self.assertIsInstance(new_instance, YnlFamily)

    def test_get_instance_raises_exception_with_passing_wrong_params(self):

        with self.assertRaises(FileNotFoundError) as cm_exc:
            NetlinkFactory.get_instance('spec-not-exists.yaml')

            self.assertEqual(FileNotFoundError, cm_exc.exception, 'Invalid YAML spec file')

        with self.assertRaises(FileNotFoundError) as cm_exc:
            NetlinkFactory.get_instance('dpll.yaml', 'schema-not-exists.yaml')

            self.assertEqual(FileNotFoundError, cm_exc.exception, 'Invalid YAML schema file')
