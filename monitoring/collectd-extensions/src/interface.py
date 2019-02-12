#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
############################################################################
#
# This is the Host Interface Monitor plugin for collectd.
#
# Only mgmt, infra and oam interfaces are supported with the following
# mapping specified in /etc/platform/platform.conf
#
#   oam - oam_interface            | controller | mandatory
# mgmnt - management_interface     | all hosts  | mandatory
# infa  - infrastructure_interface | any host   | optional
#
# This plugin queries the maintenance Link Monitor daemon 'lmon'
# for a link status summary of that hosts configured networks.
#
# This plugin's read_func issues an http GET request to the Link Monitor
# which responds with a json string that represents a complete summary
# of the monitored links, state and the time of the last event or when
# initial status was learned. An example of the Link Monitor response is
#
#  {
#      "status" : "pass"
#      "link_info": [
#      { "network":"mgmt",
#        "type":"vlan",
#        "links": [
#              { "name":"enp0s8.1", "state":"Up", "time":"5674323454567" },
#              { "name":"enp0s8.2", "state":"Up", "time":"5674323454567" }]
#      },
#      { "network":"infra",
#        "type":"bond",
#        "bond":"bond0",
#        "links": [
#              { "name":"enp0s9f1", "state":"Down", "time":"5674323454567" },
#              { "name":"enp0s9f0", "state":"Up"  , "time":"5674323454567" }]
#      },
#      { "network":"oam",
#        "type":"single",
#        "links": [
#              { "name":"enp0s3", "state":"Up", "time":"5674323454567" }]
#      }]
#  }
#
# On failure
#
#  {
#      "status" : "fail ; bad request <or other text based reason>"
#  }
#
# This plugin then uses this information to manage interface alarm
# assertion and clear with appropriate severity.
#
# Severity: Interface and Port levels
#
#  Alarm Level  Minor        Major              Critical
#  -----------  -----  ---------------------    ----------------------------
#  Interface     N/A   One of lag pair is Up    All Interface ports are Down
#       Port     N/A   Physical Link is Down    N/A
#
# Sample Data: represented as % of total links Up for that network interface
#
#  100 or 100% percent used - all links of interface are up.
#   50 or  50% percent used - one of lag pair is Up and the other is Down
#    0 or   0% percent used - all ports for that network are Down
#
############################################################################

import os
import time
import datetime
import collectd
import plugin_common as pc
from fm_api import constants as fm_constants
from fm_api import fm_api

# Fault manager API Object
api = fm_api.FaultAPIs()

# name of the plugin - all logs produced by this plugin are prefixed with this
PLUGIN = 'interface plugin'

# Interface Monitoring Interval in seconds
PLUGIN_AUDIT_INTERVAL = 10

# Sample Data 'type' and 'instance' database field values.
PLUGIN_TYPE = 'percent'
PLUGIN_TYPE_INSTANCE = 'usage'

# The Link Status Query URL
PLUGIN_HTTP_URL_PREFIX = 'http://localhost:'

# This plugin's timeout
PLUGIN_HTTP_TIMEOUT = 5

# Specify the link monitor as the maintenance destination service
# full path should look like ; http://localhost:2122/mtce/lmon
PLUGIN_HTTP_URL_PATH = '/mtce/lmon'

# Port and Interface Alarm Identifiers
PLUGIN_OAM_PORT_ALARMID = '100.106'     # OAM Network Port
PLUGIN_OAM_IFACE_ALARMID = '100.107'    # OAM Network Interface

PLUGIN_MGMT_PORT_ALARMID = '100.108'    # Management Network Port
PLUGIN_MGMT_IFACE_ALARMID = '100.109'   # Management Network Interface

PLUGIN_INFRA_PORT_ALARMID = '100.110'   # Infrastructure Network Port
PLUGIN_INFRA_IFACE_ALARMID = '100.111'  # Infrastructure Nwk Interface

# List of all alarm identifiers.
ALARM_ID_LIST = [PLUGIN_OAM_PORT_ALARMID,
                 PLUGIN_OAM_IFACE_ALARMID,
                 PLUGIN_MGMT_PORT_ALARMID,
                 PLUGIN_MGMT_IFACE_ALARMID,
                 PLUGIN_INFRA_PORT_ALARMID,
                 PLUGIN_INFRA_IFACE_ALARMID]

