#
# Copyright (c) 2013-2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import time

# noinspection PyUnresolvedReferences
from fm_api import fm_api
# noinspection PyUnresolvedReferences
from fm_api import constants as fm_constants
# noinspection PyUnresolvedReferences
from oslo_log import log as logging

from sysinv.conductor.cache_tiering_service_config import ServiceConfig

# noinspection PyProtectedMember
from i18n import _, _LI, _LW, _LE

import constants
import exception

LOG = logging.getLogger(__name__)


# When upgrading from 16.10 to 17.x Ceph goes from Hammer release
# to Jewel release. After all storage nodes are upgraded to 17.x
# the cluster is in HEALTH_WARN until administrator explicitly
# enables require_jewel_osds flag - which signals Ceph that it
# can safely transition from Hammer to Jewel
#
# This class is needed only when upgrading from 16.10 to 17.x
# TODO: remove it after 1st 17.x release
#
class HandleUpgradesMixin(object):

    def __init__(self, service):
        self.service = service
        self.surpress_require_jewel_osds_warning = False

    def setup(self, config):
        self._set_upgrade(self.service.retry_get_software_upgrade_status())

    def _set_upgrade(self, upgrade):
        state = upgrade.get('state')
        from_version = upgrade.get('from_version')
        if (state
                and state != constants.UPGRADE_COMPLETED
                and from_version == constants.TITANIUM_SERVER_VERSION_16_10):
            LOG.info(_LI("Surpress require_jewel_osds health warning"))
            self.surpress_require_jewel_osds_warning = True

    def set_flag_require_jewel_osds(self):
        try:
            response, body = self.service.ceph_api.osd_set_key(
                constants.CEPH_FLAG_REQUIRE_JEWEL_OSDS,
                body='json')
            LOG.info(_LI("Set require_jewel_osds flag"))
        except IOError as e:
            raise exception.CephApiFailure(
                call="osd_set_key",
                reason=e.message)
        else:
            if not response.ok:
                raise exception.CephSetKeyFailure(
                    flag=constants.CEPH_FLAG_REQUIRE_JEWEL_OSDS,
                    extra=_("needed to complete upgrade to Jewel"),
                    response_status_code=response.status_code,
                    response_reason=response.reason,
                    status=body.get('status'),
                    output=body.get('output'))

    def filter_health_status(self, health):
        health = self.auto_heal(health)
        # filter out require_jewel_osds warning
        #
        if not self.surpress_require_jewel_osds_warning:
            return health
        if health['health'] != constants.CEPH_HEALTH_WARN:
            return health
        if (constants.CEPH_HEALTH_WARN_REQUIRE_JEWEL_OSDS_NOT_SET
                not in health['detail']):
            return health
        return self._remove_require_jewel_osds_warning(health)

    def _remove_require_jewel_osds_warning(self, health):
        reasons_list = []
        for reason in health['detail'].split(';'):
            reason = reason.strip()
            if len(reason) == 0:
                continue
            if constants.CEPH_HEALTH_WARN_REQUIRE_JEWEL_OSDS_NOT_SET in reason:
                continue
            reasons_list.append(reason)
        if len(reasons_list) == 0:
            health = {
                'health': constants.CEPH_HEALTH_OK,
                'detail': ''}
        else:
            health['detail'] = '; '.join(reasons_list)
        return health

    def auto_heal(self, health):
        if (health['health'] == constants.CEPH_HEALTH_WARN
                and (constants.CEPH_HEALTH_WARN_REQUIRE_JEWEL_OSDS_NOT_SET
                     in health['detail'])):
            try:
                upgrade = self.service.get_software_upgrade_status()
            except Exception as ex:
                LOG.warn(_LW(
                    "Getting software upgrade status failed "
                    "with: %s. Skip auto-heal attempt "
                    "(will retry on next ceph status poll).") % str(ex))
                return
            state = upgrade.get('state')
            # surpress require_jewel_osds in case upgrade is
            # in progress but not completed or aborting
            if (not self.surpress_require_jewel_osds_warning
                    and (upgrade.get('from_version')
                         == constants.TITANIUM_SERVER_VERSION_16_10)
                    and state not in [
                        None,
                        constants.UPGRADE_COMPLETED,
                        constants.UPGRADE_ABORTING,
                        constants.UPGRADE_ABORT_COMPLETING,
                        constants.UPGRADE_ABORTING_ROLLBACK]):
                LOG.info(_LI("Surpress require_jewel_osds health warning"))
                self.surpress_require_jewel_osds_warning = True
            # set require_jewel_osds in case upgrade is
            # not in progress or completed
            if (state in [None, constants.UPGRADE_COMPLETED]):
                LOG.warn(_LW(
                    "No upgrade in progress or update completed "
                    "and require_jewel_osds health warning raised. "
                    "Set require_jewel_osds flag."))
                self.set_flag_require_jewel_osds()
                health = self._remove_require_jewel_osds_warning(health)
                LOG.info(_LI("Unsurpress require_jewel_osds health warning"))
                self.surpress_require_jewel_osds_warning = False
            # unsurpress require_jewel_osds in case upgrade
            # is aborting
            if (self.surpress_require_jewel_osds_warning
                    and state in [
                        constants.UPGRADE_ABORTING,
                        constants.UPGRADE_ABORT_COMPLETING,
                        constants.UPGRADE_ABORTING_ROLLBACK]):
                LOG.info(_LI("Unsurpress require_jewel_osds health warning"))
                self.surpress_require_jewel_osds_warning = False
        return health


