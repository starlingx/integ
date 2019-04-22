#
# Copyright (c) 2018-2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Version 1.0
#
############################################################################
#
# This file is the collectd 'FM Alarm' Notifier.
#
# This notifier manages raising and clearing alarms based on collectd
# notifications ; i.e. automatic collectd calls to this handler/notifier.
#
# Collectd process startup automatically calls this module's init_func which
# declares and initializes a plugObject class for plugin type in preparation
# for periodic ongoing monitoring where collectd calls notify_func for each
# plugin and instance of that plugin.
#
# All other class or common member functions implemented herein exist in
# support of that aformentioned initialization and periodic monitoring.
#
# Collects provides information about each event as an object passed to the
# notification handler ; the notification object.
#
#    object.host              - the hostname.
#
#    object.plugin            - the name of the plugin aka resource.
#    object.plugin_instance   - plugin instance string i.e. say mountpoint
#                               for df plugin or numa? node for memory.
#    object.type,             - the unit i.e. percent or absolute.
#    object.type_instance     - the attribute i.e. free, used, etc.
#
#    object.severity          - a integer value 0=OK , 1=warning, 2=failure.
#    object.message           - a log-able message containing the above along
#                               with the value.
#
# This notifier uses the notification object to manage plugin/instance alarms.
#
# To avoid stuck alarms or missing alarms the plugin thresholds should be
# configured with Persist = true and persistOK = true. Thes controls tell
# collectd to always send notifications regardless of state change ; which
# would be the case with these cobtrols set to false.
#
# Persist   = false ; only send notifications on 'okay' to 'not okay' change.
# PersistOK = false ; only send notifications on 'not okay' to 'okay' change.
#
# With these both set to true in the threshold spec for the plugin then
# collectd will call this notifier for each audit plugin/instance audit.
#
# Collectd supports only 2 threshold severities ; warning and failure.
# The 'failure' maps to 'critical' while 'warning' maps to 'major' in FM.
#
# To avoid unnecessary load on FM, this notifier maintains current alarm
# state and only makes an FM call on alarm state changes. Current alarm state
# is queried by the init function called by collectd on process startup.
#
# Current alarm state is maintained by two severity lists for each plugin,
# a warnings list and a failures list.
#
# When a failure is reported against a specific plugin then that resources's
# entity_id is added to that plugin's alarm object's failures list. Similarly,
# warning assertions get their entity id added to plugin's alarm object's
# warnings list. Any entity id should only exist in one of the lists at one
# time or in none at all if the notification condition is 'okay' and the alarm
# is cleared.
#
# Adding Plugins:
#
# To add new plugin support just search for ADD_NEW_PLUGIN and add the data
# requested in that area.
#
# Example commands to read samples from the influx database
#
# SELECT * FROM df_value WHERE instance='root' AND type='percent_bytes' AND
#                                                      type_instance='used'
# SELECT * FROM cpu_value WHERE type='percent' AND type_instance='used'
# SELECT * FROM memory_value WHERE type='percent' AND type_instance='used'
#
############################################################################
#
# Import list

# UT imports
import os
import re
import uuid
import collectd
from threading import RLock as Lock
from fm_api import constants as fm_constants
from fm_api import fm_api
import tsconfig.tsconfig as tsc
import plugin_common as pc

# only load influxdb on the controller
if tsc.nodetype == 'controller':
    from influxdb import InfluxDBClient

api = fm_api.FaultAPIs()

# Debug control
debug = False
debug_lists = False
want_state_audit = False
want_vswitch = False

# number of notifier loops before the state is object dumped
DEBUG_AUDIT = 2

# write a 'value' log on a the resource sample change of more than this amount
LOG_STEP = 10

# Number of back to back database update misses
MAX_NO_UPDATE_B4_ALARM = 5

# This plugin name
PLUGIN = 'alarm notifier'

# Path to the plugin's drop dir
PLUGIN_PATH = '/etc/collectd.d/'

# the name of the collectd samples database
DATABASE_NAME = 'collectd samples'

READING_TYPE__PERCENT_USAGE = '% usage'

# Default invalid threshold value
INVALID_THRESHOLD = float(-1)

# collectd severity definitions ;
# Note: can't seem to pull then in symbolically with a header
NOTIF_FAILURE = 1
NOTIF_WARNING = 2
NOTIF_OKAY = 4

PASS = 0
FAIL = 1

# Some plugin_instances are mangled by collectd.
# The filesystem plugin is especially bad for this.
# For instance the "/var/log" MountPoint instance is
# reported as "var-log".
# The following is a list of mangled instances list
# that need the '-' replaced with '/'.
#
# ADD_NEW_PLUGIN if there are new file systems being added that
# have subdirectories in the name then they will need to be added
# to the mangled list
mangled_list = {"dev-shm",
                "var-log",
                "var-run",
                "var-lock",
                "var-lib-rabbitmq",
                "var-lib-postgresql",
                "var-lib-ceph-mon",
                "etc-nova-instances",
                "opt-platform",
                "opt-cgcs",
                "opt-etcd",
                "opt-extension",
                "opt-backups"}

# ADD_NEW_PLUGIN: add new alarm id definition
ALARM_ID__CPU = "100.101"
ALARM_ID__MEM = "100.103"
ALARM_ID__DF = "100.104"
ALARM_ID__EXAMPLE = "100.113"

ALARM_ID__VSWITCH_CPU = "100.102"
ALARM_ID__VSWITCH_MEM = "100.115"
ALARM_ID__VSWITCH_PORT = "300.001"
ALARM_ID__VSWITCH_IFACE = "300.002"


# ADD_NEW_PLUGIN: add new alarm id to the list
ALARM_ID_LIST = [ALARM_ID__CPU,
                 ALARM_ID__MEM,
                 ALARM_ID__DF,
                 ALARM_ID__VSWITCH_CPU,
                 ALARM_ID__VSWITCH_MEM,
                 ALARM_ID__VSWITCH_PORT,
                 ALARM_ID__VSWITCH_IFACE,
                 ALARM_ID__EXAMPLE]

# ADD_NEW_PLUGIN: add plugin name definition
# WARNING: This must line up exactly with the plugin
#          filename without the extension.
PLUGIN__DF = "df"
PLUGIN__CPU = "cpu"
PLUGIN__MEM = "memory"
PLUGIN__INTERFACE = "interface"
PLUGIN__NTP_QUERY = "ntpq"
PLUGIN__VSWITCH_PORT = "vswitch_port"
PLUGIN__VSWITCH_CPU = "vswitch_cpu"
PLUGIN__VSWITCH_MEM = "vswitch_mem"
PLUGIN__VSWITCH_IFACE = "vswitch_iface"
PLUGIN__EXAMPLE = "example"