# Monitored Network Name Strings
NETWORK_MGMT = 'mgmt'
NETWORK_INFRA = 'infra'
NETWORK_OAM = 'oam'

# Port / Interface State strings
LINK_UP = 'Up'
LINK_DOWN = 'Down'

# Alarm control actions
ALARM_ACTION_RAISE = 'raise'
ALARM_ACTION_CLEAR = 'clear'

# Alarm level.
# Ports are the lowest level and represent a physical link
# Interfaces are port groupings in terms of LAG
LEVEL_PORT = 'port'
LEVEL_IFACE = 'interface'


# Link Object (aka Port or Physical interface) Structure
# and member functions.
class LinkObject:

    def __init__(self, alarm_id):

        self.name = None
        self.state = LINK_UP
        self.timestamp = float(0)
        self.severity = fm_constants.FM_ALARM_SEVERITY_CLEAR
        self.alarm_id = alarm_id
        self.state_change = True

        collectd.debug("%s LinkObject constructor: %s" %
                       (PLUGIN, alarm_id))

    ##################################################################
    #
    # Name       : raise_port_alarm
    #
    # Purpose    : This link object member function is used to
    #              raise link/port alarms.
    #
    # Parameters : Network the link is part of.
    #
    # Returns    : True on failure and False on success.
    #
    ##################################################################
    def raise_port_alarm(self, network):
        """ Raise a port alarm """

        if self.severity != fm_constants.FM_ALARM_SEVERITY_MAJOR:

            if manage_alarm(self.name,
                            network,
                            LEVEL_PORT,
                            ALARM_ACTION_RAISE,
                            fm_constants.FM_ALARM_SEVERITY_MAJOR,
                            self.alarm_id,
                            self.timestamp) is False:

                self.severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
                collectd.info("%s %s %s port alarm raised" %
                              (PLUGIN, self.name, self.alarm_id))
                return False
            else:
                return True
        else:
            return False

    ##################################################################
    #
    # Name       : clear_port_alarm
    #
    # Purpose    : This link object member function is used to
    #              clear link/port alarms.
    #
    # Parameters : Network the link is part of.
    #
    # Returns    : True on failure and False on success.
    #
    ##################################################################
    def clear_port_alarm(self, network):
        """ Clear a port alarm """

        if self.severity != fm_constants.FM_ALARM_SEVERITY_CLEAR:
            if manage_alarm(self.name,
                            network,
                            LEVEL_PORT,
                            ALARM_ACTION_CLEAR,
                            fm_constants.FM_ALARM_SEVERITY_CLEAR,
                            self.alarm_id,
                            self.timestamp) is False:

                collectd.info("%s %s %s port alarm cleared" %
                              (PLUGIN, self.name, self.alarm_id))
                self.severity = fm_constants.FM_ALARM_SEVERITY_CLEAR
                return False
            else:
                return True
        else:
            return False


