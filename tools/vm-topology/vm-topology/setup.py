#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import setuptools

setuptools.setup(
    name='vm_topology',
    description='Show compute resources and VM topology',
    version='1.0.0',
    license='Apache-2.0',
    packages=['vm_topology', 'vm_topology.exec'],
    entry_points={
        'console_scripts': [
            'vm-topology = vm_topology.exec.vm_topology:main',
        ]}
)
