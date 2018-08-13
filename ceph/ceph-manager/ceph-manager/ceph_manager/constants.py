#
# Copyright (c) 2016-2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from i18n import _
# noinspection PyUnresolvedReferences
from sysinv.common import constants as sysinv_constants

CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL = \
    sysinv_constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL
CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER = \
    sysinv_constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER
CEPH_POOLS = sysinv_constants.BACKING_POOLS
CEPH_REPLICATION_FACTOR = sysinv_constants.CEPH_REPLICATION_FACTOR_DEFAULT
SERVICE_PARAM_CEPH_CACHE_HIT_SET_TYPE_BLOOM = \
    sysinv_constants.SERVICE_PARAM_CEPH_CACHE_HIT_SET_TYPE_BLOOM
CACHE_TIERING_DEFAULTS = sysinv_constants.CACHE_TIERING_DEFAULTS
TARGET_MAX_BYTES = \
    sysinv_constants.SERVICE_PARAM_CEPH_CACHE_TIER_TARGET_MAX_BYTES

# Cache tiering section shortener
CACHE_TIERING = \
    sysinv_constants.SERVICE_PARAM_SECTION_CEPH_CACHE_TIER
CACHE_TIERING_DESIRED = \
    sysinv_constants.SERVICE_PARAM_SECTION_CEPH_CACHE_TIER_DESIRED
CACHE_TIERING_APPLIED = \
    sysinv_constants.SERVICE_PARAM_SECTION_CEPH_CACHE_TIER_APPLIED
CACHE_TIERING_SECTIONS = \
    [CACHE_TIERING, CACHE_TIERING_DESIRED, CACHE_TIERING_APPLIED]

# Cache flush parameters
CACHE_FLUSH_OBJECTS_THRESHOLD = 1000
CACHE_FLUSH_MIN_WAIT_OBJ_COUNT_DECREASE_SEC = 1
CACHE_FLUSH_MAX_WAIT_OBJ_COUNT_DECREASE_SEC = 128

CACHE_TIERING_MIN_QUOTA = 5

FM_ALARM_REASON_MAX_SIZE = 256

# TODO this will later change based on parsed health
# clock skew is vm malfunction, mon or osd is equipment mal
ALARM_CAUSE = 'equipment-malfunction'
ALARM_TYPE = 'equipment'

# Ceph health check interval (in seconds)
CEPH_HEALTH_CHECK_INTERVAL = 60

# Ceph health statuses
CEPH_HEALTH_OK = 'HEALTH_OK'
CEPH_HEALTH_WARN = 'HEALTH_WARN'
CEPH_HEALTH_ERR = 'HEALTH_ERR'
CEPH_HEALTH_DOWN = 'CEPH_DOWN'

# Statuses not reported by Ceph
CEPH_STATUS_CUSTOM = [CEPH_HEALTH_DOWN]

SEVERITY = {CEPH_HEALTH_DOWN: 'critical',
            CEPH_HEALTH_ERR: 'critical',
            CEPH_HEALTH_WARN: 'warning'}

SERVICE_AFFECTING = {CEPH_HEALTH_DOWN: True,
                     CEPH_HEALTH_ERR: True,
                     CEPH_HEALTH_WARN: False}

# TODO this will later change based on parsed health
ALARM_REASON_NO_OSD = _('no OSDs')
ALARM_REASON_OSDS_DOWN = _('OSDs are down')
ALARM_REASON_OSDS_OUT = _('OSDs are out')
ALARM_REASON_OSDS_DOWN_OUT = _('OSDs are down/out')
ALARM_REASON_PEER_HOST_DOWN = _('peer host down')

REPAIR_ACTION_MAJOR_CRITICAL_ALARM = _(
    'Ensure storage hosts from replication group are unlocked and available.'
    'Check if OSDs of each storage host are up and running.'
    'If problem persists, contact next level of support.')
REPAIR_ACTION = _('If problem persists, contact next level of support.')

SYSINV_CONDUCTOR_TOPIC = 'sysinv.conductor_manager'
CEPH_MANAGER_TOPIC = 'sysinv.ceph_manager'
SYSINV_CONFIG_FILE = '/etc/sysinv/sysinv.conf'

# Titanium Cloud version strings
TITANIUM_SERVER_VERSION_16_10 = '16.10'

CEPH_HEALTH_WARN_REQUIRE_JEWEL_OSDS_NOT_SET = (
    "all OSDs are running jewel or later but the "
    "'require_jewel_osds' osdmap flag is not set")

UPGRADE_COMPLETED = \
    sysinv_constants.UPGRADE_COMPLETED
UPGRADE_ABORTING = \
    sysinv_constants.UPGRADE_ABORTING
UPGRADE_ABORT_COMPLETING = \
    sysinv_constants.UPGRADE_ABORT_COMPLETING
UPGRADE_ABORTING_ROLLBACK = \
    sysinv_constants.UPGRADE_ABORTING_ROLLBACK

CEPH_FLAG_REQUIRE_JEWEL_OSDS = 'require_jewel_osds'

# Tiers
CEPH_CRUSH_TIER_SUFFIX = sysinv_constants.CEPH_CRUSH_TIER_SUFFIX
SB_TIER_TYPE_CEPH = sysinv_constants.SB_TIER_TYPE_CEPH
SB_TIER_SUPPORTED = sysinv_constants.SB_TIER_SUPPORTED
SB_TIER_DEFAULT_NAMES = sysinv_constants.SB_TIER_DEFAULT_NAMES
SB_TIER_CEPH_POOLS = sysinv_constants.SB_TIER_CEPH_POOLS