# ADD_NEW_PLUGIN: add plugin name to list
PLUGIN_NAME_LIST = [PLUGIN__CPU,
                    PLUGIN__MEM,
                    PLUGIN__DF,
                    PLUGIN__VSWITCH_CPU,
                    PLUGIN__VSWITCH_MEM,
                    PLUGIN__VSWITCH_PORT,
                    PLUGIN__VSWITCH_IFACE,
                    PLUGIN__EXAMPLE]


# PluginObject Class
class PluginObject:

    dbObj = None                           # shared database connection obj
    host = None                            # saved hostname
    lock = None                            # global lock for mread_func mutex
    database_setup = False                 # state of database setup
    database_setup_in_progress = False     # connection mutex

    def __init__(self, id, plugin):
        """PluginObject Class constructor"""

        # plugin specific static class members.
        self.id = id               # alarm id ; 100.1??
        self.plugin = plugin       # name of the plugin ; df, cpu, memory ...
        self.plugin_instance = ""  # the instance name for the plugin
        self.resource_name = ""    # The top level name of the resource
        self.instance_name = ""    # The instance name

        # Instance specific learned static class members.
        self.entity_id = ""        # fm entity id host=<hostname>.<instance>
        self.instance = ""         # <plugin>_<instance>

        # [ 'float value string','float threshold string]
        self.values = []
        self.value = float(0)       # float value of reading

        # float value of threshold
        self.threshold = float(INVALID_THRESHOLD)

        # Common static class members.
        self.reason_warning = ""
        self.reason_failure = ""
        self.repair = ""
        self.alarm_type = fm_constants.FM_ALARM_TYPE_7     # OPERATIONAL
        self.cause = fm_constants.ALARM_PROBABLE_CAUSE_50  # THRESHOLD CROSS
        self.suppression = True
        self.service_affecting = False

        # default most reading types are usage
        self.reading_type = READING_TYPE__PERCENT_USAGE

        # Severity tracking lists.
        # Maintains severity state between notifications.
        # Each is a list of entity ids for severity asserted alarms.
        # As alarms are cleared so is the entry in these lists.
        # The entity id should only be in one lists for any given raised alarm.
        self.warnings = []
        self.failures = []

        # total notification count
        self.count = 0

        # Debug: state audit controls
        self.audit_threshold = 0
        self.audit_count = 0

        # This member is used to help log change values using the
        # LOG_STEP threshold consant
        self.last_value = ""

        # For plugins that have multiple instances like df (filesystem plugin)
        # we need to create an instance of this object for each one.
        # This dictionary is used to associate an instance with its object.
        self.instance_objects = {}

    def _ilog(self, string):
        """Create a collectd notifier info log with the string param"""
        collectd.info('%s %s : %s' % (PLUGIN, self.plugin, string))

    def _llog(self, string):
        """Create a collectd notifier info log with the string param if debug_lists"""
        if debug_lists:
            collectd.info('%s %s : %s' % (PLUGIN, self.plugin, string))

    def _elog(self, string):
        """Create a collectd notifier error log with the string param"""
        collectd.error('%s %s : %s' % (PLUGIN, self.plugin, string))

    ##########################################################################
    #
    # Name    : _state_audit
    #
    # Purpose : Debug Tool to log plugin object info.
    #
    #           Not called in production code.
    #
    # Only the severity lists are dumped for now.
    # Other info can be added as needed.
    # Can be run as an audit or called directly.
    #
    ##########################################################################

    def _state_audit(self, location):
        """Log the state of the specified object"""

        if self.id == ALARM_ID__CPU:
            _print_state()

        self.audit_count += 1
        if self.warnings:
            collectd.info("%s AUDIT %d: %s warning list %s:%s" %
                          (PLUGIN,
                           self.audit_count,
                           self.plugin,
                           location,
                           self.warnings))
        if self.failures:
            collectd.info("%s AUDIT %d: %s failure list %s:%s" %
                          (PLUGIN,
                           self.audit_count,
                           self.plugin,
                           location,
                           self.failures))

    ##########################################################################
    #
    # Name    : _manage_change
    #
    # Purpose : Manage sample value change.
    #
    #           Handle no sample update case.
    #           Parse the notification log.
    #           Handle base object instances.
    #           Generate a log entry if the sample value changes more than
    #             step value.
    #
    ##########################################################################

    def _manage_change(self, nObject):
        """Log resource instance value on step state change"""

        # filter out messages to ignore ; notifications that have no value
        if "has not been updated for" in nObject.message:
            collectd.info("%s %s %s (%s)" %
                          (PLUGIN,
                           self.entity_id,
                           nObject.message,
                           nObject.severity))
            return "done"

        # Get the value from the notification message.
        # The location in the message is different based on the message type ;
        #   normal reading or overage reading
        #
        # message: Host controller-0, plugin memory type percent   ... [snip]
        #          All data sources are within range again.
        #          Current value of "value" is 51.412038.            <------
        #
        # message: Host controller-0, plugin df (instance scratch) ... [snip]
        #          Data source "value" is currently 97.464027.       <------
        #          That is above the failure threshold of 90.000000. <------

        # recognized strings - value only     value and threshold
        #                      ------------   -------------------
        value_sig_list = ['Current value of', 'is currently']

        # list of parsed 'string version' float values ['value','threshold']
        self.values = []
        for sig in value_sig_list:
            index = nObject.message.find(sig)
            if index != -1:
                self.values = \
                    re.findall(r"[-+]?\d*\.\d+|\d+", nObject.message[index:-1])

        # contains string versions of the float values extracted from
        # the notification message. The threshold value is included for
        # readings that are out of threshold.
        if len(self.values):
            # validate the reading
            try:
                self.value = float(self.values[0])
                # get the threshold if its there.
                if len(self.values) > 1:
                    self.threshold = float(self.values[1])
                    if nObject.plugin == PLUGIN__MEM:
                        if self.reading_type == READING_TYPE__PERCENT_USAGE:
                            # Note: add one to % usage reading types so that it
                            #       matches how rmond did it. In collectd an
                            #       overage is over the specified threshold
                            #       whereas in rmon an overage is at threshold
                            #       or above.
                            self.threshold = float(self.values[1]) + 1
                        else:
                            self.threshold = float(self.values[1])
                else:
                    self.threshold = float(INVALID_THRESHOLD)  # invalid value

            except ValueError as ex:
                collectd.error("%s %s value not integer or float (%s) (%s)" %
                               (PLUGIN, self.entity_id, self.value, str(ex)))
                return "done"
            except TypeError as ex:
                collectd.info("%s %s value has no type (%s)" %
                              (PLUGIN, self.entity_id, str(ex)))
                return "done"
        else:
            collectd.info("%s %s reported no value (%s)" %
                          (PLUGIN, self.entity_id, nObject.message))
            return "done"

        # get the last reading
        if self.last_value:
            last = float(self.last_value)
        else:
            last = float(0)

        # Determine if the change is large enough to log and save the new value
        logit = False
        if self.count == 0 or LOG_STEP == 0:
            logit = True
        elif self.reading_type == "connections":
            if self.value != last:
                logit = True
        elif self.value > last:
            if (last + LOG_STEP) < self.value:
                logit = True
        elif last > self.value:
            if (self.value + LOG_STEP) < last:
                logit = True

        # Case on types.
        #
        # Note: only usage type so far
        if logit:
            resource = self.resource_name

            # setup resource name for filesystem instance usage log
            if self.plugin == PLUGIN__DF:
                resource = self.instance

            elif self.plugin == PLUGIN__MEM:
                if self.instance_name:
                    if self.instance_name != 'platform':
                        resource += ' ' + self.instance_name

            # setup resource name for vswitch process instance name
            elif self.plugin == PLUGIN__VSWITCH_MEM:
                resource += ' Processor '
                resource += self.instance_name

            if self.reading_type == READING_TYPE__PERCENT_USAGE:
                tmp = str(self.value).split('.')
                if len(tmp[0]) == 1:
                    pre = ':  '
                else:
                    pre = ': '
                collectd.info("%s reading%s%2.2f %s - %s" %
                              (PLUGIN,
                               pre,
                               self.value,
                               self.reading_type,
                               resource))

            elif self.reading_type == "connections" and \
                    self.instance_objects and \
                    self.value != self.last_value:
                if self.instance_objects:
                    collectd.info("%s monitor: %2d %s - %s" %
                                  (PLUGIN,
                                   self.value,
                                   self.reading_type,
                                   resource))

            self.last_value = float(self.value)

    ##########################################################################
    #
    # Name    : _severity_change
    #
    # Purpose : Compare current severity to instance severity lists to
    #           facilitate early 'do nothing' exit from a notification.
    #
    # Returns : True if the severity changed
    #           False if severity is the same
    #
    ##########################################################################

    def _severity_change(self, entity_id, severity):
        """Check for a severity change"""

        if entity_id in self.warnings:
            self._llog(entity_id + " is already in warnings list")
            current_severity_str = "warning"
        elif entity_id in self.failures:
            self._llog(entity_id + " is already in failures list")
            current_severity_str = "failure"
        else:
            self._llog(entity_id + " is already OK")
            current_severity_str = "okay"

        # Compare to current state to previous state.
        # If they are the same then return done.
        if severity == current_severity_str:
            return False
        else:
            return True

    ########################################################################
    #
    # Name    : _manage_alarm
    #
    # Putpose : Alarm Severity Tracking
    #
    # This class member function accepts a severity level and entity id.
    # It manages the content of the current alarm object's 'failures' and
    # 'warnings' lists ; aka Severity Lists.
    #
    # These Severity Lists are used to record current alarmed state for
    # each instance of a plugin.
    # If an alarm is raised then its entity id is added to the appropriate
    # severity list.
    #
    # A failure notification or critical alarm goes in the failures list.
    # A warning notification or major alarm goes into the warnings list.
    #
    # These lists are used to avoid making unnecessary calls to FM.
    #
    # Startup Behavior:
    #
    # The collectd daemon runs the init function of every plugin on startup.
    # That includes this notifier plugin. The init function queries the FM
    # database for any active alarms.
    #
    # This member function is called for any active alarms that are found.
    # The entity id for active alarms is added to the appropriate
    # Severity List. This way existing alarms are maintained over collectd
    # process startup.
    #
    # Runtime Behavior:
    #
    # The current severity state is first queried and compared to the
    # newly reported severity level. If they are the same then a "done"
    # is returned telling the caller that there is no further work to do.
    # Otherwise, the lists are managed in a way that has the entity id
    # of a raised alarm in the corresponding severity list.
    #
    # See inline comments below for each specific severity and state
    # transition case.
    #
    #########################################################################

    def _manage_alarm(self, entity_id, severity):
        """Manage the alarm severity lists and report state change"""

        collectd.debug("%s manage alarm %s %s %s" %
                       (PLUGIN,
                        self.id,
                        severity,
                        entity_id))

        # Get the instance's current state
        if entity_id in self.warnings:
            current_severity_str = "warning"
        elif entity_id in self.failures:
            current_severity_str = "failure"
        else:
            current_severity_str = "okay"

        # Compare to current state to previous state.
        # If they are the same then return done.
        if severity == current_severity_str:
            return "done"

        # Otherwise, manage the severity lists ; case by case.
        warnings_list_change = False
        failures_list_change = False

        # Case 1: Handle warning to failure severity change.
        if severity == "warning" and current_severity_str == "failure":

            if entity_id in self.failures:
                self.failures.remove(entity_id)
                failures_list_change = True
                self._llog(entity_id + " is removed from failures list")
            else:
                self._elog(entity_id + " UNEXPECTEDLY not in failures list")

            # Error detection
            if entity_id in self.warnings:
                self.warnings.remove(entity_id)
                self._elog(entity_id + " UNEXPECTEDLY in warnings list")

            self.warnings.append(entity_id)
            warnings_list_change = True
            self._llog(entity_id + " is added to warnings list")

        # Case 2: Handle failure to warning alarm severity change.
        elif severity == "failure" and current_severity_str == "warning":

            if entity_id in self.warnings:
                self.warnings.remove(entity_id)
                warnings_list_change = True
                self._llog(entity_id + " is removed from warnings list")
            else:
                self._elog(entity_id + " UNEXPECTEDLY not in warnings list")

            # Error detection
            if entity_id in self.failures:
                self.failures.remove(entity_id)
                self._elog(entity_id + " UNEXPECTEDLY in failures list")

            self.failures.append(entity_id)
            failures_list_change = True
            self._llog(entity_id + " is added to failures list")

        # Case 3: Handle new alarm.
        elif severity != "okay" and current_severity_str == "okay":
            if severity == "warning":
                self.warnings.append(entity_id)
                warnings_list_change = True
                self._llog(entity_id + " added to warnings list")
            elif severity == "failure":
                self.failures.append(entity_id)
                failures_list_change = True
                self._llog(entity_id + " added to failures list")

        # Case 4: Handle alarm clear.
        else:
            # plugin is okay, ensure this plugin's entity id
            # is not in either list
            if entity_id in self.warnings:
                self.warnings.remove(entity_id)
                warnings_list_change = True
                self._llog(entity_id + " removed from warnings list")
            if entity_id in self.failures:
                self.failures.remove(entity_id)
                failures_list_change = True
                self._llog(entity_id + " removed from failures list")

        if warnings_list_change is True:
            if self.warnings:
                collectd.info("%s %s warnings %s" %
                              (PLUGIN, self.plugin, self.warnings))
            else:
                collectd.info("%s %s no warnings" %
                              (PLUGIN, self.plugin))

        if failures_list_change is True:
            if self.failures:
                collectd.info("%s %s failures %s" %
                              (PLUGIN, self.plugin, self.failures))
            else:
                collectd.info("%s %s no failures" %
                              (PLUGIN, self.plugin))

    ##########################################################################
    #
    # Name    : _get_instance_object
    #
    # Purpose : Safely get an object from the self instance object list
    #           indexed by eid.
    #
    ##########################################################################
    def _get_instance_object(self, eid):
        """Safely get an object from the self instance object dict while locked

        :param eid: the index for the instance object dictionary
        :return: object or None
        """

        try:
            collectd.debug("%s %s Get   Lock ..." % (PLUGIN, self.plugin))
            PluginObject.lock.acquire()

            obj = self.instance_objects[eid]
            return obj
        except:
            collectd.error("%s failed to get instance from %s object list" %
                           (PLUGIN, self.plugin))
            return None

        finally:
            collectd.debug("%s %s Get UnLock ..." % (PLUGIN, self.plugin))
            PluginObject.lock.release()

    ##########################################################################
    #
    # Name    : _add_instance_object
    #
    # Purpose : Safely add an object to the self instance object list
    #           indexed by eid while locked. if found locked the instance
    #           add will be re-attempted on next sample.
    #
    ##########################################################################
    def _add_instance_object(self, obj, eid):
        """Update self instance_objects list while locked

        :param obj: the object to add
        :param eid: index for instance_objects
        :return: nothing
        """
        try:
            collectd.debug("%s %s Add   Lock ..." % (PLUGIN, self.plugin))
            PluginObject.lock.acquire()

            self.instance_objects[eid] = obj
        except:
            collectd.error("%s failed to add instance to %s object list" %
                           (PLUGIN, self.plugin))

        finally:
            collectd.debug("%s %s Add UnLock ..." % (PLUGIN, self.plugin))
            PluginObject.lock.release()

    ##########################################################################
    #
    # Name    : _copy_instance_object
    #
    # Purpose : Copy select members of self object to target object.
    #
    ##########################################################################
    def _copy_instance_object(self, object):
        """Copy select members of self object to target object"""

        object.resource_name = self.resource_name
        object.instance_name = self.instance_name
        object.reading_type = self.reading_type

        object.reason_warning = self.reason_warning
        object.reason_failure = self.reason_failure
        object.repair = self.repair

        object.alarm_type = self.alarm_type
        object.cause = self.cause
        object.suppression = self.suppression
        object.service_affecting = self.service_affecting

    ##########################################################################
    #
    # Name    : _create_instance_object
    #
    # Purpose : Create a new instance object and tack it on the supplied base
    #           object's instance object dictionary.
    #
    ##########################################################################
    def _create_instance_object(self, instance):

        try:
            # create a new plugin object
            inst_obj = PluginObject(self.id, self.plugin)
            self._copy_instance_object(inst_obj)

            # initialize the object with instance specific data
            inst_obj.instance_name = instance
            inst_obj.entity_id = _build_entity_id(self.plugin,
                                                  instance)

            self._add_instance_object(inst_obj, inst_obj.entity_id)

            collectd.debug("%s created %s instance (%s) object %s" %
                           (PLUGIN, inst_obj.resource_name,
                            inst_obj.entity_id, inst_obj))

            collectd.info("%s monitoring %s %s %s" %
                          (PLUGIN,
                           inst_obj.resource_name,
                           inst_obj.instance_name,
                           inst_obj.reading_type))

            return inst_obj

        except:
            collectd.error("%s %s:%s inst object create failed" %
                           (PLUGIN, inst_obj.resource_name, instance))
        return None

    ##########################################################################
    #
    # Name    : _create_instance_objects
    #
    # Purpose : Create a list of instance objects for 'self' type plugin and
    #           add those objects to the parent's instance_objects dictionary.
    #
    # Note    : This is currently only used for the DF (filesystem) plugin.
    #           All other instance creations/allocations are done on-demand.
    #
    ##########################################################################
    def _create_instance_objects(self):
        """Create, initialize and add an instance object to this/self plugin"""

        # Create the File System subordinate instance objects.
        if self.id == ALARM_ID__DF:

            # read the df.conf file and return/get a list of mount points
            conf_file = PLUGIN_PATH + 'df.conf'
            if not os.path.exists(conf_file):
                collectd.error("%s cannot create filesystem "
                               "instance objects ; missing : %s" %
                               (PLUGIN, conf_file))
                return FAIL

            mountpoints = []
            with open(conf_file, 'r') as infile:
                for line in infile:
                    if 'MountPoint ' in line:

                        # get the mountpoint path from the line
                        try:
                            mountpoint = line.split('MountPoint ')[1][1:-2]
                            mountpoints.append(mountpoint)
                        except:
                            collectd.error("%s skipping invalid '%s' "
                                           "mountpoint line: %s" %
                                           (PLUGIN, conf_file, line))

            collectd.debug("%s MountPoints: %s" % (PLUGIN, mountpoints))

            # loop over the mount points
            for mp in mountpoints:
                # create a new plugin object
                inst_obj = PluginObject(ALARM_ID__DF, PLUGIN__DF)

                # initialize the object with instance specific data
                inst_obj.resource_name = self.resource_name
                inst_obj.instance_name = mp
                inst_obj.instance = mp
                # build the plugin instance name from the mount point
                if mp == '/':
                    inst_obj.plugin_instance = 'root'
                else:
                    inst_obj.plugin_instance = mp[1:].replace('/', '-')

                inst_obj.entity_id = _build_entity_id(PLUGIN__DF,
                                                      inst_obj.plugin_instance)

                # add this subordinate object to the parent's
                # instance object list
                self._add_instance_object(inst_obj, inst_obj.entity_id)

                collectd.info("%s monitoring %s usage" %
                              (PLUGIN, inst_obj.instance))


