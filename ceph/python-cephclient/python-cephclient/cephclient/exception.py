#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


class CephClientException(Exception):
    message = "generic ceph client exception"

    def __init__(self, *args, **kwargs):
        if "message" not in kwargs:
            try:
                message = self.message.format(*args, **kwargs)
            except Exception:   # noqa
                message = '{}, args:{}, kwargs: {}'.format(
                    self.message, args, kwargs)
        else:
            message = kwargs["message"]
        super(CephClientException, self).__init__(message)


class CephMonRestfulListKeysError(CephClientException):
    message = "Failed to get ceph-mgr restful plugin keys. {}"


class CephMonRestfulJsonError(CephClientException):
    message = "Failed to decode ceph-mgr restful plugin JSON response: {}"


class CephMonRestfulMissingUserCredentials(CephClientException):
    message = "Failed to get ceph-mgr restful plugin credentials for user: {}"


class CephMgrDumpError(CephClientException):
    message = "Failed to get ceph manager info. {}"


class CephMgrJsonError(CephClientException):
    message = "Failed to decode ceph manager JSON response: {}"


class CephMgrMissingRestfulService(CephClientException):
    message = "Missing restful service. Available services: {}"


class CephClientFormatNotSupported(CephClientException):
    message = "Command '{prefix}' does not support request format '{format}'"


class CephClientResponseFormatNotImplemented(CephClientException):
    message = ("Can't decode response. Support for '{format}' format "
               "is not implemented. Response: {reason}")


class CephClientFunctionNotImplemented(CephClientException):
    message = "Function '{name}' is not implemented"


class CephClientInvalidChoice(CephClientException):
    message = ("Function '{function}' does not support option "
               "{option}='{value}'. Supported values are: {supported}")


class CephClientTypeError(CephClientException):
    message = ("Expecting option '{name}' of type {expected}. "
               "Got {actual} instead")


class CephClientValueOutOfBounds(CephClientException):
    message = ("Argument '{name}' should be within range: {min} .. {max} "
               ". Got value '{actual}' instead")


class CephClientInvalidPgid(CephClientException):
    message = ("Argument '{name}' is not a valid Ceph PG id. Expected "
               "n.xxx where n is an int > 0, xxx is a hex number > 0. "
               "Got value '{actual}' instead")


class CephClientInvalidIPAddr(CephClientException):
    message = ("Argument '{name}' should be a valid IPv4 or IPv6 address. "
               "Got value '{actual}' instead")


class CephClientInvalidOsdIdValue(CephClientException):
    message = ("Invalid OSD ID value '{osdid}'. Should start with 'osd.'")


class CephClientInvalidOsdIdType(CephClientException):
    message = ("Invalid OSD ID type for '{osdid}'. "
               "Expected integer or 'osd.NNN'")


class CephClientNoSuchUser(CephClientException):
    message = ("No such user '{user}'.")


class CephClientIncorrectPassword(CephClientException):
    message = ("Incorrect password for user '{user}'.")
