#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import copy
import contextlib
import functools
import math
import subprocess
import time
import traceback
# noinspection PyUnresolvedReferences
import eventlet
# noinspection PyUnresolvedReferences
from eventlet.semaphore import Semaphore
# noinspection PyUnresolvedReferences
from oslo_log import log as logging
# noinspection PyUnresolvedReferences
from sysinv.conductor.cache_tiering_service_config import ServiceConfig

from i18n import _LI, _LW, _LE

import constants
import exception
import ceph

LOG = logging.getLogger(__name__)
CEPH_POOLS = copy.deepcopy(constants.CEPH_POOLS)

MAX_WAIT = constants.CACHE_FLUSH_MAX_WAIT_OBJ_COUNT_DECREASE_SEC
MIN_WAIT = constants.CACHE_FLUSH_MIN_WAIT_OBJ_COUNT_DECREASE_SEC


class LockOwnership(object):
    def __init__(self, sem):
        self.sem = sem

    @contextlib.contextmanager
    def __call__(self):
        try:
            yield
        finally:
            if self.sem:
                self.sem.release()

    def transfer(self):
        new_lo = LockOwnership(self.sem)
        self.sem = None
        return new_lo


class Lock(object):

    def __init__(self):
        self.sem = Semaphore(value=1)

    def try_lock(self):
        result = self.sem.acquire(blocking=False)
        if result:
            return LockOwnership(self.sem)