# Interface (aka Network) Level Object Structure and member functions
class NetworkObject:

    def __init__(self, name):

        self.name = name
        self.sample = 0
        self.sample_last = 0
        self.severity = fm_constants.FM_ALARM_SEVERITY_CLEAR
        self.degraded = False
        self.timestamp = float(0)

        # add the respective alarm IDs to each object
        alarm_id = None
        if name == NETWORK_OAM:
            alarm_id = PLUGIN_OAM_PORT_ALARMID
            self.alarm_id = PLUGIN_OAM_IFACE_ALARMID
        elif name == NETWORK_MGMT:
            alarm_id = PLUGIN_MGMT_PORT_ALARMID
            self.alarm_id = PLUGIN_MGMT_IFACE_ALARMID
        elif name == NETWORK_INFRA:
            alarm_id = PLUGIN_INFRA_PORT_ALARMID
            self.alarm_id = PLUGIN_INFRA_IFACE_ALARMID
        else:
            self.alarm_id = ""
            collectd.error("%s unexpected network (%s)" % (PLUGIN, name))

        collectd.debug("%s %s NetworkObject constructor: %s" %
                       (PLUGIN, name, self.alarm_id))

        if alarm_id:
            self.link_one = LinkObject(alarm_id)
            self.link_two = LinkObject(alarm_id)

    ##################################################################
    #
    # Name       : raise_iface_alarm
    #
    # Purpose    : This network object member function used to
    #              raise interface alarms.
    #
    # Parameters : None
    #
    # Returns    : True on failure and False on success.
    #
    ##################################################################
    def raise_iface_alarm(self, severity):
        """ Raise an interface  alarm """

        if severity == fm_constants.FM_ALARM_SEVERITY_CLEAR:
            collectd.error("%s %s raise alarm called with clear severity" %
                           (PLUGIN, self.name))
            return True

        if self.severity != severity:
            if manage_alarm(self.name,
                            self.name,
                            LEVEL_IFACE,
                            ALARM_ACTION_RAISE,
                            severity,
                            self.alarm_id,
                            self.timestamp) is False:

                self.severity = severity
                collectd.info("%s %s %s %s interface alarm raised" %
                              (PLUGIN,
                               self.name,
                               self.alarm_id,
                               pc.get_severity_str(severity)))
                return False
            else:
                return True
        else:
            return False

    ##################################################################
    #
    # Name       : clear_iface_alarm
    #
    # Purpose    : This network object member function used to
    #              clear interface alarms.
    #
    # Parameters : None
    #
    # Returns    : True on failure and False on success.
    #
    ##################################################################
    def clear_iface_alarm(self):
        """ Clear an interface alarm """

        if self.severity != fm_constants.FM_ALARM_SEVERITY_CLEAR:
            if manage_alarm(self.name,
                            self.name,
                            LEVEL_IFACE,
                            ALARM_ACTION_CLEAR,
                            fm_constants.FM_ALARM_SEVERITY_CLEAR,
                            self.alarm_id,
                            self.timestamp) is False:

                collectd.info("%s %s %s %s interface alarm cleared" %
                              (PLUGIN,
                               self.name,
                               self.alarm_id,
                               pc.get_severity_str(self.severity)))
                self.severity = fm_constants.FM_ALARM_SEVERITY_CLEAR
                return False
            else:
                return True
        else:
            return False

    ######################################################################
    #
    # Name     : manage_iface_alarm
    #
    # Purpose  : clear or raise appropriate severity level interface alarm
    #
    # Returns  : None
    #
    ######################################################################
    def manage_iface_alarm(self):
        """ """
        # Single Link Config
        if self.link_two.name is None:
            if self.link_one.state == LINK_DOWN:
                if self.severity != fm_constants.FM_ALARM_SEVERITY_CRITICAL:
                    self.timestamp = self.link_one.timestamp
                    self.raise_iface_alarm(
                        fm_constants.FM_ALARM_SEVERITY_CRITICAL)
            elif self.link_one.state == LINK_UP:
                if self.severity != fm_constants.FM_ALARM_SEVERITY_CLEAR:
                    self.clear_iface_alarm()

        # Lagged Link Config
        #
        # The interface level timestamp is updated based on the failed
        # link timestamps
        elif self.link_one.state == LINK_UP and \
                self.link_two.state == LINK_DOWN:
            if self.severity != fm_constants.FM_ALARM_SEVERITY_MAJOR:
                self.timestamp = self.link_two.timestamp
                self.raise_iface_alarm(fm_constants.FM_ALARM_SEVERITY_MAJOR)

        elif self.link_one.state == LINK_DOWN and \
                self.link_two.state == LINK_UP:
            if self.severity != fm_constants.FM_ALARM_SEVERITY_MAJOR:
                self.timestamp = self.link_one.timestamp
                self.raise_iface_alarm(fm_constants.FM_ALARM_SEVERITY_MAJOR)

        elif self.link_one.state == LINK_UP and self.link_two.state == LINK_UP:
            if self.severity != fm_constants.FM_ALARM_SEVERITY_CLEAR:
                self.clear_iface_alarm()

        elif self.link_one.state == LINK_DOWN and \
                self.link_two.state == LINK_DOWN:
            if self.severity != fm_constants.FM_ALARM_SEVERITY_CRITICAL:
                if self.link_one.timestamp > self.link_two.timestamp:
                    self.timestamp = self.link_one.timestamp
                else:
                    self.timestamp = self.link_two.timestamp
                self.raise_iface_alarm(fm_constants.FM_ALARM_SEVERITY_CRITICAL)