PluginObject.host = os.uname()[1]


# ADD_NEW_PLUGIN: add plugin to this table
# This instantiates the plugin objects
PLUGINS = {
    PLUGIN__CPU: PluginObject(ALARM_ID__CPU, PLUGIN__CPU),
    PLUGIN__MEM: PluginObject(ALARM_ID__MEM, PLUGIN__MEM),
    PLUGIN__DF: PluginObject(ALARM_ID__DF, PLUGIN__DF),
    PLUGIN__VSWITCH_CPU: PluginObject(ALARM_ID__VSWITCH_CPU,
                                      PLUGIN__VSWITCH_CPU),
    PLUGIN__VSWITCH_MEM: PluginObject(ALARM_ID__VSWITCH_MEM,
                                      PLUGIN__VSWITCH_MEM),
    PLUGIN__VSWITCH_PORT: PluginObject(ALARM_ID__VSWITCH_PORT,
                                       PLUGIN__VSWITCH_PORT),
    PLUGIN__VSWITCH_IFACE: PluginObject(ALARM_ID__VSWITCH_IFACE,
                                        PLUGIN__VSWITCH_IFACE),
    PLUGIN__EXAMPLE: PluginObject(ALARM_ID__EXAMPLE, PLUGIN__EXAMPLE)}