class Monitor(HandleUpgradesMixin):

    def __init__(self, service):
        self.service = service
        self.current_ceph_health = ""
        self.cache_enabled = False
        self.tiers_size = {}
        self.known_object_pool_name = None
        self.primary_tier_name = constants.SB_TIER_DEFAULT_NAMES[
            constants.SB_TIER_TYPE_CEPH] + constants.CEPH_CRUSH_TIER_SUFFIX
        self.cluster_is_up = False
        super(Monitor, self).__init__(service)

    def setup(self, config):
        self.set_caching_tier_config(config)
        super(Monitor, self).setup(config)

    def set_caching_tier_config(self, config):
        conf = ServiceConfig().from_dict(
            config.get(constants.CACHE_TIERING_APPLIED))
        if conf:
            self.cache_enabled = conf.cache_enabled

    def monitor_check_cache_tier(self, enable_flag):
        LOG.info(_LI("monitor_check_cache_tier: "
                     "enable_flag={}".format(enable_flag)))
        self.cache_enabled = enable_flag

    def run(self):
        # Wait until Ceph cluster is up and we can get the fsid
        while True:
            self.ceph_get_fsid()
            if self.service.entity_instance_id:
                break
            time.sleep(constants.CEPH_HEALTH_CHECK_INTERVAL)

        # Start monitoring ceph status
        while True:
            self.ceph_poll_status()
            self.ceph_poll_quotas()
            time.sleep(constants.CEPH_HEALTH_CHECK_INTERVAL)

    def ceph_get_fsid(self):
        # Check whether an alarm has already been raised
        self._get_current_alarms()
        if self.current_health_alarm:
            LOG.info(_LI("Current alarm: %s") %
                     str(self.current_health_alarm.__dict__))

        fsid = self._get_fsid()
        if not fsid:
            # Raise alarm - it will not have an entity_instance_id
            self._report_fault({'health': constants.CEPH_HEALTH_DOWN,
                                'detail': 'Ceph cluster is down.'},
                               fm_constants.FM_ALARM_ID_STORAGE_CEPH)
        else:
            # Clear alarm with no entity_instance_id
            self._clear_fault(fm_constants.FM_ALARM_ID_STORAGE_CEPH)
            self.service.entity_instance_id = 'cluster=%s' % fsid

    def ceph_poll_status(self):
        # get previous data every time in case:
        # * daemon restarted
        # * alarm was cleared manually but stored as raised in daemon
        self._get_current_alarms()
        if self.current_health_alarm:
            LOG.info(_LI("Current alarm: %s") %
                     str(self.current_health_alarm.__dict__))

        # get ceph health
        health = self._get_health()
        LOG.info(_LI("Current Ceph health: "
                     "%(health)s detail: %(detail)s") % health)

        health = self.filter_health_status(health)
        if health['health'] != constants.CEPH_HEALTH_OK:
            self._report_fault(health, fm_constants.FM_ALARM_ID_STORAGE_CEPH)
            self._report_alarm_osds_health()
        else:
            self._clear_fault(fm_constants.FM_ALARM_ID_STORAGE_CEPH)
            self.clear_all_major_critical()

    def filter_health_status(self, health):
        return super(Monitor, self).filter_health_status(health)

    def ceph_poll_quotas(self):
        self._get_current_alarms()
        if self.current_quota_alarms:
            LOG.info(_LI("Current quota alarms %s") %
                     self.current_quota_alarms)

        # Get current current size of each tier
        previous_tiers_size = self.tiers_size
        self.tiers_size = self._get_tiers_size()

        # Make sure any removed tiers have the alarms cleared
        for t in (set(previous_tiers_size)-set(self.tiers_size)):
            self._clear_fault(fm_constants.FM_ALARM_ID_STORAGE_CEPH_FREE_SPACE,
                              "{0}.tier={1}".format(
                                  self.service.entity_instance_id,
                                  t[:-len(constants.CEPH_CRUSH_TIER_SUFFIX)]))

        # Check the quotas on each tier
        for tier in self.tiers_size:
            # TODO(rchurch): For R6 remove the tier from the default crushmap
            # and remove this check. No longer supporting this tier in R5
            if tier == 'cache-tier':
                continue

            # Extract the tier name from the crush equivalent
            tier_name = tier[:-len(constants.CEPH_CRUSH_TIER_SUFFIX)]

            if self.tiers_size[tier] == 0:
                LOG.info(_LI("'%s' tier cluster size not yet available")
                         % tier_name)
                continue

            pools_quota_sum = 0
            if tier == self.primary_tier_name:
                for pool in constants.CEPH_POOLS:
                    if (pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL or
                       pool['pool_name'] ==
                       constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER):
                        object_pool_name = self._get_object_pool_name()
                        if object_pool_name is None:
                            LOG.error("Rados gateway object data pool does "
                                      "not exist.")
                        else:
                            pools_quota_sum += \
                                self._get_osd_pool_quota(object_pool_name)
                    else:
                        pools_quota_sum += self._get_osd_pool_quota(
                            pool['pool_name'])
            else:
                for pool in constants.SB_TIER_CEPH_POOLS:
                    pool_name = "{0}-{1}".format(pool['pool_name'], tier_name)
                    pools_quota_sum += self._get_osd_pool_quota(pool_name)

            # Currently, there is only one pool on the addtional tier(s),
            # therefore allow a quota of 0
            if (pools_quota_sum != self.tiers_size[tier] and
                    pools_quota_sum != 0):
                self._report_fault(
                    {'tier_name': tier_name,
                     'tier_eid': "{0}.tier={1}".format(
                         self.service.entity_instance_id,
                         tier_name)},
                    fm_constants.FM_ALARM_ID_STORAGE_CEPH_FREE_SPACE)
            else:
                self._clear_fault(
                    fm_constants.FM_ALARM_ID_STORAGE_CEPH_FREE_SPACE,
                    "{0}.tier={1}".format(self.service.entity_instance_id,
                                          tier_name))

    # CEPH HELPERS

    def _get_fsid(self):
        try:
            response, fsid = self.service.ceph_api.fsid(
                body='text', timeout=30)
        except IOError as e:
            LOG.warning(_LW("ceph_api.fsid failed: %s") % str(e.message))
            self.cluster_is_up = False
            return None

        if not response.ok:
            LOG.warning(_LW("Get fsid failed: %s") % response.reason)
            self.cluster_is_up = False
            return None

        self.cluster_is_up = True
        return fsid.strip()

    def _get_health(self):
        try:
            # we use text since it has all info
            response, body = self.service.ceph_api.health(
                body='text', timeout=30)
        except IOError as e:
            LOG.warning(_LW("ceph_api.health failed: %s") % str(e.message))
            self.cluster_is_up = False
            return {'health': constants.CEPH_HEALTH_DOWN,
                    'detail': 'Ceph cluster is down.'}

        if not response.ok:
            LOG.warning(_LW("CEPH health check failed: %s") % response.reason)
            health_info = [constants.CEPH_HEALTH_DOWN, response.reason]
            self.cluster_is_up = False
        else:
            health_info = body.split(' ', 1)
            self.cluster_is_up = True

        health = health_info[0]

        if len(health_info) > 1:
            detail = health_info[1]
        else:
            detail = health_info[0]

        return {'health': health.strip(),
                'detail': detail.strip()}

    def _get_object_pool_name(self):
        if self.known_object_pool_name is None:
            response, body = self.service.ceph_api.osd_pool_get(
                constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL,
                "pg_num",
                body='json')

            if response.ok:
                self.known_object_pool_name = \
                    constants.CEPH_POOL_OBJECT_GATEWAY_NAME_JEWEL
                return self.known_object_pool_name

            response, body = self.service.ceph_api.osd_pool_get(
                constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER,
                "pg_num",
                body='json')

            if response.ok:
                self.known_object_pool_name = \
                    constants.CEPH_POOL_OBJECT_GATEWAY_NAME_HAMMER
                return self.known_object_pool_name

        return self.known_object_pool_name

    def _get_osd_pool_quota(self, pool_name):
        try:
            resp, quota = self.service.ceph_api.osd_get_pool_quota(
                pool_name, body='json')
        except IOError:
            return 0

        if not resp.ok:
            LOG.error(_LE("Getting the quota for "
                          "%(name)s pool failed:%(reason)s)") %
                      {"name": pool_name, "reason": resp.reason})
            return 0
        else:
            try:
                quota_gib = int(quota["output"]["quota_max_bytes"])/(1024**3)
                return quota_gib
            except IOError:
                return 0

    # we have two root nodes 'cache-tier' and 'storage-tier'
    # to calculate the space that is used by the pools, we must only
    # use 'storage-tier'
    # this function determines if a certain node is under a certain
    # tree
    def host_is_in_root(self, search_tree, node, root_name):
        if node['type'] == 'root':
            if node['name'] == root_name:
                return True
            else:
                return False
        return self.host_is_in_root(search_tree,
                                    search_tree[node['parent']],
                                    root_name)

    # The information received from ceph is not properly
    # structured for efficient parsing and searching, so
    # it must be processed and transformed into a more
    # structured form.
    #
    # Input received from ceph is an array of nodes with the
    # following structure:
    #    [{'id':<node_id>, 'children':<array_of_children_ids>, ....},
    #     ...]
    #
    # We process this array and transform it into a dictionary
    # (for efficient access) The transformed "search tree" is a
    # dictionary with the following structure:
    #   {<node_id> : {'children':<array_of_children_ids>}
    def _get_tiers_size(self):
        try:
            resp, body = self.service.ceph_api.osd_df(
                body='json',
                output_method='tree')
        except IOError:
            return 0
        if not resp.ok:
            LOG.error(_LE("Getting the cluster usage "
                          "information failed: %(reason)s - "
                          "%(body)s") % {"reason": resp.reason,
                                         "body": body})
            return {}

        # A node is a crushmap element: root, chassis, host, osd. Create a
        # dictionary for the nodes with the key as the id used for efficient
        # searching through nodes.
        #
        # For example: storage-0's node has one child node => OSD 0
        # {
        #     "id": -4,
        #     "name": "storage-0",
        #     "type": "host",
        #     "type_id": 1,
        #     "reweight": -1.000000,
        #     "kb": 51354096,
        #     "kb_used": 1510348,
        #     "kb_avail": 49843748,
        #     "utilization": 2.941047,
        #     "var": 1.480470,
        #     "pgs": 0,
        #     "children": [
        #         0
        #     ]
        # },
        search_tree = {}
        for node in body['output']['nodes']:
            search_tree[node['id']] = node

        # Extract the tiers as we will return a dict for the size of each tier
        tiers = {k: v for k, v in search_tree.items() if v['type'] == 'root'}

        # For each tier, traverse the heirarchy from the root->chassis->host.
        # Sum the host sizes to determine the overall size of the tier
        tier_sizes = {}
        for tier in tiers.values():
            tier_size = 0
            for chassis_id in tier['children']:
                chassis_size = 0
                chassis = search_tree[chassis_id]
                for host_id in chassis['children']:
                    host = search_tree[host_id]
                    if (chassis_size == 0 or
                            chassis_size > host['kb']):
                        chassis_size = host['kb']
                tier_size += chassis_size/(1024 ** 2)
            tier_sizes[tier['name']] = tier_size

        return tier_sizes

    # ALARM HELPERS

    @staticmethod
    def _check_storage_group(osd_tree, group_id,
                             hosts, osds, fn_report_alarm):
        reasons = set()
        degraded_hosts = set()
        severity = fm_constants.FM_ALARM_SEVERITY_CRITICAL
        for host_id in hosts:
            if len(osds[host_id]) == 0:
                reasons.add(constants.ALARM_REASON_NO_OSD)
                degraded_hosts.add(host_id)
            else:
                for osd_id in osds[host_id]:
                    if osd_tree[osd_id]['status'] == 'up':
                        if osd_tree[osd_id]['reweight'] == 0.0:
                            reasons.add(constants.ALARM_REASON_OSDS_OUT)
                            degraded_hosts.add(host_id)
                        else:
                            severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
                    elif osd_tree[osd_id]['status'] == 'down':
                        reasons.add(constants.ALARM_REASON_OSDS_DOWN)
                        degraded_hosts.add(host_id)
        if constants.ALARM_REASON_OSDS_OUT in reasons \
           and constants.ALARM_REASON_OSDS_DOWN in reasons:
            reasons.add(constants.ALARM_REASON_OSDS_DOWN_OUT)
            reasons.remove(constants.ALARM_REASON_OSDS_OUT)
        if constants.ALARM_REASON_OSDS_DOWN in reasons \
           and constants.ALARM_REASON_OSDS_DOWN_OUT in reasons:
            reasons.remove(constants.ALARM_REASON_OSDS_DOWN)
        reason = "/".join(list(reasons))
        if severity == fm_constants.FM_ALARM_SEVERITY_CRITICAL:
            reason = "{} {}: {}".format(
                fm_constants.ALARM_CRITICAL_REPLICATION,
                osd_tree[group_id]['name'],
                reason)
        elif severity == fm_constants.FM_ALARM_SEVERITY_MAJOR:
            reason = "{} {}: {}".format(
                fm_constants.ALARM_MAJOR_REPLICATION,
                osd_tree[group_id]['name'],
                reason)
        if len(degraded_hosts) == 0:
            if len(hosts) < 2:
                fn_report_alarm(
                    osd_tree[group_id]['name'],
                    "{} {}: {}".format(
                        fm_constants.ALARM_MAJOR_REPLICATION,
                        osd_tree[group_id]['name'],
                        constants.ALARM_REASON_PEER_HOST_DOWN),
                    fm_constants.FM_ALARM_SEVERITY_MAJOR)
        elif len(degraded_hosts) == 1:
            fn_report_alarm(
                "{}.host={}".format(
                    osd_tree[group_id]['name'],
                    osd_tree[list(degraded_hosts)[0]]['name']),
                reason, severity)
        else:
            fn_report_alarm(
                osd_tree[group_id]['name'],
                reason, severity)

    def _check_storage_tier(self, osd_tree, tier_name, fn_report_alarm):
        for tier_id in osd_tree:
            if osd_tree[tier_id]['type'] != 'root':
                continue
            if osd_tree[tier_id]['name'] != tier_name:
                continue
            for group_id in osd_tree[tier_id]['children']:
                if osd_tree[group_id]['type'] != 'chassis':
                    continue
                if not osd_tree[group_id]['name'].startswith('group-'):
                    continue
                hosts = []
                osds = {}
                for host_id in osd_tree[group_id]['children']:
                    if osd_tree[host_id]['type'] != 'host':
                        continue
                    hosts.append(host_id)
                    osds[host_id] = []
                    for osd_id in osd_tree[host_id]['children']:
                        if osd_tree[osd_id]['type'] == 'osd':
                            osds[host_id].append(osd_id)
                self._check_storage_group(osd_tree, group_id, hosts,
                                          osds, fn_report_alarm)
            break

    def _current_health_alarm_equals(self, reason, severity):
        if not self.current_health_alarm:
            return False
        if getattr(self.current_health_alarm, 'severity', None) != severity:
            return False
        if getattr(self.current_health_alarm, 'reason_text', None) != reason:
            return False
        return True

    def _report_alarm_osds_health(self):
        response, osd_tree = self.service.ceph_api.osd_tree(body='json')
        if not response.ok:
            LOG.error(_LE("Failed to retrieve Ceph OSD tree: "
                          "status_code: %(status_code)s, reason: %(reason)s") %
                      {"status_code": response.status_code,
                       "reason": response.reason})
            return
        osd_tree = dict([(n['id'], n) for n in osd_tree['output']['nodes']])
        alarms = []

        self._check_storage_tier(osd_tree, "storage-tier",
                                 lambda *args: alarms.append(args))
        if self.cache_enabled:
            self._check_storage_tier(osd_tree, "cache-tier",
                                     lambda *args: alarms.append(args))

        old_alarms = {}
        for alarm_id in [
                fm_constants.FM_ALARM_ID_STORAGE_CEPH_MAJOR,
                fm_constants.FM_ALARM_ID_STORAGE_CEPH_CRITICAL]:
            alarm_list = self.service.fm_api.get_faults_by_id(alarm_id)
            if not alarm_list:
                continue
            for alarm in alarm_list:
                if alarm.entity_instance_id not in old_alarms:
                    old_alarms[alarm.entity_instance_id] = []
                old_alarms[alarm.entity_instance_id].append(
                    (alarm.alarm_id, alarm.reason_text))

        for peer_group, reason, severity in alarms:
            if self._current_health_alarm_equals(reason, severity):
                continue
            alarm_critical_major = fm_constants.FM_ALARM_ID_STORAGE_CEPH_MAJOR
            if severity == fm_constants.FM_ALARM_SEVERITY_CRITICAL:
                alarm_critical_major = (
                    fm_constants.FM_ALARM_ID_STORAGE_CEPH_CRITICAL)
            entity_instance_id = (
                self.service.entity_instance_id + '.peergroup=' + peer_group)
            alarm_already_exists = False
            if entity_instance_id in old_alarms:
                for alarm_id, old_reason in old_alarms[entity_instance_id]:
                    if (reason == old_reason and
                            alarm_id == alarm_critical_major):
                        # if the alarm is exactly the same, we don't need
                        # to recreate it
                        old_alarms[entity_instance_id].remove(
                            (alarm_id, old_reason))
                        alarm_already_exists = True
                    elif (alarm_id == alarm_critical_major):
                        # if we change just the reason, then we just remove the
                        # alarm from the list so we don't remove it at the
                        # end of the function
                        old_alarms[entity_instance_id].remove(
                            (alarm_id, old_reason))

                if (len(old_alarms[entity_instance_id]) == 0):
                    del old_alarms[entity_instance_id]

                # in case the alarm is exactly the same, we skip the alarm set
                if alarm_already_exists is True:
                    continue
            major_repair_action = constants.REPAIR_ACTION_MAJOR_CRITICAL_ALARM
            fault = fm_api.Fault(
                alarm_id=alarm_critical_major,
                alarm_type=fm_constants.FM_ALARM_TYPE_4,
                alarm_state=fm_constants.FM_ALARM_STATE_SET,
                entity_type_id=fm_constants.FM_ENTITY_TYPE_CLUSTER,
                entity_instance_id=entity_instance_id,
                severity=severity,
                reason_text=reason,
                probable_cause=fm_constants.ALARM_PROBABLE_CAUSE_15,
                proposed_repair_action=major_repair_action,
                service_affecting=constants.SERVICE_AFFECTING['HEALTH_WARN'])
            alarm_uuid = self.service.fm_api.set_fault(fault)
            if alarm_uuid:
                LOG.info(_LI(
                    "Created storage alarm %(alarm_uuid)s - "
                    "severity: %(severity)s, reason: %(reason)s, "
                    "service_affecting: %(service_affecting)s") % {
                    "alarm_uuid": str(alarm_uuid),
                    "severity": str(severity),
                    "reason": reason,
                    "service_affecting": str(
                        constants.SERVICE_AFFECTING['HEALTH_WARN'])})
            else:
                LOG.error(_LE(
                    "Failed to create storage alarm - "
                    "severity: %(severity)s, reason: %(reason)s, "
                    "service_affecting: %(service_affecting)s") % {
                    "severity": str(severity),
                    "reason": reason,
                    "service_affecting": str(
                        constants.SERVICE_AFFECTING['HEALTH_WARN'])})

        for entity_instance_id in old_alarms:
            for alarm_id, old_reason in old_alarms[entity_instance_id]:
                self.service.fm_api.clear_fault(alarm_id, entity_instance_id)

    @staticmethod
    def _parse_reason(health):
        """ Parse reason strings received from Ceph """
        if health['health'] in constants.CEPH_STATUS_CUSTOM:
            # Don't parse reason messages that we added
            return "Storage Alarm Condition: %(health)s. %(detail)s" % health

        reasons_lst = health['detail'].split(';')

        parsed_reasons_text = ""

        # Check if PGs have issues - we can't safely store the entire message
        # as it tends to be long
        for reason in reasons_lst:
            if "pgs" in reason:
                parsed_reasons_text += "PGs are degraded/stuck or undersized"
                break

        # Extract recovery status
        parsed_reasons = [r.strip() for r in reasons_lst if 'recovery' in r]
        if parsed_reasons:
            parsed_reasons_text += ";" + ";".join(parsed_reasons)

        # We need to keep the most important parts of the messages when storing
        # them to fm alarms, therefore text between [] brackets is truncated if
        # max size is reached.

        # Add brackets, if needed
        if len(parsed_reasons_text):
            lbracket = " ["
            rbracket = "]"
        else:
            lbracket = ""
            rbracket = ""

        msg = {"head": "Storage Alarm Condition: ",
               "tail": ". Please check 'ceph -s' for more details."}
        max_size = constants.FM_ALARM_REASON_MAX_SIZE - \
            len(msg["head"]) - len(msg["tail"])

        return (
            msg['head'] +
            (health['health'] + lbracket + parsed_reasons_text)[:max_size-1] +
            rbracket + msg['tail'])

    def _report_fault(self, health, alarm_id):
        if alarm_id == fm_constants.FM_ALARM_ID_STORAGE_CEPH:
            new_severity = constants.SEVERITY[health['health']]
            new_reason_text = self._parse_reason(health)
            new_service_affecting = \
                constants.SERVICE_AFFECTING[health['health']]

            # Raise or update alarm if necessary
            if ((not self.current_health_alarm) or
                (self.current_health_alarm.__dict__['severity'] !=
                 new_severity) or
                (self.current_health_alarm.__dict__['reason_text'] !=
                 new_reason_text) or
                (self.current_health_alarm.__dict__['service_affecting'] !=
                 str(new_service_affecting))):

                fault = fm_api.Fault(
                    alarm_id=fm_constants.FM_ALARM_ID_STORAGE_CEPH,
                    alarm_type=fm_constants.FM_ALARM_TYPE_4,
                    alarm_state=fm_constants.FM_ALARM_STATE_SET,
                    entity_type_id=fm_constants.FM_ENTITY_TYPE_CLUSTER,
                    entity_instance_id=self.service.entity_instance_id,
                    severity=new_severity,
                    reason_text=new_reason_text,
                    probable_cause=fm_constants.ALARM_PROBABLE_CAUSE_15,
                    proposed_repair_action=constants.REPAIR_ACTION,
                    service_affecting=new_service_affecting)

                alarm_uuid = self.service.fm_api.set_fault(fault)
                if alarm_uuid:
                    LOG.info(_LI(
                        "Created storage alarm %(alarm_uuid)s - "
                        "severity: %(severity)s, reason: %(reason)s, "
                        "service_affecting: %(service_affecting)s") % {
                        "alarm_uuid": alarm_uuid,
                        "severity": new_severity,
                        "reason": new_reason_text,
                        "service_affecting": new_service_affecting})
                else:
                    LOG.error(_LE(
                        "Failed to create storage alarm - "
                        "severity: %(severity)s, reason: %(reason)s "
                        "service_affecting: %(service_affecting)s") % {
                        "severity": new_severity,
                        "reason": new_reason_text,
                        "service_affecting": new_service_affecting})

            # Log detailed reason for later analysis
            if (self.current_ceph_health != health['health'] or
                    self.detailed_health_reason != health['detail']):
                LOG.info(_LI("Ceph status changed: %(health)s "
                             "detailed reason: %(detail)s") % health)
                self.current_ceph_health = health['health']
                self.detailed_health_reason = health['detail']

        elif (alarm_id == fm_constants.FM_ALARM_ID_STORAGE_CEPH_FREE_SPACE and
              not health['tier_eid'] in self.current_quota_alarms):

            quota_reason_text = ("Quota/Space mismatch for the %s tier. The "
                                 "sum of Ceph pool quotas does not match the "
                                 "tier size." % health['tier_name'])
            fault = fm_api.Fault(
                alarm_id=fm_constants.FM_ALARM_ID_STORAGE_CEPH_FREE_SPACE,
                alarm_state=fm_constants.FM_ALARM_STATE_SET,
                entity_type_id=fm_constants.FM_ENTITY_TYPE_CLUSTER,
                entity_instance_id=health['tier_eid'],
                severity=fm_constants.FM_ALARM_SEVERITY_MINOR,
                reason_text=quota_reason_text,
                alarm_type=fm_constants.FM_ALARM_TYPE_7,
                probable_cause=fm_constants.ALARM_PROBABLE_CAUSE_75,
                proposed_repair_action=(
                    "Update ceph storage pool quotas to use all available "
                    "cluster space for the %s tier." % health['tier_name']),
                service_affecting=False)

            alarm_uuid = self.service.fm_api.set_fault(fault)
            if alarm_uuid:
                LOG.info(_LI(
                    "Created storage quota storage alarm %(alarm_uuid)s. "
                    "Reason: %(reason)s") % {
                    "alarm_uuid": alarm_uuid, "reason": quota_reason_text})
            else:
                LOG.error(_LE("Failed to create quota "
                              "storage alarm. Reason: %s") % quota_reason_text)

    def _clear_fault(self, alarm_id, entity_instance_id=None):
        # Only clear alarm if there is one already raised
        if (alarm_id == fm_constants.FM_ALARM_ID_STORAGE_CEPH and
                self.current_health_alarm):
            LOG.info(_LI("Clearing health alarm"))
            self.service.fm_api.clear_fault(
                fm_constants.FM_ALARM_ID_STORAGE_CEPH,
                self.service.entity_instance_id)
        elif (alarm_id == fm_constants.FM_ALARM_ID_STORAGE_CEPH_FREE_SPACE and
              entity_instance_id in self.current_quota_alarms):
            LOG.info(_LI("Clearing quota alarm with entity_instance_id %s")
                     % entity_instance_id)
            self.service.fm_api.clear_fault(
                fm_constants.FM_ALARM_ID_STORAGE_CEPH_FREE_SPACE,
                entity_instance_id)

    def clear_critical_alarm(self, group_name):
        alarm_list = self.service.fm_api.get_faults_by_id(
            fm_constants.FM_ALARM_ID_STORAGE_CEPH_CRITICAL)
        if alarm_list:
            for alarm in range(len(alarm_list)):
                group_id = alarm_list[alarm].entity_instance_id.find("group-")
                group_instance_name = (
                    "group-" +
                    alarm_list[alarm].entity_instance_id[group_id + 6])
                if group_name == group_instance_name:
                    self.service.fm_api.clear_fault(
                        fm_constants.FM_ALARM_ID_STORAGE_CEPH_CRITICAL,
                        alarm_list[alarm].entity_instance_id)

    def clear_all_major_critical(self, group_name=None):
        # clear major alarms
        alarm_list = self.service.fm_api.get_faults_by_id(
            fm_constants.FM_ALARM_ID_STORAGE_CEPH_MAJOR)
        if alarm_list:
            for alarm in range(len(alarm_list)):
                if group_name is not None:
                    group_id = (
                        alarm_list[alarm].entity_instance_id.find("group-"))
                    group_instance_name = (
                        "group-" +
                        alarm_list[alarm].entity_instance_id[group_id+6])
                    if group_name == group_instance_name:
                        self.service.fm_api.clear_fault(
                            fm_constants.FM_ALARM_ID_STORAGE_CEPH_MAJOR,
                            alarm_list[alarm].entity_instance_id)
                else:
                    self.service.fm_api.clear_fault(
                        fm_constants.FM_ALARM_ID_STORAGE_CEPH_MAJOR,
                        alarm_list[alarm].entity_instance_id)
        # clear critical alarms
        alarm_list = self.service.fm_api.get_faults_by_id(
            fm_constants.FM_ALARM_ID_STORAGE_CEPH_CRITICAL)
        if alarm_list:
            for alarm in range(len(alarm_list)):
                if group_name is not None:
                    group_id = (
                        alarm_list[alarm].entity_instance_id.find("group-"))
                    group_instance_name = (
                        "group-" +
                        alarm_list[alarm].entity_instance_id[group_id + 6])
                    if group_name == group_instance_name:
                        self.service.fm_api.clear_fault(
                            fm_constants.FM_ALARM_ID_STORAGE_CEPH_CRITICAL,
                            alarm_list[alarm].entity_instance_id)
                else:
                    self.service.fm_api.clear_fault(
                        fm_constants.FM_ALARM_ID_STORAGE_CEPH_CRITICAL,
                        alarm_list[alarm].entity_instance_id)

    def _get_current_alarms(self):
        """ Retrieve currently raised alarm """
        self.current_health_alarm = self.service.fm_api.get_fault(
            fm_constants.FM_ALARM_ID_STORAGE_CEPH,
            self.service.entity_instance_id)
        quota_faults = self.service.fm_api.get_faults_by_id(
            fm_constants.FM_ALARM_ID_STORAGE_CEPH_FREE_SPACE)
        if quota_faults:
            self.current_quota_alarms = [f.entity_instance_id
                                         for f in quota_faults]
        else:
            self.current_quota_alarms = []
