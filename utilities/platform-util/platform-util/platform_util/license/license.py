#
# Copyright (c) 2017-2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from ctypes import cdll
from ctypes import util
from ctypes import c_bool
from ctypes import c_int
from ctypes import c_char_p
from ctypes import pointer
from ctypes import create_string_buffer
import logging
import os
from platform_util.license import constants
from platform_util.license import exception
import re
import sys
from sysinv.common import constants as sysinv_constants
from tsconfig.tsconfig import system_type
from tsconfig.tsconfig import system_mode
from tsconfig.tsconfig import SW_VERSION

LOG = logging.getLogger(__name__)

sm_common = cdll.LoadLibrary(util.find_library("sm_common"))


class c_char_p_sub(c_char_p):
    pass


def get_licenses_info():
    """Get the license information"""

    feature_list = []
    sm_common.flex_lm_license_get_feature_list.restype = c_char_p_sub
    features = sm_common.flex_lm_license_get_feature_list()
    if features.value:
        feature_list = [feature for feature in features.value.split(',')
            if feature.startswith(constants.FEATURE_PREFIX)]
    sm_common.flex_lm_license_free(features)

    lc_attrs_list = []
    licenses = [license for license in constants.LICENSE_NAMES]
    for feature in feature_list:
        try:
            lc_attrs = verify_feature_license(feature)
        except Exception as e:
            # Set the license attributes for installed expired licenses
            if constants.EXPIRED.lower() in e:
                process_license = True
                status = constants.INSTALLED
                expiry_date = constants.EXPIRED
            # Set the license attributes for installed invalid licenses
            elif constants.INVALID or constants.VERSION_LICENSE_ERR in e:
                process_license = True
                status = constants.INVALID
                expiry_date = '-'
            # Unknown license
            else:
                process_license = False
                LOG.warning("Feature %s is not supported." % feature)

            # Send supporting licenses only
            name = constants.LICENSE_MAP.get(feature)
            if process_license and name:
                lc_attrs = dict(name=name, status=status,
                    expiry_date=expiry_date)
            else:
                lc_attrs = dict()

        if lc_attrs:
            license_name = lc_attrs.get('name')
            if (not any(lc.get('name') == license_name
                 for lc in lc_attrs_list)):
                # Get the list of license attributes for all valid
                # licenses and installed expired/invalid licenses
                lc_attrs_list.append(lc_attrs)
                if license_name in licenses:
                    # Get the list of not-installed license names
                    licenses.remove(license_name)

    # Set the license attributes for all
    # not-installed licenses
    for license_name in licenses:
        lc_attrs = dict(name=license_name,
            status=constants.NOT_INSTALLED,
            expiry_date='-')
        lc_attrs_list.append(lc_attrs)

    # Return the list of license attributes
    # for all supporting licenses
    return lc_attrs_list


def verify_feature_license(feature_name, feature_version=None):
    """Verify a license of a feature"""

    valid = pointer(c_bool(0))

    if not feature_version:
        feature_version = SW_VERSION

    expire_days_left = pointer(c_int(0))
    expire_date_text = create_string_buffer(
        constants.LICENSE_DATE_TEXT_MAX_CHAR)
    vendor = create_string_buffer(
        constants.LICENSE_VENDOR_MAX_CHAR)
    err_msg = create_string_buffer(
        constants.LICENSE_ERR_MSG_MAX_CHAR)

    LOG.info("License check. License feature name=%s version=%s",
             feature_name, feature_version)
    feature_check = sm_common.sm_license_check(valid,
                                               feature_name,
                                               feature_version,
                                               expire_days_left, expire_date_text,
                                               vendor, err_msg)
    sm_common.sm_error_str.restype = c_char_p
    if (sm_common.sm_error_str(feature_check) != 'OKAY' or
       (not valid.contents.value)):

        LOG.error("License check error, error = %s\n", err_msg.value)
        msg = "ERROR: License check failed; "
        if constants.NO_FEATURE_LICENSE_ERR in err_msg.value:
            msg += "the license file does not contain the required license."
            raise exception.LicenseNotFound(msg)
        elif constants.EXPIRED_LICENSE_ERR in err_msg.value:
            msg += "the license file contains a license that is expired."
            raise exception.ExpiredLicense(msg)
        elif constants.VERSION_LICENSE_ERR in err_msg.value:
            msg += "the license file contains a license which is NOT applicable " \
                   "to the current system software version."
            raise exception.InvalidLicenseVersion(msg)
        else:
            msg += "the license file contains an invalid license."
            raise exception.InvalidLicense(msg)

    vendor = re.search(r'\<name\>(.*?)\<\/name\>', vendor.value)
    if vendor:
        license_name = vendor.group(1)
    else:
        license_name = constants.LICENSE_MAP.get(feature_name)

    # Return license attributes of a valid license
    lc_attrs = dict(name=license_name, status=constants.INSTALLED,
        expiry_date=expire_date_text.value)

    return lc_attrs


def verify_license(license_file):
    """Verify all features in a license file"""

    os.environ["LM_LICENSE_FILE"] = license_file
    os.environ["WIND_LICENSE_PROXY"] = "/usr/bin/wrlmproxy-5.0.2"

    # Get all features in the license file
    feature_list = []
    sm_common.flex_lm_license_get_feature_list.restype = c_char_p_sub
    features = sm_common.flex_lm_license_get_feature_list()
    if features.value:
        feature_list = [feature for feature in features.value.split(',')
            if feature.startswith(constants.FEATURE_PREFIX)]
    sm_common.flex_lm_license_free(features)

    # Validate license of each feature in the license file
    for feature in feature_list:
        verify_feature_license(feature)

    if system_type == sysinv_constants.TIS_AIO_BUILD:
        if system_mode == sysinv_constants.SYSTEM_MODE_SIMPLEX:
            product_license = constants.AIO_SIMPLEX_SYSTEM_LICENSES
        elif (system_mode == sysinv_constants.SYSTEM_MODE_DUPLEX or
             system_mode == sysinv_constants.SYSTEM_MODE_DUPLEX_DIRECT):
            product_license = constants.AIO_SYSTEM_LICENSES
    elif system_type == sysinv_constants.TIS_STD_BUILD:
        product_license = constants.STD_SYSTEM_LICENSES

    # Verify the right product license is installed
    if not any(feature in feature_list for feature in product_license):
        raise exception.InvalidLicenseType(
            "ERROR: License check failed; the license file does not contain a "
            "product license for the current %s/%s." % (system_type, system_mode))

    # Verify the licensed tech-preview technologies(ex. baremetal container..)
    # Check if magnum or ironic services are currently running
    # If yes, verify the feature licenses for magnum/ironic are licensed in the
    # license file.


def main():
    if len(sys.argv) == 2 :
        licensefile = sys.argv[1]
    else:
        print("Usage: verify-license <license file>")
        exit(-1)

    try:
        verify_license(licensefile)
    except exception.InvalidLicenseType:
        exit(1)
    except exception.LicenseNotFound:
        exit(2)
    except exception.ExpiredLicense:
        exit(3)
    except exception.InvalidLicenseVersion:
        exit(4)
    except exception.InvalidLicense:
        exit(5)
