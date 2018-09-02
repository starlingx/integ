#
# Copyright (c) 2016-2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# noinspection PyUnresolvedReferences
from i18n import _, _LW
# noinspection PyUnresolvedReferences
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class CephManagerException(Exception):
    message = _("An unknown exception occurred.")

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs
        if not message:
            try:
                message = self.message % kwargs
            except TypeError:
                LOG.warn(_LW('Exception in string format operation'))
                for name, value in kwargs.iteritems():
                    LOG.error("%s: %s" % (name, value))
                # at least get the core message out if something happened
                message = self.message
        super(CephManagerException, self).__init__(message)


class CephPoolSetQuotaFailure(CephManagerException):
    message = _("Error seting the OSD pool "
                "quota %(name)s for %(pool)s to %(value)s") \
                + ": %(reason)s"


class CephPoolGetQuotaFailure(CephManagerException):
    message = _("Error geting the OSD pool quota for %(pool)s") \
                + ": %(reason)s"


class CephPoolCreateFailure(CephManagerException):
    message = _("Creating OSD pool %(name)s failed: %(reason)s")


class CephPoolDeleteFailure(CephManagerException):
    message = _("Deleting OSD pool %(name)s failed: %(reason)s")


class CephPoolRulesetFailure(CephManagerException):
    message = _("Assigning crush ruleset to OSD "
                "pool %(name)s failed: %(reason)s")


class CephPoolSetParamFailure(CephManagerException):
    message = _("Cannot set Ceph OSD pool parameter: "
                "pool_name=%(pool_name)s, param=%(param)s, value=%(value)s. "
                "Reason: %(reason)s")


class CephPoolGetParamFailure(CephManagerException):
    message = _("Cannot get Ceph OSD pool parameter: "
                "pool_name=%(pool_name)s, param=%(param)s. "
                "Reason: %(reason)s")


class CephSetKeyFailure(CephManagerException):
    message = _("Error setting the Ceph flag "
                "'%(flag)s' %(extra)s: "
                "response=%(response_status_code)s:%(response_reason)s, "
                "status=%(status)s, output=%(output)s")


class CephApiFailure(CephManagerException):
    message = _("API failure: "
                "call=%(call)s, reason=%(reason)s")
