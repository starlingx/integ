#
# Copyright (c) 2017 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4
# coding=utf-8
#

# All available licenses
LICENSE_FEATURE_STD = "WR_TS"
LICENSE_FEATURE_STD_EVAL = "WR_TS_EVAL"
LICENSE_FEATURE_AIO = "WR_TS_CPE"
LICENSE_FEATURE_AIO_EVAL = "WR_TS_CPE_EVAL"
LICENSE_FEATURE_SIMPLEX = "WR_TS_CPE_SX"
LICENSE_FEATURE_SIMPLEX_EVAL = "WR_TS_CPE_SX_EVAL"

# All supporting license names
STD_PRODUCT_CFG = "Standard_Product_Configuration"
AIO_PRODUCT_CFG = "All-In-One_Product_Configuration"
AIO_SX_PRODUCT_CFG = "All-In-One_Simplex_Product_Configuration"

# All supporting licenses list
LICENSE_NAMES = [
    STD_PRODUCT_CFG,
    AIO_PRODUCT_CFG,
    AIO_SX_PRODUCT_CFG
]

# License mapping 
LICENSE_MAP = { 
    LICENSE_FEATURE_STD: STD_PRODUCT_CFG,
    LICENSE_FEATURE_AIO: AIO_PRODUCT_CFG,
    LICENSE_FEATURE_SIMPLEX: AIO_SX_PRODUCT_CFG,
    LICENSE_FEATURE_STD_EVAL: STD_PRODUCT_CFG,
    LICENSE_FEATURE_AIO_EVAL: AIO_PRODUCT_CFG,
    LICENSE_FEATURE_SIMPLEX_EVAL: AIO_SX_PRODUCT_CFG,
}

# Product licenses lists
STD_SYSTEM_LICENSES = [LICENSE_FEATURE_STD, LICENSE_FEATURE_STD_EVAL]
AIO_SYSTEM_LICENSES = [LICENSE_FEATURE_AIO, LICENSE_FEATURE_AIO_EVAL]
AIO_SIMPLEX_SYSTEM_LICENSES = [LICENSE_FEATURE_SIMPLEX, LICENSE_FEATURE_SIMPLEX_EVAL]

# License check error types
NO_FEATURE_LICENSE_ERR = "No such feature exists"
EXPIRED_LICENSE_ERR = "Feature has expired"
VERSION_LICENSE_ERR = "License file does not support this version"

# License limits
LICENSE_DATE_TEXT_MAX_CHAR = 32
LICENSE_ERR_MSG_MAX_CHAR = 512
LICENSE_VENDOR_MAX_CHAR =128

# Package name prefix
PACKAGE_PREFIX = "NL_TS"
# Feature name prefix
FEATURE_PREFIX = "WR_TS"

# License status
INSTALLED = "Installed"
NOT_INSTALLED = "Not-installed"
INVALID = "Invalid"

EXPIRED = "Expired"
