#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
############################################################################
#
# This is the Remote Logging Server plugin for collectd.
#
# The Remote Logging Server is enabled if /etc/syslog-ng/syslog-ng.conf
# contains '@include remotelogging.conf'
#
# There is no asynchronous notification of remote logging server
# configuration enable/disable state changes. Therefore, each audit
# interval needs to check whether its enabled or not.
#
# every audit interval ...
#
# read_func:
#   check enabled:
#   if disabled and alarmed:
#      clear alarm
#   if enabled:
#      get ip and port
#      query status
#      if connected and alarmed:
#          clear alarm
#      if not connected and not alarmed:
#          raise alarm
#
# system remotelogging-modify --ip_address <ip address>
#                             --transport tcp
#                             --enabled True
#
############################################################################

import os
import collectd
import tsconfig.tsconfig as tsc
import plugin_common as pc
from fm_api import constants as fm_constants
from oslo_concurrency import processutils
from fm_api import fm_api

# Fault manager API Object
api = fm_api.FaultAPIs()

# name of the plugin
PLUGIN_NAME = 'remotels'

# all logs produced by this plugin are prefixed with this
PLUGIN = 'remote logging server'

# Interface Monitoring Interval in seconds
PLUGIN_AUDIT_INTERVAL = 60

# Sample Data 'type' and 'instance' database field values.
PLUGIN_TYPE = 'absolute'
PLUGIN_TYPE_INSTANCE = 'reachable'

# Remote Logging Connectivity Alarm ID
PLUGIN_ALARMID = '100.118'

# The file where this plugin learns if remote logging is enabled
SYSLOG_CONF_FILE = '/etc/syslog-ng/syslog-ng.conf'

# Plugin Control Object
obj = pc.PluginObject(PLUGIN, "")


# Raise Remote Logging Server Alarm
def raise_alarm():
    """Raise Remote Logging Server Alarm"""

    repair = 'Ensure Remote Log Server IP is reachable from '
    repair += 'Controller through OAM interface; otherwise '
    repair += 'contact next level of support.'

    reason = 'Controller cannot establish connection with '
    reason += 'remote logging server.'

    try:
        fault = fm_api.Fault(
            alarm_id=PLUGIN_ALARMID,
            alarm_state=fm_constants.FM_ALARM_STATE_SET,
            entity_type_id=fm_constants.FM_ENTITY_TYPE_HOST,
            entity_instance_id=obj.base_eid,
            severity=fm_constants.FM_ALARM_SEVERITY_MINOR,
            reason_text=reason,
            alarm_type=fm_constants.FM_ALARM_TYPE_1,
            probable_cause=fm_constants.ALARM_PROBABLE_CAUSE_6,
            proposed_repair_action=repair,
            service_affecting=False,
            suppression=False)

        alarm_uuid = api.set_fault(fault)
        if pc.is_uuid_like(alarm_uuid) is False:
            collectd.error("%s %s:%s set_fault failed:%s" %
                           (PLUGIN, PLUGIN_ALARMID,
                            obj.base_eid, alarm_uuid))
        else:
            collectd.info("%s %s:%s alarm raised" %
                          (PLUGIN, PLUGIN_ALARMID, obj.base_eid))
            obj.alarmed = True

    except:
        collectd.error("%s %s:%s set_fault exception" %
                       (PLUGIN, PLUGIN_ALARMID, obj.base_eid))


# Clear remote logging server alarm
def clear_alarm():
    """Clear remote logging server alarm"""

    try:
        if api.clear_fault(PLUGIN_ALARMID, obj.base_eid) is True:
            collectd.info("%s alarm cleared" % PLUGIN)
        obj.alarmed = False
        return True

    except:
        collectd.error("%s %s:%s clear failed ; will retry" %
                       (PLUGIN, PLUGIN_ALARMID, obj.base_eid))
        return False


# The config function - called once on collectd process startup
def config_func(config):
    """Configure the plugin"""

    # all configuration is learned during normal monitoring
    obj.config_done = True
    return 0


# The init function - called once on collectd process startup
def init_func():
    """Init the plugin"""

    # remote logging server monitoring is for controllers only
    if tsc.nodetype != 'controller':
        return 0

    if obj.init_done is False:
        if obj.init_ready() is False:
            return False

    obj.hostname = obj.gethostname()
    obj.base_eid = 'host=' + obj.hostname
    obj.init_done = True
    collectd.info("%s initialization complete" % PLUGIN)

    return True