def _get_base_object(alarm_id):
    """Get the alarm object for the specified alarm id"""
    for plugin in PLUGIN_NAME_LIST:
        if PLUGINS[plugin].id == alarm_id:
            return PLUGINS[plugin]
    return None


def _get_object(alarm_id, eid):
    """Get the plugin object for the specified alarm id and eid"""

    base_obj = _get_base_object(alarm_id)
    if len(base_obj.instance_objects):
        try:
            return(base_obj.instance_objects[eid])
        except:
            collectd.debug("%s %s has no instance objects" %
                           (PLUGIN, base_obj.plugin))
    return base_obj


def _build_entity_id(plugin, plugin_instance):
    """Builds an entity id string based on the collectd notification object"""

    inst_error = False

    entity_id = 'host='
    entity_id += PluginObject.host

    if plugin == PLUGIN__MEM:
        if plugin_instance != 'platform':
            entity_id += '.numa=' + plugin_instance

    elif plugin == PLUGIN__VSWITCH_MEM:

        # host=<hostname>.processor=<socket-id>
        if plugin_instance:
            entity_id += '.processor=' + plugin_instance
        else:
            inst_error = True

    elif plugin == PLUGIN__VSWITCH_IFACE:

        # host=<hostname>.interface=<if-uuid>
        if plugin_instance:
            entity_id += '.interface=' + plugin_instance
        else:
            inst_error = True

    elif plugin == PLUGIN__VSWITCH_PORT:

        # host=<hostname>.port=<port-uuid>
        if plugin_instance:
            entity_id += '.port=' + plugin_instance
        else:
            inst_error = True

    elif plugin == PLUGIN__DF:

        # host=<hostname>.filesystem=<mountpoint>
        if plugin_instance:
            instance = plugin_instance

            # build the entity_id for this plugin
            entity_id += '.filesystem=/'

            # collectd replaces the instance '/' with the word 'root'
            # So skip over "root" as '/' is already part of the
            # entity_id
            if instance != 'root':
                # Look for other instances that are in the mangled list
                if instance in mangled_list:
                    instance = instance.replace('-', '/')
                entity_id += instance

    if inst_error is True:
        collectd.error("%s eid build failed ; missing instance" % plugin)
        return None

    return entity_id