class CacheTiering(object):

    def __init__(self, service):
        self.service = service
        self.lock = Lock()
        # will be unlocked by set_initial_config()
        self._init_config_lock = self.lock.try_lock()
        self.config = None
        self.config_desired = None
        self.config_applied = None
        self.target_max_bytes = {}

    def set_initial_config(self, config):
        with self._init_config_lock():
            LOG.info("Setting Ceph cache tiering initial configuration")
            self.config = ServiceConfig.from_dict(
                config.get(constants.CACHE_TIERING, {})) or \
                ServiceConfig()
            self.config_desired = ServiceConfig.from_dict(
                config.get(constants.CACHE_TIERING_DESIRED, {})) or \
                ServiceConfig()
            self.config_applied = ServiceConfig.from_dict(
                config.get(constants.CACHE_TIERING_APPLIED, {})) or \
                ServiceConfig()
            if self.config_desired:
                LOG.debug("set_initial_config config_desired %s " %
                          self.config_desired.to_dict())
            if self.config_applied:
                LOG.debug("set_initial_config config_applied %s " %
                          self.config_applied.to_dict())

            # Check that previous caching tier operation completed
            # successfully or perform recovery
            if (self.config_desired and
                self.config_applied and
                (self.config_desired.cache_enabled !=
                    self.config_applied.cache_enabled)):
                if self.config_desired.cache_enabled:
                    self.enable_cache(self.config_desired.to_dict(),
                                      self.config_applied.to_dict(),
                                      self._init_config_lock.transfer())
                else:
                    self.disable_cache(self.config_desired.to_dict(),
                                       self.config_applied.to_dict(),
                                       self._init_config_lock.transfer())

    def is_locked(self):
        lock_ownership = self.lock.try_lock()
        if not lock_ownership:
            return True
        with lock_ownership():
            return False

    def update_pools_info(self):
        global CEPH_POOLS
        cfg = self.service.sysinv_conductor.call(
            {}, 'get_ceph_pools_config')
        CEPH_POOLS = copy.deepcopy(cfg)
        LOG.info(_LI("update_pools_info: pools: {}").format(CEPH_POOLS))

    def enable_cache(self, new_config, applied_config, lock_ownership=None):
        new_config = ServiceConfig.from_dict(new_config)
        applied_config = ServiceConfig.from_dict(applied_config)
        if not lock_ownership:
            lock_ownership = self.lock.try_lock()
            if not lock_ownership:
                raise exception.CephCacheEnableFailure()
        with lock_ownership():
            eventlet.spawn(self.do_enable_cache,
                           new_config, applied_config,
                           lock_ownership.transfer())

    def do_enable_cache(self, new_config, applied_config, lock_ownership):
        LOG.info(_LI("cache_tiering_enable_cache: "
                     "new_config={}, applied_config={}").format(
                        new_config.to_dict(), applied_config.to_dict()))
        _unwind_actions = []
        with lock_ownership():
            success = False
            _exception = None
            try:
                self.config_desired.cache_enabled = True
                self.update_pools_info()
                for pool in CEPH_POOLS:
                    if (pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL or
                       pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER):
                        object_pool_name = \
                          self.service.monitor._get_object_pool_name()
                        pool['pool_name'] = object_pool_name

                    self.cache_pool_create(pool)
                    _unwind_actions.append(
                        functools.partial(self.cache_pool_delete, pool))
                for pool in CEPH_POOLS:
                    if (pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL or
                       pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER):
                        object_pool_name = \
                            self.service.monitor._get_object_pool_name()
                        pool['pool_name'] = object_pool_name

                    self.cache_tier_add(pool)
                    _unwind_actions.append(
                        functools.partial(self.cache_tier_remove, pool))
                for pool in CEPH_POOLS:
                    if (pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL or
                       pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER):
                        object_pool_name = \
                          self.service.monitor._get_object_pool_name()
                        pool['pool_name'] = object_pool_name

                    self.cache_mode_set(pool, 'writeback')
                    self.cache_pool_set_config(pool, new_config)
                    self.cache_overlay_create(pool)
                success = True
            except Exception as e:
                LOG.error(_LE('Failed to enable cache: reason=%s') %
                          traceback.format_exc())
                for action in reversed(_unwind_actions):
                    try:
                        action()
                    except Exception:
                        LOG.warn(_LW('Failed cache enable '
                                     'unwind action: reason=%s') %
                                 traceback.format_exc())
                success = False
                _exception = str(e)
            finally:
                self.service.monitor.monitor_check_cache_tier(success)
                if success:
                    self.config_applied.cache_enabled = True
                self.service.sysinv_conductor.call(
                    {}, 'cache_tiering_enable_cache_complete',
                    success=success, exception=_exception,
                    new_config=new_config.to_dict(),
                    applied_config=applied_config.to_dict())
                # Run first update of periodic target_max_bytes
                self.update_cache_target_max_bytes()

    @contextlib.contextmanager
    def ignore_ceph_failure(self):
        try:
            yield
        except exception.CephManagerException:
            pass

    def disable_cache(self, new_config, applied_config, lock_ownership=None):
        new_config = ServiceConfig.from_dict(new_config)
        applied_config = ServiceConfig.from_dict(applied_config)
        if not lock_ownership:
            lock_ownership = self.lock.try_lock()
            if not lock_ownership:
                raise exception.CephCacheDisableFailure()
        with lock_ownership():
            eventlet.spawn(self.do_disable_cache,
                           new_config, applied_config,
                           lock_ownership.transfer())

    def do_disable_cache(self, new_config, applied_config, lock_ownership):
        LOG.info(_LI("cache_tiering_disable_cache: "
                     "new_config={}, applied_config={}").format(
                        new_config, applied_config))
        with lock_ownership():
            success = False
            _exception = None
            try:
                self.config_desired.cache_enabled = False
                for pool in CEPH_POOLS:
                    if (pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL or
                       pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER):
                        object_pool_name = \
                          self.service.monitor._get_object_pool_name()
                        pool['pool_name'] = object_pool_name

                    with self.ignore_ceph_failure():
                        self.cache_mode_set(
                            pool, 'forward')

                for pool in CEPH_POOLS:
                    if (pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL or
                       pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER):
                        object_pool_name = \
                          self.service.monitor._get_object_pool_name()
                        pool['pool_name'] = object_pool_name

                    retries_left = 3
                    while True:
                        try:
                            self.cache_flush(pool)
                            break
                        except exception.CephCacheFlushFailure:
                            retries_left -= 1
                            if not retries_left:
                                # give up
                                break
                            else:
                                time.sleep(1)
                for pool in CEPH_POOLS:
                    if (pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL or
                       pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER):
                        object_pool_name = \
                          self.service.monitor._get_object_pool_name()
                        pool['pool_name'] = object_pool_name

                    with self.ignore_ceph_failure():
                        self.cache_overlay_delete(pool)
                        self.cache_tier_remove(pool)
                for pool in CEPH_POOLS:
                    if (pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL or
                       pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER):
                        object_pool_name = \
                          self.service.monitor._get_object_pool_name()
                        pool['pool_name'] = object_pool_name

                    with self.ignore_ceph_failure():
                        self.cache_pool_delete(pool)
                success = True
            except Exception as e:
                LOG.warn(_LE('Failed to disable cache: reason=%s') %
                         traceback.format_exc())
                _exception = str(e)
            finally:
                self.service.monitor.monitor_check_cache_tier(False)
                if success:
                    self.config_desired.cache_enabled = False
                    self.config_applied.cache_enabled = False
                self.service.sysinv_conductor.call(
                    {}, 'cache_tiering_disable_cache_complete',
                    success=success, exception=_exception,
                    new_config=new_config.to_dict(),
                    applied_config=applied_config.to_dict())

    def get_pool_pg_num(self, pool_name):
        return self.service.sysinv_conductor.call(
                                    {}, 'get_pool_pg_num',
                                    pool_name=pool_name)

    def cache_pool_create(self, pool):
        backing_pool = pool['pool_name']
        cache_pool = backing_pool + '-cache'
        pg_num = self.get_pool_pg_num(cache_pool)
        if not ceph.osd_pool_exists(self.service.ceph_api, cache_pool):
            ceph.osd_pool_create(
                self.service.ceph_api, cache_pool,
                pg_num, pg_num)

    def cache_pool_delete(self, pool):
        cache_pool = pool['pool_name'] + '-cache'
        ceph.osd_pool_delete(
            self.service.ceph_api, cache_pool)

    def cache_tier_add(self, pool):
        backing_pool = pool['pool_name']
        cache_pool = backing_pool + '-cache'
        response, body = self.service.ceph_api.osd_tier_add(
            backing_pool, cache_pool,
            force_nonempty="--force-nonempty",
            body='json')
        if response.ok:
            LOG.info(_LI("Added OSD tier: "
                         "backing_pool={}, cache_pool={}").format(
                            backing_pool, cache_pool))
        else:
            e = exception.CephPoolAddTierFailure(
                backing_pool=backing_pool,
                cache_pool=cache_pool,
                response_status_code=response.status_code,
                response_reason=response.reason,
                status=body.get('status'),
                output=body.get('output'))
            LOG.warn(e)
            raise e

    def cache_tier_remove(self, pool):
        backing_pool = pool['pool_name']
        cache_pool = backing_pool + '-cache'
        response, body = self.service.ceph_api.osd_tier_remove(
            backing_pool, cache_pool, body='json')
        if response.ok:
            LOG.info(_LI("Removed OSD tier: "
                         "backing_pool={}, cache_pool={}").format(
                            backing_pool, cache_pool))
        else:
            e = exception.CephPoolRemoveTierFailure(
                backing_pool=backing_pool,
                cache_pool=cache_pool,
                response_status_code=response.status_code,
                response_reason=response.reason,
                status=body.get('status'),
                output=body.get('output'))
            LOG.warn(e)
            raise e

    def cache_mode_set(self, pool, mode):
        backing_pool = pool['pool_name']
        cache_pool = backing_pool + '-cache'
        response, body = self.service.ceph_api.osd_tier_cachemode(
            cache_pool, mode, body='json')
        if response.ok:
            LOG.info(_LI("Set OSD tier cache mode: "
                         "cache_pool={}, mode={}").format(cache_pool, mode))
        else:
            e = exception.CephCacheSetModeFailure(
                cache_pool=cache_pool,
                mode=mode,
                response_status_code=response.status_code,
                response_reason=response.reason,
                status=body.get('status'),
                output=body.get('output'))
            LOG.warn(e)
            raise e

    def cache_pool_set_config(self, pool, config):
        for name, value in config.params.iteritems():
            self.cache_pool_set_param(pool, name, value)

    def cache_pool_set_param(self, pool, name, value):
        backing_pool = pool['pool_name']
        cache_pool = backing_pool + '-cache'
        ceph.osd_set_pool_param(
            self.service.ceph_api, cache_pool, name, value)

    def cache_overlay_create(self, pool):
        backing_pool = pool['pool_name']
        cache_pool = backing_pool + '-cache'
        response, body = self.service.ceph_api.osd_tier_set_overlay(
            backing_pool, cache_pool, body='json')
        if response.ok:
            LOG.info(_LI("Set OSD tier overlay: "
                         "backing_pool={}, cache_pool={}").format(
                            backing_pool, cache_pool))
        else:
            e = exception.CephCacheCreateOverlayFailure(
                backing_pool=backing_pool,
                cache_pool=cache_pool,
                response_status_code=response.status_code,
                response_reason=response.reason,
                status=body.get('status'),
                output=body.get('output'))
            LOG.warn(e)
            raise e

    def cache_overlay_delete(self, pool):
        backing_pool = pool['pool_name']
        cache_pool = pool['pool_name']
        response, body = self.service.ceph_api.osd_tier_remove_overlay(
            backing_pool, body='json')
        if response.ok:
            LOG.info(_LI("Removed OSD tier overlay: "
                         "backing_pool={}").format(backing_pool))
        else:
            e = exception.CephCacheDeleteOverlayFailure(
                backing_pool=backing_pool,
                cache_pool=cache_pool,
                response_status_code=response.status_code,
                response_reason=response.reason,
                status=body.get('status'),
                output=body.get('output'))
            LOG.warn(e)
            raise e

    @staticmethod
    def rados_cache_flush_evict_all(pool):
        backing_pool = pool['pool_name']
        cache_pool = backing_pool + '-cache'
        try:
            subprocess.check_call(
                ['/usr/bin/rados', '-p', cache_pool, 'cache-flush-evict-all'])
            LOG.info(_LI("Flushed OSD cache pool:"
                         "cache_pool={}").format(cache_pool))
        except subprocess.CalledProcessError as e:
            _e = exception.CephCacheFlushFailure(
                cache_pool=cache_pool,
                return_code=str(e.returncode),
                cmd=" ".join(e.cmd),
                output=e.output)
            LOG.warn(_e)
            raise _e

    def cache_flush(self, pool):
        backing_pool = pool['pool_name']
        cache_pool = backing_pool + '-cache'
        try:
            # set target_max_objects to a small value to force evacuation of
            # objects from cache before we use rados cache-flush-evict-all
            # WARNING: assuming cache_pool will be deleted after flush so
            # we don't have to save/restore the value of target_max_objects
            #
            self.cache_pool_set_param(pool, 'target_max_objects', 1)
            prev_object_count = None
            wait_interval = MIN_WAIT
            while True:
                response, body = self.service.ceph_api.df(body='json')
                if not response.ok:
                    LOG.warn(_LW(
                        "Failed to retrieve cluster free space stats: "
                        "status_code=%d, reason=%s") % (
                            response.status_code, response.reason))
                    break
                stats = None
                for s in body['output']['pools']:
                    if s['name'] == cache_pool:
                        stats = s['stats']
                        break
                if not stats:
                    LOG.warn(_LW("Missing pool free space stats: "
                                 "cache_pool=%s") % cache_pool)
                    break
                object_count = stats['objects']
                if object_count < constants.CACHE_FLUSH_OBJECTS_THRESHOLD:
                    break
                if prev_object_count is not None:
                    delta_objects = object_count - prev_object_count
                    if delta_objects > 0:
                        LOG.warn(_LW("Unexpected increase in number "
                                     "of objects in cache pool: "
                                     "cache_pool=%s, prev_object_count=%d, "
                                     "object_count=%d") % (
                                         cache_pool, prev_object_count,
                                         object_count))
                        break
                    if delta_objects == 0:
                        wait_interval *= 2
                        if wait_interval > MAX_WAIT:
                            LOG.warn(_LW(
                                "Cache pool number of objects did not "
                                "decrease: cache_pool=%s, object_count=%d, "
                                "wait_interval=%d") % (
                                cache_pool, object_count, wait_interval))
                            break
                    else:
                        wait_interval = MIN_WAIT
                time.sleep(wait_interval)
                prev_object_count = object_count
        except exception.CephPoolSetParamFailure as e:
            LOG.warn(e)
        finally:
            self.rados_cache_flush_evict_all(pool)

    def update_cache_target_max_bytes(self):
        "Dynamically compute target_max_bytes of caching pools"

        # Only compute if cache tiering is enabled
        if self.config_applied and self.config_desired:
            if (not self.config_desired.cache_enabled or
                    not self.config_applied.cache_enabled):
                LOG.debug("Cache tiering disabled, no need to update "
                          "target_max_bytes.")
                return
        LOG.debug("Updating target_max_bytes")

        # Get available space
        response, body = self.service.ceph_api.osd_df(body='json',
                                                      output_method='tree')
        if not response.ok:
            LOG.warn(_LW(
                "Failed to retrieve cluster free space stats: "
                "status_code=%d, reason=%s") % (
                    response.status_code, response.reason))
            return

        storage_tier_size = 0
        cache_tier_size = 0

        replication = constants.CEPH_REPLICATION_FACTOR
        for node in body['output']['nodes']:
            if node['name'] == 'storage-tier':
                storage_tier_size = node['kb']*1024/replication
            elif node['name'] == 'cache-tier':
                cache_tier_size = node['kb']*1024/replication

        if storage_tier_size == 0 or cache_tier_size == 0:
            LOG.info("Failed to get cluster size "
                     "(storage_tier_size=%s, cache_tier_size=%s),"
                     "retrying on next cycle" %
                     (storage_tier_size, cache_tier_size))
            return

        # Get available pools
        response, body = self.service.ceph_api.osd_lspools(body='json')
        if not response.ok:
            LOG.warn(_LW(
                "Failed to retrieve available pools: "
                "status_code=%d, reason=%s") % (
                    response.status_code, response.reason))
            return
        pools = [p['poolname'] for p in body['output']]

        # Separate backing from caching for easy iteration
        backing_pools = []
        caching_pools = []
        for p in pools:
            if p.endswith('-cache'):
                caching_pools.append(p)
            else:
                backing_pools.append(p)
        LOG.debug("Pools: caching: %s, backing: %s" % (caching_pools,
                                                       backing_pools))

        if not len(caching_pools):
            # We do not have caching pools created yet
            return

        # Get quota from backing pools that are cached
        stats = {}
        for p in caching_pools:
            backing_name = p.replace('-cache', '')
            stats[backing_name] = {}
            try:
                quota = ceph.osd_pool_get_quota(self.service.ceph_api,
                                                backing_name)
            except exception.CephPoolGetQuotaFailure as e:
                LOG.warn(_LW(
                    "Failed to retrieve quota: "
                    "exception: %s") % str(e))
                return
            stats[backing_name]['quota'] = quota['max_bytes']
            stats[backing_name]['quota_pt'] = (quota['max_bytes']*100.0 /
                                               storage_tier_size)
            LOG.debug("Quota for pool: %s "
                      "is: %s B representing %s pt" %
                      (backing_name,
                       quota['max_bytes'],
                       stats[backing_name]['quota_pt']))

        # target_max_bytes logic:
        # - For computing target_max_bytes cache_tier_size must be equal than
        #   the sum of target_max_bytes of each caching pool
        # - target_max_bytes for each caching pool is computed as the
        #   percentage of quota in corresponding backing pool
        # - the caching tiers has to work at full capacity, so if the sum of
        #   all quotas in the backing tier is different than 100% we need to
        #   normalize
        # - if the quota is zero for any pool we add CACHE_TIERING_MIN_QUOTA
        #   by default *after* normalization so that we have real minimum

        # We compute the real percentage that need to be normalized after
        # ensuring that we have CACHE_TIERING_MIN_QUOTA for each pool with
        # a quota of 0
        real_100pt = 90.0  # we start from max and decrease it for each 0 pool
        # Note: We must avoid reaching 100% at all costs! and
        # cache_target_full_ratio, the Ceph parameter that is supposed to
        # protect the cluster against this does not work in Ceph v0.94.6!
        # Therefore a value of 90% is better suited for this
        for p in caching_pools:
            backing_name = p.replace('-cache', '')
            if stats[backing_name]['quota_pt'] == 0:
                real_100pt -= constants.CACHE_TIERING_MIN_QUOTA
            LOG.debug("Quota before normalization for %s is: %s pt" %
                      (p, stats[backing_name]['quota_pt']))

        # Compute total percentage of quotas for all backing pools.
        # Should be 100% if correctly configured
        total_quota_pt = 0
        for p in caching_pools:
                backing_name = p.replace('-cache', '')
                total_quota_pt += stats[backing_name]['quota_pt']
        LOG.debug("Total quota pt is: %s" % total_quota_pt)

        # Normalize quota pt to 100% (or real_100pt)
        if total_quota_pt != 0:  # to avoid divide by zero
            for p in caching_pools:
                backing_name = p.replace('-cache', '')
                stats[backing_name]['quota_pt'] = \
                    (stats[backing_name]['quota_pt'] *
                     (real_100pt / total_quota_pt))

        # Do not allow quota to be 0 for any pool
        total = 0
        for p in caching_pools:
            backing_name = p.replace('-cache', '')
            if stats[backing_name]['quota_pt'] == 0:
                stats[backing_name]['quota_pt'] = \
                    constants.CACHE_TIERING_MIN_QUOTA
            total += stats[backing_name]['quota_pt']
            LOG.debug("Quota after normalization for %s is: %s:" %
                      (p, stats[backing_name]['quota_pt']))

        if total > 100:
            # Supplementary protection, we really have to avoid going above
            # 100%. Note that real_100pt is less than 100% but we still got
            # more than 100!
            LOG.warn("Total sum of quotas should not go above 100% "
                     "but is: %s, recalculating in next cycle" % total)
            return
        LOG.debug("Total sum of quotas is %s pt" % total)

        # Get current target_max_bytes. We cache it to reduce requests
        # to ceph-rest-api. We are the ones changing it, so not an issue.
        for p in caching_pools:
            if p not in self.target_max_bytes:
                try:
                    value = ceph.osd_get_pool_param(self.service.ceph_api, p,
                                                    constants.TARGET_MAX_BYTES)
                except exception.CephPoolGetParamFailure as e:
                    LOG.warn(e)
                    return
                self.target_max_bytes[p] = value
        LOG.debug("Existing target_max_bytes got from "
                  "Ceph: %s" % self.target_max_bytes)

        # Set TARGET_MAX_BYTES
        LOG.debug("storage_tier_size: %s "
                  "cache_tier_size: %s" % (storage_tier_size,
                                           cache_tier_size))
        for p in caching_pools:
            backing_name = p.replace('-cache', '')
            s = stats[backing_name]
            target_max_bytes = math.floor(s['quota_pt'] * cache_tier_size /
                                          100.0)
            target_max_bytes = int(target_max_bytes)
            LOG.debug("New Target max bytes of pool: %s is: %s B" % (
                        p, target_max_bytes))

            # Set the new target_max_bytes only if it changed
            if self.target_max_bytes.get(p) == target_max_bytes:
                LOG.debug("Target max bytes of pool: %s "
                          "is already updated" % p)
                continue
            try:
                ceph.osd_set_pool_param(self.service.ceph_api, p,
                                        constants.TARGET_MAX_BYTES,
                                        target_max_bytes)
                self.target_max_bytes[p] = target_max_bytes
            except exception.CephPoolSetParamFailure as e:
                LOG.warn(e)
                continue
        return
