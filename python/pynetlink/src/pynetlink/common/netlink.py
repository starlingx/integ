#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module contains common classes for Netlink library"""

import os
from importlib.resources import files
from ..base import NlError
from ..base import YnlFamily


class NetlinkException(Exception):

    def __init__(self, e: NlError):
        self.os_code = e.error
        self.nl_msg = e.nl_msg.extack
        self.nl_code = e.nl_msg.error

    def __str__(self):
        if(self.os_code != 0):
            return f'OS error: {os.strerror(self.os_code)} ({self.os_code})'
        else:
            return f'Netlink error: {self.nl_msg} ({self.nl_code})'


class NetlinkFactory:

    @staticmethod
    def get_instance(yaml_spec_file: str,
                     yaml_schema_file: str = 'genetlink.yaml') -> YnlFamily:
        """Returns a new instance for access the netlink protocol.

        yaml_spec_file: Name of the YAML file containing the access specifications
        for the netlink interface.
        yaml_schema_file: Name of the YAML file containing the schema definitions
        to translate the values of the netlink protocol.
        """

        return YnlFamily(
            files('pynetlink').joinpath('specs', yaml_spec_file),
            files('pynetlink').joinpath('schemas', yaml_schema_file),
            process_unknown=True)

    @staticmethod
    def get_dpll_instance() -> YnlFamily:
        """Returns a new instance for interact with DPLL devices using netlink protocol."""

        return NetlinkFactory.get_instance('dpll.yaml')
