#!/usr/bin/env python
#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import setuptools

setuptools.setup(
    name='python-cephclient',
    packages=['cephclient'],
    version='13.2.2.0',
    url='https://github.com/openstack/stx-integ/tree/master/ceph/python-cephclient/python-cephclient',  # noqa E501
    author='Daniel Badea',
    author_email='daniel.badea@windriver.com',
    description=(
        'A client library in Python for Ceph Mgr RESTful plugin '
        'providing REST API access to the cluster over an SSL-secured '
        'connection. Python API is compatible with the old Python '
        'Ceph client at https://github.com/dmsimard/python-cephclient '
        'that no longer works in Ceph mimic because Ceph REST API '
        'component was removed.'),
    license='Apache-2.0',
    keywords='ceph rest api ceph-rest-api client library',
    install_requires=['ipaddress', 'requests', 'six'],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Development Status :: 1 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python',
        'Topic :: Utilities'
    ])
