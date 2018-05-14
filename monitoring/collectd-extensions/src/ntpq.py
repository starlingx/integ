
# Copyright (c) 2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
#

import os
import subprocess
import uuid
import collectd
from fm_api import constants as fm_constants
from fm_api import fm_api
import tsconfig.tsconfig as tsc

api = fm_api.FaultAPIs()

PLUGIN = 'NTP query plugin'

PLUGIN_SCRIPT = '/etc/rmonfiles.d/query_ntp_servers.sh'
PLUGIN_RESULT = '/tmp/ntpq_server_info'

# static variables
ALARM_ID__NTPQ = "100.114"


# define a class here that will persist over read calls
class NtpqObject:
    hostname = ''
    base_eid = ''
    severity = 'clear'
    suppression = True
    service_affecting = False
    status = 0
    last_result = ''
    this_result = ''
    id = ALARM_ID__NTPQ
    name = "NTP"
    alarm_type = fm_constants.FM_ALARM_TYPE_1
    cause = fm_constants.ALARM_PROBABLE_CAUSE_UNKNOWN
    repair = "Monitor and if condition persists, "
    repair += "contact next level of support."


obj = NtpqObject()


def is_uuid_like(val):
    """Returns validation of a value as a UUID."""
    try:
        return str(uuid.UUID(val)) == val
    except (TypeError, ValueError, AttributeError):
        return False


# The config function - called once on collectd process startup
def config_func(config):
    """
    Configure the plugin
    """

    collectd.debug('%s config function' % PLUGIN)
    return 0


# The init function - called once on collectd process startup
def init_func():

    # ntp query is for controllers only
    if tsc.nodetype != 'controller':
        return 0

    # get current hostname
    obj.hostname = os.uname()[1]
    obj.base_eid = 'host=' + obj.hostname + '.ntp'
    collectd.info("%s on %s with entity id '%s'" % PLUGIN, obj.hostname, obj.base_eid)
    return 0


# The sample read function - called on every audit interval
def read_func():

    # ntp query is for controllers only
    if tsc.nodetype != 'controller':
        return 0

    result = int(0)
    # Query ntp
    try:
        result = os.system(PLUGIN_SCRIPT)
    except Exception as e:
        collectd.error("%s Could not run '%s' (%s)" %
                       (PLUGIN, e))
        return 0

    obj.status = int(result)/0x100

    collectd.info("%s Query Result: %s" % (PLUGIN, obj.status))

    if os.path.exists(PLUGIN_RESULT) is False:
        collectd.error("%s produced no result file '%s'" %
                       (PLUGIN, PLUGIN_RESULT))
        return 0

    # read the query result file.
    # format is in the PLUGIN_SCRIPT file.
    # This code only wants the second line.
    # It contains list of unreachable ntp servers that need alarm management.
    count = 0
    with open(PLUGIN_RESULT, 'r') as infile:
        for line in infile:
            count += 1
            collectd.info("%s Query Result: %s" % (PLUGIN, line))
    if count == 0:
        collectd.error("%s produced empty result file '%s'" %
                       (PLUGIN, PLUGIN_RESULT))
        return 0

    sample = 1

    # Dispatch usage value to collectd
    val = collectd.Values(host=obj.hostname)
    val.plugin = 'ntpq'
    val.plugin_instance = 'some.ntp.server.ip'
    val.type = 'absolute'
    val.type_instance = 'state'
    val.dispatch(values=[sample])

    severity = 'clear'
    obj.severity = 'clear'

    # if there is no severity change then consider exiting
    if obj.severity == severity:

        # unless the current severity is 'minor'
        if severity == 'minor':
            # TODO: check to see if the failing IP address is changed
            collectd.info("%s NEED TO CHECK IP ADDRESSES" % (PLUGIN))
        else:
            return 0

    # if current severity is clear but previous severity is not then
    # prepare to clear the alarms
    if severity == 'clear':
        _alarm_state = fm_constants.FM_ALARM_STATE_CLEAR

        # TODO: loop over all raises alarms and clear them
        collectd.info("%s NEED CLEAR ALL ALARMS" % (PLUGIN))
        if api.clear_fault(obj.id, obj.base_eid) is False:
            collectd.error("%s %s:%s clear_fault failed" %
                           (PLUGIN, obj.id, obj.base_eid))
        return 0

    elif severity == 'major':
        reason = "NTP configuration does not contain any valid "
        reason += "or reachable NTP servers."
        eid = obj.base_eid
        fm_severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
    else:
        # TODO: There can be up to 3 inacessable servers
        ip = 'some.server.ip.addr'
        reason = "NTP address "
        reason += ip
        reason += " is not a valid or a reachable NTP server."
        eid = obj.base_eid + '=' + ip
        fm_severity = fm_constants.FM_ALARM_SEVERITY_MINOR

    fault = fm_api.Fault(
        alarm_id=obj.id,
        alarm_state=fm_constants.FM_ALARM_STATE_SET,
        entity_type_id=fm_constants.FM_ENTITY_TYPE_HOST,
        entity_instance_id=eid,
        severity=fm_severity,
        reason_text=reason,
        alarm_type=obj.alarm_type,
        probable_cause=obj.cause,
        proposed_repair_action=obj.repair,
        service_affecting=obj.service_affecting,
        suppression=obj.suppression)

    alarm_uuid = api.set_fault(fault)
    if is_uuid_like(alarm_uuid) is False:
        collectd.error("%s %s:%s set_fault failed:%s" %
                       (PLUGIN, obj.id, eid, alarm_uuid))
        return 0

    # TODO: clear the object alarm state

    return 0


# register the config, init and read functions
collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func)
