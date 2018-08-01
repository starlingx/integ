"""
Copyright (c) 2017 Wind River Systems, Inc.

SPDX-License-Identifier: Apache-2.0

"""

###################
# IMPORTS
###################

import array
import fcntl
import struct
import glob

EXT2_APPEND_FL = 0x00000020
EXT4_EXTENTS_FL = 0x00080000

EXT_IOC_SETFLAGS = 0x40086602
EXT_IOC_GETFLAGS = 0x80086601


def _is_file_append_only(filename):
    buf = array.array('h', [0])
    with open(filename, 'r') as f:
        fcntl.ioctl(f.fileno(), EXT_IOC_GETFLAGS, buf)
    has_append_only = (buf.tolist()[0] & EXT2_APPEND_FL) == EXT2_APPEND_FL
    return has_append_only


def _set_file_attrs(filename, attrs):
    flags = struct.pack('i', attrs)
    with open(filename, 'r') as f:
        fcntl.ioctl(f.fileno(), EXT_IOC_SETFLAGS, flags)


def chattr_add_append_only(filename):
    _set_file_attrs(filename, EXT2_APPEND_FL | EXT4_EXTENTS_FL)


def chattr_remove_append_only(filename):
    _set_file_attrs(filename, EXT4_EXTENTS_FL)


def prerotate():
    for filename in glob.glob("/var/log/bash.log*"):
        if _is_file_append_only(filename):
            chattr_remove_append_only(filename)


def postrotate():
    for filename in glob.glob("/var/log/bash.log*"):
        if not _is_file_append_only(filename):
            chattr_add_append_only(filename)


def ensure_bash_log_locked_down():
    # need the same functionality as postrotate
    postrotate()
