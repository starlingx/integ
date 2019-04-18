#
# Copyright (c) 2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


class ValidateError(Exception):
    """Base class for license validation exceptions"""

    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return self.message or ""


class InvalidLicense(ValidateError):
    """Generic invalid license error"""
    pass


class ExpiredLicense(ValidateError):
    """Expired license error"""
    pass


class InvalidLicenseVersion(ValidateError):
    """Invalid license version error"""
    pass


class InvalidLicenseType(ValidateError):
    """Invalid license type error"""
    pass


class LicenseNotFound(ValidateError):
    """License not found error"""
    pass