# The sample read function - called on every audit interval
def read_func():
    """Remote logging server connectivity plugin read function"""

    # remote logging server monitoring is for controllers only
    if tsc.nodetype != 'controller':
        return 0

    if obj.init_done is False:
        init_func()
        return 0

    # get current state
    current_enabled_state = obj.enabled

    # check to see if remote logging is enabled
    obj.enabled = False   # assume disabled
    if os.path.exists(SYSLOG_CONF_FILE) is True:
        with open(SYSLOG_CONF_FILE, 'r') as infile:
            for line in infile:
                if line.startswith('@include '):
                    service = line.rstrip().split(' ')[1]
                    if service == '"remotelogging.conf"':
                        obj.enabled = True
                        break

    if current_enabled_state == obj.enabled:
        logit = False
    else:
        if obj.enabled is False:
            collectd.info("%s is disabled" % PLUGIN)
        else:
            collectd.info("%s is enabled" % PLUGIN)
        logit = True

    # Handle startup case by clearing existing alarm if its raised.
    # Its runtime cheaper and simpler to issue a blind clear than query.
    if obj.audits == 0:
        if clear_alarm() is False:
            # if clear fails then retry next time
            return 0
        if obj.enabled is False:
            collectd.info("%s is disabled" % PLUGIN)
        obj.audits = 1

    if obj.enabled is False:
        if obj.alarmed is True:
            clear_alarm()
        return 0

    # If we get here then the server is enabled ...
    # Need to query it

    # Get the ip and port from line that looks like this
    #
    #            tag                 proto     address          port
    # -----------------------------   ---  --------------       ---
    # destination remote_log_server  {tcp("128.224.186.65" port(514));};
    #
    address = protocol = port = ''
    with open(SYSLOG_CONF_FILE, 'r') as infile:
        for line in infile:
            if line.startswith('destination remote_log_server'):
                try:
                    if len(line.split('{')) > 1:
                        protocol = line.split('{')[1][0:3]
                        address = line.split('{')[1].split('"')[1]
                        port = line.split('{')[1].split('(')[2].split(')')[0]
                        if not protocol or not address or not port:
                            collectd.error("%s remote log server credentials "
                                           "parse error ; (%s:%s:%s)" %
                                           (PLUGIN, protocol, address, port))
                            return 1
                        else:
                            # line parsed ; move on ...
                            break
                    else:
                        collectd.error("%s remote log server line parse error"
                                       " ; %s" % (PLUGIN, line))
                except Exception as ex:
                    collectd.error("%s remote log server credentials "
                                   "parse exception ; (%s)" % (PLUGIN, line))

    if ':' in address:
        ipv = 6
        protocol += 6

        # Monitoring of IPV6 is not currently supported
        return 0

    else:
        ipv = 4

        # This plugin detects server connectivity through its socket status.
        # To get that construct the remote logging server IP string.
        # The files being looked at(/proc/net/tcp(udp)) use hex values,
        # so convert the string caps hex value with reverse ordering of
        # the "ipv4" values
        index = 3
        addr = [0, 0, 0, 0]

        # swap order
        for tup in address.split('.'):
            addr[index] = int(tup)
            index -= 1

        # build the CAPs HEX address
        UPPER_HEX_IP = ''
        for tup in addr:
            val = hex(int(tup)).split('x')[-1].upper()
            if len(val) == 1:
                UPPER_HEX_IP += '0'
            UPPER_HEX_IP += val
        UPPER_HEX_IP += ':'
        tmp = hex(int(port)).split('x')[-1].upper()
        for i in range(4 - len(tmp)):
            UPPER_HEX_IP += '0'
        UPPER_HEX_IP += tmp

    # log example tcp:ipv4:128.224.186.65:514 : IP:41BAE080:0202
    collectd.debug("%s %s:ipv%d:%s:%s : IP:%s" %
                   (PLUGIN, protocol, ipv, address, port, UPPER_HEX_IP))

    cmd = "cat /proc/net/" + protocol
    cmd += " | awk '{print $3 \" \" $4}' | grep " + UPPER_HEX_IP
    cmd += " | awk '{print $2}'"
    res, err = processutils.execute(cmd, shell=True)
    if err:
        collectd.error("%s processutils error:%s" % (PLUGIN, err))

        # cmd example:
        # cat /proc/net/tcp | awk '{print $3 " " $4}'
        #                   | grep 41BAE080:0202
        #                   | awk '{print $2}'
        collectd.debug("%s Cmd:%s" % (PLUGIN, cmd))
        return 0

    if res and res.rstrip() == '01':
        # connected state reads 01
        # Example log: Res:[01]

        # clear alarm if
        #  - currently alarmed and
        #  - debounced by 1 ; need 2 connected readings in a row
        if obj.alarmed is True:
            clear_alarm()

        # Only log on state change
        if obj.usage != 1:
            logit = True

        obj.usage = 1
        conn = ''

    else:
        # res typically reads 02 when notr connected
        # Example log: Res:[02]
        collectd.debug("%s Res:[%s] " % (PLUGIN, res.rstrip()))

        # raise alarm if
        #  - not already alarmed
        #  - debounced by 1 ; need 2 failures in a row
        if obj.alarmed is False and obj.usage == 0:
            raise_alarm()

        # only log on state change
        if obj.usage == 1 or obj.audits == 1:
            logit = True

        obj.usage = 0
        conn = 'not '

    if logit is True:
        collectd.info("%s is %sconnected [%s ipv%d %s:%s]" %
                      (PLUGIN, conn, protocol, ipv, address, port))
    obj.audits += 1

    # Dispatch usage value to collectd
    val = collectd.Values(host=obj.hostname)
    val.plugin = PLUGIN_NAME
    val.type = PLUGIN_TYPE
    val.type_instance = PLUGIN_TYPE_INSTANCE
    val.dispatch(values=[obj.usage])
    return 0


# register the config, init and read functions
collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func, interval=PLUGIN_AUDIT_INTERVAL)
