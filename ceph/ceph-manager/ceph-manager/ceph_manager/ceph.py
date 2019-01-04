#
# Copyright (c) 2016-2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from ceph_manager import exception
from ceph_manager.i18n import _LI
# noinspection PyUnresolvedReferences
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


def osd_pool_set_quota(ceph_api, pool_name, max_bytes=0, max_objects=0):
    """Set the quota for an OSD pool_name
    Setting max_bytes or max_objects to 0 will disable that quota param
    :param pool_name:         OSD pool_name
    :param max_bytes:    maximum bytes for OSD pool_name
    :param max_objects:  maximum objects for OSD pool_name
    """

    # Update quota if needed
    prev_quota = osd_pool_get_quota(ceph_api, pool_name)
    if prev_quota["max_bytes"] != max_bytes:
        resp, b = ceph_api.osd_set_pool_quota(pool_name, 'max_bytes',
                                              max_bytes, body='json')
        if resp.ok:
            LOG.info(_LI("Set OSD pool_name quota: "
                         "pool_name={}, max_bytes={}").format(
                             pool_name, max_bytes))
        else:
            e = exception.CephPoolSetQuotaFailure(
                pool=pool_name, name='max_bytes',
                value=max_bytes, reason=resp.reason)
            LOG.error(e)
            raise e
    if prev_quota["max_objects"] != max_objects:
        resp, b = ceph_api.osd_set_pool_quota(pool_name, 'max_objects',
                                              max_objects,
                                              body='json')
        if resp.ok:
            LOG.info(_LI("Set OSD pool_name quota: "
                         "pool_name={}, max_objects={}").format(
                             pool_name, max_objects))
        else:
            e = exception.CephPoolSetQuotaFailure(
                pool=pool_name, name='max_objects',
                value=max_objects, reason=resp.reason)
            LOG.error(e)
            raise e


def osd_pool_get_quota(ceph_api, pool_name):
    resp, quota = ceph_api.osd_get_pool_quota(pool_name, body='json')
    if not resp.ok:
        e = exception.CephPoolGetQuotaFailure(
            pool=pool_name, reason=resp.reason)
        LOG.error(e)
        raise e
    else:
        return {"max_objects": quota["output"]["quota_max_objects"],
                "max_bytes": quota["output"]["quota_max_bytes"]}


def osd_pool_exists(ceph_api, pool_name):
    response, body = ceph_api.osd_pool_get(
        pool_name, "pg_num", body='json')
    if response.ok:
        return True
    return False


def osd_pool_create(ceph_api, pool_name, pg_num, pgp_num):
    # ruleset 0: is the default ruleset if no crushmap is loaded or
    # the ruleset for the backing tier if loaded:
    # Name: storage_tier_ruleset
    ruleset = 0
    response, body = ceph_api.osd_pool_create(
        pool_name, pg_num, pgp_num, pool_type="replicated",
        ruleset=ruleset, body='json')
    if response.ok:
        LOG.info(_LI("Created OSD pool: "
                     "pool_name={}, pg_num={}, pgp_num={}, "
                     "pool_type=replicated, ruleset={}").format(
            pool_name, pg_num, pgp_num, ruleset))
    else:
        e = exception.CephPoolCreateFailure(
            name=pool_name, reason=response.reason)
        LOG.error(e)
        raise e

    # Explicitly assign the ruleset to the pool on creation since it is
    # ignored in the create call
    response, body = ceph_api.osd_set_pool_param(
        pool_name, "crush_ruleset", ruleset, body='json')
    if response.ok:
        LOG.info(_LI("Assigned crush ruleset to OS pool: "
                     "pool_name={}, ruleset={}").format(
            pool_name, ruleset))
    else:
        e = exception.CephPoolRulesetFailure(
            name=pool_name, reason=response.reason)
        LOG.error(e)
        ceph_api.osd_pool_delete(
            pool_name, pool_name,
            sure='--yes-i-really-really-mean-it',
            body='json')
        raise e


def osd_pool_delete(ceph_api, pool_name):
    """Delete an osd pool
    :param pool_name:  pool name
    """
    response, body = ceph_api.osd_pool_delete(
        pool_name, pool_name,
        sure='--yes-i-really-really-mean-it',
        body='json')
    if response.ok:
        LOG.info(_LI("Deleted OSD pool {}").format(pool_name))
    else:
        e = exception.CephPoolDeleteFailure(
            name=pool_name, reason=response.reason)
        LOG.warn(e)
        raise e


def osd_set_pool_param(ceph_api, pool_name, param, value):
    response, body = ceph_api.osd_set_pool_param(
        pool_name, param, value,
        force=None, body='json')
    if response.ok:
        LOG.info('OSD set pool param: '
                 'pool={}, name={}, value={}'.format(
                     pool_name, param, value))
    else:
        raise exception.CephPoolSetParamFailure(
            pool_name=pool_name,
            param=param,
            value=str(value),
            reason=response.reason)
    return response, body


def osd_get_pool_param(ceph_api, pool_name, param):
    response, body = ceph_api.osd_get_pool_param(
        pool_name, param, body='json')
    if response.ok:
        LOG.debug('OSD get pool param: '
                  'pool={}, name={}, value={}'.format(
                      pool_name, param, body['output'][param]))
    else:
        raise exception.CephPoolGetParamFailure(
            pool_name=pool_name,
            param=param,
            reason=response.reason)
    return body['output'][param]
