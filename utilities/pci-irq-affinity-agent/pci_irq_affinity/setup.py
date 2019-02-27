#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#
# flake8: noqa
#
from setuptools import setup, find_packages

setup(
    name='pci-irq-affinity-agent',
    description='PCI Interrupt Affinity Agent',
    version='1.0.0',
    classifiers=[
        'Environment :: OpenStack',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.6',
    ],
    license='Apache-2.0',
    platforms=['any'],
    provides='pci_irq_affinity_agent',
    packages=find_packages(),
    include_package_data=False,
    entry_points={
        'console_scripts': [
            'pci-irq-affinity-agent = pci_irq_affinity.agent:process_main',
        ],
    }
)