def _get_df_mountpoints():

    conf_file = PLUGIN_PATH + 'df.conf'
    if not os.path.exists(conf_file):
        collectd.error("%s cannot create filesystem "
                       "instance objects ; missing : %s" %
                       (PLUGIN, conf_file))
        return FAIL

    mountpoints = []
    with open(conf_file, 'r') as infile:
        for line in infile:
            if 'MountPoint ' in line:

                # get the mountpoint path from the line
                try:
                    mountpoint = line.split('MountPoint ')[1][1:-2]
                    mountpoints.append(mountpoint)
                except:
                    collectd.error("%s skipping invalid '%s' "
                                   "mountpoint line: %s" %
                                   (PLUGIN, conf_file, line))

    return(mountpoints)


def _print_obj(obj):
    """Print a single object"""
    base_object = False
    for plugin in PLUGIN_NAME_LIST:
        if PLUGINS[plugin] == obj:
            base_object = True
            break

    num = len(obj.instance_objects)
    if num > 0 or base_object is True:
        prefix = "PLUGIN "
        if num:
            prefix += str(num)
        else:
            prefix += " "
    else:
        prefix = "INSTANCE"

    if obj.plugin_instance:
        resource = obj.plugin + ":" + obj.plugin_instance
    else:
        resource = obj.plugin

    collectd.info("%s %s res: %s name: %s\n" %
                  (PLUGIN, prefix, resource, obj.resource_name))
    collectd.info("%s     eid : %s\n" % (PLUGIN, obj.entity_id))
    collectd.info("%s     inst: %s name: %s\n" %
                  (PLUGIN, obj.instance, obj.instance_name))
    collectd.info("%s     value:%2.1f thld:%2.1f cause:%s (%d) type:%s" %
                  (PLUGIN,
                   obj.value,
                   obj.threshold,
                   obj.cause,
                   obj.count,
                   obj.reading_type))
    collectd.info("%s     warn:%s fail:%s" %
                  (PLUGIN, obj.warnings, obj.failures))
    collectd.info("%s     repair:t: %s" %
                  (PLUGIN, obj.repair))
    if obj.cause != fm_constants.ALARM_PROBABLE_CAUSE_50:
        collectd.info("%s     reason:w: %s\n"
                      "%s     reason:f: %s\n" %
                      (PLUGIN, obj.reason_warning,
                       PLUGIN, obj.reason_failure))
    # collectd.info(" ")