# Plugin Control Object
obj = pc.PluginObject(PLUGIN, PLUGIN_HTTP_URL_PREFIX)


# Network Object List - Primary Network/Link Control Object
NETWORKS = [NetworkObject(NETWORK_MGMT),
            NetworkObject(NETWORK_OAM),
            NetworkObject(NETWORK_INFRA)]


##########################################################################
#
# Name      : get_timestamp
#
# Purpose   : Convert the long long int microsecond time as string
#             that accompany link info from the Link Monitor (lmond)
#             and catch exceptions in doing so.
#
# Parameters: lmon_time - long long int as string
#
# Returns   : float time that can be consumed by datetime.fromtimestamp
#
#             Returns same unit of now time if provided lmon_time is
#             invalid.
#
##########################################################################
def get_timestamp(lmon_time):
    """ Convert lmon time to fm timestamp time """

    if lmon_time:
        try:
            return(float(float(lmon_time)/1000000))
        except:
            collectd.error("%s failed to parse timestamp ;"
                           " using current time" % PLUGIN)
    else:
        collectd.error("%s no timestamp ;"
                       " using current time" % PLUGIN)

    return(float(time.time()))


def dump_network_info(network):
    """ Log the specified network info """

    link_one_event_time = datetime.datetime.fromtimestamp(
        float(network.link_one.timestamp)).strftime('%Y-%m-%d %H:%M:%S')

    link_two_info = ''
    if network.link_two.name is not None:
        link_two_event_time = datetime.datetime.fromtimestamp(
            float(network.link_two.timestamp)).strftime('%Y-%m-%d %H:%M:%S')

        link_two_info += "; link two '"
        link_two_info += network.link_two.name
        link_two_info += "' went " + network.link_two.state
        link_two_info += " at " + link_two_event_time

    pcnt = '%'

    collectd.info("%s %5s %3d%c ; "
                  "link one '%s' went %s at %s %s" %
                  (PLUGIN,
                   network.name,
                   network.sample,
                   pcnt,
                   network.link_one.name,
                   network.link_one.state,
                   link_one_event_time,
                   link_two_info))


#########################################################################
#
# Name       : this_hosts_alarm
#
# Purpose    : Determine if the supplied eid is for this host.
#
# Description: The eid formats for the alarms managed by this plugin are
#
#              host=<hostname>.port=<port_name>
#              host=<hostname>.interface=<network_name>
#
# Assumptions: There is no restriction preventing the system
#              administrator from creating hostnames with period's ('.')
#              in them. Because so the eid cannot simply be split
#              around '='s and '.'s. Instead its split around this
#              plugins level type '.port' or '.interface'.
#
# Returns    : True if hostname is a match
#              False otherwise
#
##########################################################################
def this_hosts_alarm(hostname, eid):
    """ Check if the specified eid is for this host """

    if hostname:
        if eid:
            # 'host=controller-0.interface=mgmt'
            try:
                eid_host = None
                eid_disected = eid.split('=')
                if len(eid_disected) == 3:
                    # ['host', 'controller-0.interface', 'mgmt']
                    if len(eid_disected[1].split('.port')) == 2:
                        eid_host = eid_disected[1].split('.port')[0]
                        if eid_host and eid_host == hostname:
                            return True
                    elif len(eid_disected[1].split('.interface')) == 2:
                        eid_host = eid_disected[1].split('.interface')[0]
                        if eid_host and eid_host == hostname:
                            return True
            except Exception as ex:
                collectd.error("%s failed to parse alarm eid (%s)"
                               " [eid:%s]" % (PLUGIN, str(ex), eid))

    return False


