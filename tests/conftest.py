#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
"""Test configuration and shared fixtures for integ project."""

import os
import sys

# Add pynetlink source to path
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'python', 'pynetlink', 'src'))

# Project root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