def _print_state(obj=None):
    """Print the current object state"""
    try:
        objs = []
        if obj is None:
            for plugin in PLUGIN_NAME_LIST:
                objs.append(PLUGINS[plugin])
        else:
            objs.append(obj)

        collectd.debug("%s _print_state Lock ..." % PLUGIN)
        PluginObject.lock.acquire()
        for o in objs:
            _print_obj(o)
            if len(o.instance_objects):
                for inst_obj in o.instance_objects:
                    _print_obj(o.instance_objects[inst_obj])
    finally:
        collectd.debug("%s _print_state UnLock ..." % PLUGIN)
        PluginObject.lock.release()


def _database_setup(database):
    """Setup the influx database for collectd resource samples"""

    collectd.info("%s setting up influxdb:%s database" %
                  (PLUGIN, database))

    error_str = ""

    # http://influxdb-python.readthedocs.io/en/latest/examples.html
    # http://influxdb-python.readthedocs.io/en/latest/api-documentation.html
    PluginObject.dbObj = InfluxDBClient('127.0.0.1', '8086', database)
    if PluginObject.dbObj:
        try:
            PluginObject.dbObj.create_database('collectd')

            ############################################################
            #
            # TODO: Read current retention period from service parameter
            #       Make it a puppet implementation.
            #
            # Create a 1 month samples retention policy
            # -----------------------------------------
            # name     = 'collectd samples'
            # duration = set retention period in time
            #               xm - minutes
            #               xh - hours
            #               xd - days
            #               xw - weeks
            #               xy - years
            # database = 'collectd'
            # default  = True ; make it the default
            #
            ############################################################

            PluginObject.dbObj.create_retention_policy(
                DATABASE_NAME, '4w', 1, database, True)
        except Exception as ex:
            if str(ex) == 'database already exists':
                try:
                    collectd.info("%s influxdb:collectd %s" %
                                  (PLUGIN, str(ex)))
                    PluginObject.dbObj.create_retention_policy(
                        DATABASE_NAME, '4w', 1, database, True)
                except Exception as ex:
                    if str(ex) == 'retention policy already exists':
                        collectd.info("%s influxdb:collectd %s" %
                                      (PLUGIN, str(ex)))
                    else:
                        error_str = "failure from influxdb ; "
                        error_str += str(ex)
            else:
                error_str = "failed to create influxdb:" + database
    else:
        error_str = "failed to connect to influxdb:" + database

    if not error_str:
            found = False
            retention = \
                PluginObject.dbObj.get_list_retention_policies(database)
            for r in range(len(retention)):
                if retention[r]["name"] == DATABASE_NAME:
                    collectd.info("%s influxdb:%s samples retention "
                                  "policy: %s" %
                                  (PLUGIN, database, retention[r]))
                    found = True
            if found is True:
                collectd.info("%s influxdb:%s is setup" % (PLUGIN, database))
                PluginObject.database_setup = True
            else:
                collectd.error("%s influxdb:%s retention policy NOT setup" %
                               (PLUGIN, database))


def _clear_alarm_for_missing_filesystems():
    """Clear alarmed file systems that are no longer mounted or present"""

    # get the DF (filesystem plugin) base object.
    df_base_obj = PLUGINS[PLUGIN__DF]
    # create a single alarm list from both wranings and failures list
    # to avoid having to duplicate the code below for each.
    # At this point we don't care about severity, we just need to
    # determine if an any-severity' alarmed filesystem no longer exists
    # so we can cleanup by clearing its alarm.
    # Note: the 2 lists shpould always contain unique data between them
    alarm_list = df_base_obj.warnings + df_base_obj.failures
    if len(alarm_list):
        for eid in alarm_list:
            # search for any of them that might be alarmed.
            obj = df_base_obj._get_instance_object(eid)

            # only care about df (file system plugins)
            if obj is not None and \
               obj.plugin == PLUGIN__DF and \
               obj.entity_id == eid and \
               obj.plugin_instance != 'root':

                # For all others replace all '-' with '/'
                path = '/' + obj.plugin_instance.replace('-', '/')
                if os.path.ismount(path) is False:
                    if api.clear_fault(df_base_obj.id, obj.entity_id) is False:
                        collectd.error("%s %s:%s clear failed ; will retry" %
                                       (PLUGIN, df_base_obj.id, obj.entity_id))
                    else:
                        collectd.info("%s cleared alarm for missing %s" %
                                      (PLUGIN, path))
                        df_base_obj._manage_alarm(obj.entity_id, "okay")
                else:
                    collectd.debug("%s maintaining alarm for %s" %
                                   (PLUGIN, path))


