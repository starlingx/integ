#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import setuptools

setuptools.setup(
    name='storage_topology',
    description='Show openstack storage topology',
    version='1.0.0',
    license='Apache-2.0',
    packages=['storage_topology', 'storage_topology.exec'],
    entry_points={
        'console_scripts': [
            'storage-topology = storage_topology.exec.storage_topology:main',
        ]}
)
