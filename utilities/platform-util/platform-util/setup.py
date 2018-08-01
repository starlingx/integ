#
# Copyright (c) 2017-2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import setuptools

setuptools.setup(
    name='platform_util',
    description='Platform Util',
    version='1.0.0',
    license='Apache-2.0',
    platforms=['any'],
    packages=['platform_util', 'platform_util.license'],
    entry_points={
        'console_scripts': [
            'verify-license = platform_util.license.license:main'
        ],
    }
)
