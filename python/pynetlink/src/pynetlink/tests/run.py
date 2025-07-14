#
# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# All Rights Reserved.
#

"""This module execute the unit tests"""

import os
import unittest


def suite():
    loader = unittest.TestLoader()
    loader.testMethodPrefix = 'test_'

    test_path = os.path.dirname(__file__)
    base_path = os.path.abspath(
        test_path + os.sep + os.pardir + os.sep + os.pardir)

    return loader.discover('pynetlink.tests', '*test.py', base_path)


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