##########################################################################
#
# Name       : clear_alarms
#
# Purpose    : Clear all interface alarms on process startup.
#
# Description: Called after first successful Link Status query.
#
#              Loops over the provided alarm id list querying all alarms
#              for each. Any that are raised are precisely cleared.
#
#              Prevents stuck alarms over port and interface reconfig.
#
#              If the original alarm case still exists the alarm will
#              be re-raised with the original link event timestamp that
#              is part of the Link Status query response.
#
# Parameters : A list of this plugin's alarm ids
#
# Returns    : True on failure and False on success
#
##########################################################################
def clear_alarms(alarm_id_list):
    """ Clear alarm state of all plugin alarms. """
    found = False
    for alarm_id in alarm_id_list:
        alarms = api.get_faults_by_id(alarm_id)
        if alarms:
            for alarm in alarms:
                eid = alarm.entity_instance_id
                if this_hosts_alarm(obj.hostname, eid) is False:
                    # ignore other host alarms
                    continue

                if alarm_id == PLUGIN_OAM_PORT_ALARMID or \
                        alarm_id == PLUGIN_OAM_IFACE_ALARMID or \
                        alarm_id == PLUGIN_MGMT_PORT_ALARMID or \
                        alarm_id == PLUGIN_MGMT_IFACE_ALARMID or \
                        alarm_id == PLUGIN_INFRA_PORT_ALARMID or \
                        alarm_id == PLUGIN_INFRA_IFACE_ALARMID:
                    eid = alarm.entity_instance_id
                    if api.clear_fault(alarm_id, eid) is False:
                        collectd.error("%s %s:%s clear_fault failed" %
                                       (PLUGIN, alarm_id, eid))
                        return True
                    else:
                        found = True
                        collectd.info("%s %s clearing %s alarm %s:%s" %
                                      (PLUGIN,
                                       NETWORK_INFRA,
                                       alarm.severity,
                                       alarm_id,
                                       alarm.entity_instance_id))

    if found is False:
        collectd.info("%s found no startup alarms" % PLUGIN)

    return False