# Collectd calls this function on startup.
# Initialize each plugin object with plugin specific data.
# Query FM for existing alarms and run with that starting state.
def init_func():
    """Collectd FM Notifier Initialization Function"""

    PluginObject.lock = Lock()

    PluginObject.host = os.uname()[1]
    collectd.info("%s %s:%s init function" %
                  (PLUGIN, tsc.nodetype, PluginObject.host))

    # Constant CPU Plugin Object Settings
    obj = PLUGINS[PLUGIN__CPU]
    obj.resource_name = "Platform CPU"
    obj.instance_name = PLUGIN__CPU
    obj.repair = "Monitor and if condition persists, "
    obj.repair += "contact next level of support."
    collectd.info("%s monitoring %s usage" % (PLUGIN, obj.resource_name))

    ###########################################################################

    # Constant Memory Plugin Object settings
    obj = PLUGINS[PLUGIN__MEM]
    obj.resource_name = "Platform Memory"
    obj.instance_name = PLUGIN__MEM
    obj.repair = "Monitor and if condition persists, "
    obj.repair += "contact next level of support; "
    obj.repair += "may require additional memory on Host."
    collectd.info("%s monitoring %s usage" % (PLUGIN, obj.resource_name))

    ###########################################################################

    # Constant FileSystem Plugin Object settings
    obj = PLUGINS[PLUGIN__DF]
    obj.resource_name = "File System"
    obj.instance_name = PLUGIN__DF
    obj.repair = "Monitor and if condition persists, "
    obj.repair += "contact next level of support."

    # The FileSystem (DF) plugin has multiple instances
    # One instance per file system mount point being monitored.
    # Create one DF instance object per mount point
    obj._create_instance_objects()

    # ntp query is for controllers only
    if want_vswitch is False:
        collectd.debug("%s vSwitch monitoring disabled" % PLUGIN)
    elif tsc.nodetype == 'worker' or 'worker' in tsc.subfunctions:

        #######################################################################

        # Constant vSwitch CPU Usage Plugin Object settings
        obj = PLUGINS[PLUGIN__VSWITCH_CPU]
        obj.resource_name = "vSwitch CPU"
        obj.instance_name = PLUGIN__VSWITCH_CPU
        obj.repair = "Monitor and if condition persists, "
        obj.repair += "contact next level of support."
        collectd.info("%s monitoring %s usage" % (PLUGIN, obj.resource_name))

        #######################################################################

        # Constant vSwitch Memory Usage Plugin Object settings
        obj = PLUGINS[PLUGIN__VSWITCH_MEM]
        obj.resource_name = "vSwitch Memory"
        obj.instance_name = PLUGIN__VSWITCH_MEM
        obj.repair = "Monitor and if condition persists, "
        obj.repair += "contact next level of support."
        collectd.info("%s monitoring %s usage" % (PLUGIN, obj.resource_name))

        #######################################################################

        # Constant vSwitch Port State Monitor Plugin Object settings
        obj = PLUGINS[PLUGIN__VSWITCH_PORT]
        obj.resource_name = "vSwitch Port"
        obj.instance_name = PLUGIN__VSWITCH_PORT
        obj.reading_type = "state"
        obj.reason_failure = "'Data' Port failed."
        obj.reason_warning = "'Data' Port failed."
        obj.repair = "Check cabling and far-end port configuration and "
        obj.repair += "status on adjacent equipment."
        obj.alarm_type = fm_constants.FM_ALARM_TYPE_4     # EQUIPMENT
        obj.cause = fm_constants.ALARM_PROBABLE_CAUSE_29  # LOSS_OF_SIGNAL
        obj.service_affecting = True
        collectd.info("%s monitoring %s state" % (PLUGIN, obj.resource_name))

        #######################################################################

        # Constant vSwitch Interface State Monitor Plugin Object settings
        obj = PLUGINS[PLUGIN__VSWITCH_IFACE]
        obj.resource_name = "vSwitch Interface"
        obj.instance_name = PLUGIN__VSWITCH_IFACE
        obj.reading_type = "state"
        obj.reason_failure = "'Data' Interface failed."
        obj.reason_warning = "'Data' Interface degraded."
        obj.repair = "Check cabling and far-end port configuration and "
        obj.repair += "status on adjacent equipment."
        obj.alarm_type = fm_constants.FM_ALARM_TYPE_4     # EQUIPMENT
        obj.cause = fm_constants.ALARM_PROBABLE_CAUSE_29  # LOSS_OF_SIGNAL
        obj.service_affecting = True
        collectd.info("%s monitoring %s state" % (PLUGIN, obj.resource_name))

    ###########################################################################

    obj = PLUGINS[PLUGIN__EXAMPLE]
    obj.resource_name = "Example"
    obj.instance_name = PLUGIN__EXAMPLE
    obj.repair = "Not Applicable"
    collectd.info("%s monitoring %s usage" % (PLUGIN, obj.resource_name))

    if tsc.nodetype == 'controller':
        PluginObject.database_setup_in_progress = True
        _database_setup('collectd')
        PluginObject.database_setup_in_progress = False

    # ...
    # ADD_NEW_PLUGIN: Add new plugin object initialization here ...
    # ...

    ######################################################################
    #
    # With plugin objects initialized ...
    # Query FM for any resource alarms that may already be raised
    # Load the queries severity state into the appropriate
    # severity list for those that are.
    for alarm_id in ALARM_ID_LIST:
        collectd.debug("%s searching for all '%s' alarms " %
                       (PLUGIN, alarm_id))
        alarms = api.get_faults_by_id(alarm_id)
        if alarms:
            for alarm in alarms:
                want_alarm_clear = False
                eid = alarm.entity_instance_id
                # ignore alarms not for this host
                if PluginObject.host not in eid:
                    continue

                base_obj = _get_base_object(alarm_id)
                if base_obj is None:

                    # might be a plugin instance - clear it
                    want_alarm_clear = True

                collectd.info('%s found %s %s alarm [%s]' %
                              (PLUGIN,
                               alarm.severity,
                               alarm_id,
                               eid))

                if want_alarm_clear is True:

                    if api.clear_fault(alarm_id, eid) is False:
                        collectd.error("%s %s:%s clear failed" %
                                       (PLUGIN,
                                        alarm_id,
                                        eid))
                    else:
                        collectd.info("%s clear %s %s alarm %s" %
                                      (PLUGIN,
                                       alarm.severity,
                                       alarm_id,
                                       eid))
                    continue

                if alarm.severity == "critical":
                    sev = "failure"
                elif alarm.severity == "major":
                    sev = "warning"
                else:
                    sev = "okay"
                    continue

                # Load the alarm severity by doing a plugin/instance lookup.
                if base_obj is not None:
                    base_obj._manage_alarm(eid, sev)