##########################################################################
#
# Name       : manage_alarm
#
# Purpose    : Raises or clears port and interface alarms based on
#              calling parameters.
#
# Returns    : True on failure and False on success
#
##########################################################################
def manage_alarm(name, network, level, action, severity, alarm_id, timestamp):
    """ Manage raise and clear of port and interface alarms """

    ts = datetime.datetime.fromtimestamp(
        float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    collectd.debug("%s %s %s %s alarm for %s:%s [%s] %s" % (PLUGIN,
                   severity, level, alarm_id, network, name, action, ts))

    if action == ALARM_ACTION_CLEAR:
        alarm_state = fm_constants.FM_ALARM_STATE_CLEAR
        reason = ''
        repair = ''
    else:
        # reason ad repair strings are only needed on alarm assertion
        alarm_state = fm_constants.FM_ALARM_STATE_SET
        reason = "'" + network.upper() + "' " + level
        repair = 'Check cabling and far-end port configuration ' \
                 'and status on adjacent equipment.'

    # build the alarm eid and name string
    if level == LEVEL_PORT:
        eid = 'host=' + obj.hostname + "." + level + '=' + name
        reason += " failed"
    else:
        eid = 'host=' + obj.hostname + "." + level + '=' + network
        if severity == fm_constants.FM_ALARM_SEVERITY_MAJOR:
            reason += " degraded"
        else:
            reason += " failed"

    if alarm_state == fm_constants.FM_ALARM_STATE_CLEAR:
        if api.clear_fault(alarm_id, eid) is False:
            collectd.error("%s %s:%s clear_fault failed" %
                           (PLUGIN, alarm_id, eid))
            return True
        else:
            return False
    else:
        fault = fm_api.Fault(
            uuid="",
            alarm_id=alarm_id,
            alarm_state=alarm_state,
            entity_type_id=fm_constants.FM_ENTITY_TYPE_HOST,
            entity_instance_id=eid,
            severity=severity,
            reason_text=reason,
            alarm_type=fm_constants.FM_ALARM_TYPE_7,
            probable_cause=fm_constants.ALARM_PROBABLE_CAUSE_UNKNOWN,
            proposed_repair_action=repair,
            service_affecting=True,
            timestamp=ts,
            suppression=True)

        alarm_uuid = api.set_fault(fault)
        if pc.is_uuid_like(alarm_uuid) is False:
            collectd.error("%s %s:%s set_fault failed:%s" %
                           (PLUGIN, alarm_id, eid, alarm_uuid))
            return True
        else:
            return False


# The config function - called once on collectd process startup
def config_func(config):
    """ Configure the plugin """

    # Need to update the Link Status Query URL with the port number.
    url_updated = False

    # The Link Monitor port number is first searched for in
    # the /etc/mtc/lmond.conf file.
    # If its not there then its taken from the plugin config.

    # /etc/mtc/lmond.conf
    fn = '/etc/mtc/lmond.conf'
    if (os.path.exists(fn)):
        try:
            with open(fn, 'r') as infile:
                for line in infile:
                    if 'lmon_query_port' in line:
                        if isinstance(int(line.split()[2]), int):

                            # add the port
                            obj.url += line.split()[2]

                            # add the path /mtce/lmon
                            obj.url += PLUGIN_HTTP_URL_PATH

                            url_updated = "config file"
                            break
        except EnvironmentError as e:
            collectd.error(str(e), UserWarning)

    if url_updated is False:
        # Try the config as this might be updated by manifest
        for node in config.children:
            key = node.key.lower()
            val = int(node.values[0])
            if key == 'port':
                if isinstance(int(val), int):

                    # add the port
                    obj.url += str(val)

                    # add the path /mtce/lmon
                    obj.url += PLUGIN_HTTP_URL_PATH

                    url_updated = "manifest"
                    break

    if url_updated:
        collectd.info("%s configured by %s [%s]" %
                      (PLUGIN, url_updated, obj.url))
        obj.config_done = True
    else:
        collectd.error("%s config failure ; cannot monitor" %
                       (PLUGIN))
    return 0


# The init function - called once on collectd process startup
def init_func():
    """ Init the plugin """

    if obj.config_done is False:
        collectd.info("%s configuration failed" % PLUGIN)
        time.sleep(300)
        return False

    if obj.init_done is False:
        if obj.init_ready() is False:
            return False

    obj.hostname = obj.gethostname()
    obj.init_done = True
    collectd.info("%s initialization complete" % PLUGIN)

    return True


# The sample read function - called on every audit interval
def read_func():
    """ collectd interface monitor plugin read function """

    if obj.init_done is False:
        init_func()
        return 0

    if obj.audits == 0:

        # clear all alarms on first audit

        # block on fm availability

        # If existing raised the alarms are still valid then
        # they will be re-raised with the same timestamp the
        # original event occurred at once auditing resumes.
        if clear_alarms(ALARM_ID_LIST) is True:
            collectd.error("%s failed to clear existing alarms ; "
                           "retry next audit" % PLUGIN)

            # Don't proceed till we can communicate with FM and
            # clear all existing interface and port alarms.
            return 0

    try:
        # Issue query and construct the monitoring object
        error = obj.make_http_request(to=PLUGIN_HTTP_TIMEOUT)

        if len(obj.jresp) == 0:
            collectd.error("%s no json response from http request" % PLUGIN)
            return 1

        if error:
            return 1

        # Check query status
        try:
            if obj.jresp['status'] != 'pass':
                collectd.error("%s link monitor query %s" %
                               (PLUGIN, obj.jresp['status']))
                return 0

        except Exception as ex:
            collectd.error("%s http request get reason failed ; %s" %
                           (PLUGIN, str(ex)))
            collectd.info("%s  resp:%d:%s" %
                          (PLUGIN, len(obj.jresp), obj.jresp))
            return 1

        # log the first query response
        if obj.audits == 0:
            collectd.info("%s Link Status Query Response:%d:\n%s" %
                          (PLUGIN, len(obj.jresp), obj.jresp))

            # uncomment below for debug purposes
            #
            # for network in NETWORKS:
            #    dump_network_info(network)

        try:
            link_info = obj.jresp['link_info']
            for network_link_info in link_info:
                collectd.debug("%s parse link info:%s" %
                               (PLUGIN, network_link_info))
                for network in NETWORKS:
                    if network.name == network_link_info['network']:
                        links = network_link_info['links']
                        nname = network.name
                        if len(links) > 0:
                            link_one = links[0]

                            # get initial link one name
                            if network.link_one.name is None:
                                network.link_one.name = link_one['name']

                            network.link_one.timestamp =\
                                float(get_timestamp(link_one['time']))

                            # load link one state
                            if link_one['state'] == LINK_UP:
                                collectd.debug("%s %s IS Up [%s]" %
                                               (PLUGIN, network.link_one.name,
                                                network.link_one.state))
                                if network.link_one.state != LINK_UP:
                                    network.link_one.state_change = True
                                    network.link_one.clear_port_alarm(nname)
                                network.link_one.state = LINK_UP
                            else:
                                collectd.debug("%s %s IS Down [%s]" %
                                               (PLUGIN, network.link_one.name,
                                                network.link_one.state))
                                if network.link_one.state == LINK_UP:
                                    network.link_one.state_change = True
                                    network.link_one.raise_port_alarm(nname)
                                network.link_one.state = LINK_DOWN

                        if len(links) > 1:
                            link_two = links[1]

                            # get initial link two name
                            if network.link_two.name is None:
                                network.link_two.name = link_two['name']

                            network.link_two.timestamp =\
                                float(get_timestamp(link_two['time']))

                            # load link two state
                            if link_two['state'] == LINK_UP:
                                collectd.debug("%s %s IS Up [%s]" %
                                               (PLUGIN, network.link_two.name,
                                                network.link_two.state))
                                if network.link_two.state != LINK_UP:
                                    network.link_two.state_change = True
                                    network.link_two.clear_port_alarm(nname)
                                    network.link_two.state = LINK_UP
                            else:
                                collectd.debug("%s %s IS Down [%s]" %
                                               (PLUGIN, network.link_two.name,
                                                network.link_two.state))
                                if network.link_two.state == LINK_UP:
                                    network.link_two.state_change = True
                                    network.link_two.raise_port_alarm(nname)
                                network.link_two.state = LINK_DOWN

                        # manage interface alarms
                        network.manage_iface_alarm()

        except Exception as ex:
            collectd.error("%s link monitor query parse error: %s " %
                           (PLUGIN, obj.resp))

        # handle state changes
        for network in NETWORKS:
            if network.link_two.name is not None and \
                    network.link_one.state_change is True:

                if network.link_one.state == LINK_UP:
                    collectd.info("%s %s link one '%s' is Up" %
                                  (PLUGIN,
                                   network.name,
                                   network.link_one.name))
                else:
                    collectd.info("%s %s link one '%s' is Down" %
                                  (PLUGIN,
                                   network.name,
                                   network.link_one.name))

            if network.link_two.name is not None and \
                    network.link_two.state_change is True:

                if network.link_two.state == LINK_UP:
                    collectd.info("%s %s link two '%s' is Up" %
                                  (PLUGIN,
                                   network.name,
                                   network.link_two.name))
                else:
                    collectd.info("%s %s link two %s 'is' Down" %
                                  (PLUGIN,
                                   network.name,
                                   network.link_two.name))

        # Dispatch usage value to collectd
        val = collectd.Values(host=obj.hostname)
        val.plugin = 'interface'
        val.type = 'percent'
        val.type_instance = 'used'

        # For each interface [ mgmt, oam, infra ]
        #   calculate the percentage used sample
        #      sample = 100 % when all its links are up
        #      sample =   0 % when all its links are down
        #      sample =  50 % when one of a lagged group is down
        for network in NETWORKS:

            if network.link_one.name is not None:

                val.plugin_instance = network.name

                network.sample = 0

                if network.link_two.name is not None:
                    # lagged

                    if network.link_one.state == LINK_UP:
                        network.sample = 50
                    if network.link_two.state == LINK_UP:
                        network.sample += 50
                else:
                    if network.link_one.state == LINK_UP:
                        network.sample = 100
                val.dispatch(values=[network.sample])

                if network.link_one.state_change is True or \
                        network.link_two.state_change is True:

                    dump_network_info(network)

                    network.link_one.state_change = False
                    network.link_two.state_change = False

                network.sample_last = network.sample

            else:
                collectd.debug("%s %s network not provisioned" %
                               (PLUGIN, network.name))
        obj.audits += 1

    except Exception as ex:
        collectd.info("%s http request failed: %s" % (PLUGIN, str(ex)))

    return 0


# register the config, init and read functions
collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func, interval=PLUGIN_AUDIT_INTERVAL)