# The notifier function inspects the collectd notification and determines if
# the representative alarm needs to be asserted, severity changed, or cleared.
def notifier_func(nObject):

    collectd.debug('%s notification: %s %s:%s - %s %s %s [%s]' % (
        PLUGIN,
        nObject.host,
        nObject.plugin,
        nObject.plugin_instance,
        nObject.type,
        nObject.type_instance,
        nObject.severity,
        nObject.message))

    # Load up severity variables and alarm actions based on
    # this notification's severity level.
    if nObject.severity == NOTIF_OKAY:
        severity_str = "okay"
        _severity_num = fm_constants.FM_ALARM_SEVERITY_CLEAR
        _alarm_state = fm_constants.FM_ALARM_STATE_CLEAR
    elif nObject.severity == NOTIF_FAILURE:
        severity_str = "failure"
        _severity_num = fm_constants.FM_ALARM_SEVERITY_CRITICAL
        _alarm_state = fm_constants.FM_ALARM_STATE_SET
    elif nObject.severity == NOTIF_WARNING:
        severity_str = "warning"
        _severity_num = fm_constants.FM_ALARM_SEVERITY_MAJOR
        _alarm_state = fm_constants.FM_ALARM_STATE_SET
    else:
        collectd.debug('%s with unsupported severity %d' %
                       (PLUGIN, nObject.severity))
        return 0

    if tsc.nodetype == 'controller':
        if PluginObject.database_setup is False:
            if PluginObject.database_setup_in_progress is False:
                PluginObject.database_setup_in_progress = True
                _database_setup('collectd')
                PluginObject.database_setup_in_progress = False

    # get plugin object
    if nObject.plugin in PLUGINS:
        base_obj = obj = PLUGINS[nObject.plugin]

        # if this notification is for a plugin instance then get that
        # instances's object instead.
        # If that object does not yet exists then create it.
        eid = ''

        # DF instances are statically allocated
        if nObject.plugin == PLUGIN__DF:
            eid = _build_entity_id(nObject.plugin, nObject.plugin_instance)

            # get this instances object
            obj = base_obj._get_instance_object(eid)
            if obj is None:
                # path should never be hit since all DF instances
                # are statically allocated.
                return 0

        elif nObject.plugin_instance:
            need_instance_object_create = False
            # Build the entity_id from the parent object if needed
            # Build the entity_id from the parent object if needed
            eid = _build_entity_id(nObject.plugin, nObject.plugin_instance)
            try:
                # Need lock when reading/writing any obj.instance_objects list
                collectd.debug("%s %s lock" % (PLUGIN, nObject.plugin))
                PluginObject.lock.acquire()

                # collectd.info("%s Object Search eid: %s" %
                #               (nObject.plugin, eid))

                # for o in base_obj.instance_objects:
                #     collectd.error("%s %s inst object dict item %s : %s" %
                #                    (PLUGIN, nObject.plugin, o,
                #                     base_obj.instance_objects[o]))

                # we will take an exception if this object is not in the list.
                # the exception handling code below will create and add this
                # object for success path the next time around.
                inst_obj = base_obj.instance_objects[eid]

                collectd.debug("%s %s instance %s already exists %s" %
                               (PLUGIN, nObject.plugin, eid, inst_obj))
                # _print_state(inst_obj)

            except:
                need_instance_object_create = True
            finally:
                collectd.debug("%s %s unlock" % (PLUGIN, nObject.plugin))
                PluginObject.lock.release()

            if need_instance_object_create is True:
                base_obj._create_instance_object(nObject.plugin_instance)
                inst_obj = base_obj._get_instance_object(eid)
                if inst_obj:
                    collectd.debug("%s %s:%s inst object created" %
                                   (PLUGIN,
                                    inst_obj.plugin,
                                    inst_obj.instance))
                else:
                    collectd.error("%s %s:%s inst object create failed" %
                                   (PLUGIN,
                                    nObject.plugin,
                                    nObject.plugin_instance))
                    return 0

            # re-assign the object
            obj = inst_obj
        else:
            if not len(base_obj.entity_id):
                # Build the entity_id from the parent object if needed
                eid = _build_entity_id(nObject.plugin, nObject.plugin_instance)

        # update the object with the eid if its not already set.
        if not len(obj.entity_id):
            obj.entity_id = eid

    else:
        collectd.debug("%s notification for unknown plugin: %s %s" %
                       (PLUGIN, nObject.plugin, nObject.plugin_instance))
        return 0

    # if obj.warnings or obj.failures:
    #     _print_state(obj)

    # If want_state_audit is True then run the audit.
    # Primarily used for debug
    # default state is False
    # TODO: comment out for production code.
    if want_state_audit:
        obj.audit_threshold += 1
        if obj.audit_threshold == DEBUG_AUDIT:
            obj.audit_threshold = 0
            obj._state_audit("audit")

    # manage reading value change ; store last and log if gt obj.step
    action = obj._manage_change(nObject)
    if action == "done":
        return 0

    # increment just before any possible return for a valid sample
    obj.count += 1

    # audit file system presence every time we get the
    # notification for the root file system ; which will
    # always be there.
    if obj.instance == 'df_root':
        _clear_alarm_for_missing_filesystems()

    # exit early if there is no severity change
    if base_obj._severity_change(obj.entity_id, severity_str) is False:
        return 0

    if _alarm_state == fm_constants.FM_ALARM_STATE_CLEAR:
        if api.clear_fault(obj.id, obj.entity_id) is False:
            collectd.error("%s %s:%s clear_fault failed" %
                           (PLUGIN, base_obj.id, obj.entity_id))
            return 0
    else:

        # manage addition of the failure reason text
        if obj.cause == fm_constants.ALARM_PROBABLE_CAUSE_50:
            # if this is a threshold alarm then build the reason text that
            # includes the threahold and the reading that caused the assertion.
            reason = obj.resource_name
            reason += " threshold exceeded ;"
            if obj.threshold != INVALID_THRESHOLD:
                reason += " threshold {:2.0f}".format(obj.threshold) + "%,"
            if obj.value:
                reason += " actual {:2.0f}".format(obj.value) + "%"

        elif _severity_num == fm_constants.FM_ALARM_SEVERITY_CRITICAL:
            reason = obj.reason_failure

        else:
            reason = obj.reason_warning

        # build the alarm object
        fault = fm_api.Fault(
            alarm_id=obj.id,
            alarm_state=_alarm_state,
            entity_type_id=fm_constants.FM_ENTITY_TYPE_HOST,
            entity_instance_id=obj.entity_id,
            severity=_severity_num,
            reason_text=reason,
            alarm_type=base_obj.alarm_type,
            probable_cause=base_obj.cause,
            proposed_repair_action=base_obj.repair,
            service_affecting=base_obj.service_affecting,
            suppression=base_obj.suppression)

        alarm_uuid = api.set_fault(fault)
        if pc.is_uuid_like(alarm_uuid) is False:
            collectd.error("%s %s:%s set_fault failed:%s" %
                           (PLUGIN, base_obj.id, obj.entity_id, alarm_uuid))
            return 0

    # update the lists now that
    base_obj._manage_alarm(obj.entity_id, severity_str)

    collectd.info("%s %s alarm %s:%s %s:%s value:%2.2f" % (
                  PLUGIN,
                  _alarm_state,
                  base_obj.id,
                  severity_str,
                  obj.instance,
                  obj.entity_id,
                  obj.value))

    # Debug only: comment out for production code.
    # obj._state_audit("change")

    return 0


collectd.register_init(init_func)
collectd.register_notification(notifier_func)
