#
# Copyright (c) 2018 Wind River Systems, Inc.
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
#    object.host              - the hostname
#
#    object.plugin            - the name of the plugin aka resource
#    object.plugin_instance   - plugin instance string i.e. say mountpoint
#                               for df plugin
#    object.type,             - the unit i.e. percent or absolute
#    object.type_instance     - the attribute i.e. free, used, etc
#
#    object.severity          - a integer value 0=OK , 1=warning, 2=failure
#    object.message           - a log-able message containing the above along
#                               with the value
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
from fm_api import constants as fm_constants
from fm_api import fm_api
import tsconfig.tsconfig as tsc

# only load influxdb on the controller
if tsc.nodetype == 'controller':
    from influxdb import InfluxDBClient

api = fm_api.FaultAPIs()

# Debug control
debug = False
debug_lists = False
want_state_audit = False

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
                "opt-extension",
                "opt-backups"}

# ADD_NEW_PLUGIN: add new alarm id definition
ALARM_ID__CPU = "100.101"
ALARM_ID__MEM = "100.103"
ALARM_ID__DF = "100.104"
ALARM_ID__EXAMPLE = "100.113"

# ADD_NEW_PLUGIN: add new alarm id to the list
ALARM_ID_LIST = [ALARM_ID__CPU,
                 ALARM_ID__MEM,
                 ALARM_ID__DF,
                 ALARM_ID__EXAMPLE]

# ADD_NEW_PLUGIN: add plugin name definition
# WARNING: This must line up exactly with the plugin
#          filename without the extension.
PLUGIN__DF = "df"
PLUGIN__CPU = "cpu"
PLUGIN__MEM = "memory"
PLUGIN__INTERFACE = "interface"
PLUGIN__NTP_QUERY = "ntpq"
PLUGIN__VSWITCH_PORT = "vswitch-port"
PLUGIN__VSWITCH_CPU = "vswitch-cpu"
PLUGIN__VSWITCH_MEM = "vswitch-memory"
PLUGIN__VSWITCH_OVSDB = "vswitch-ovsdb"
PLUGIN__VSWITCH_OPENFLOW = "vswitch-openflow"
PLUGIN__VSWITCH_LACP_IFACE = "vswitch-lacp-iface"
PLUGIN__VSWITCH_IFACE = "vswitch-iface"
PLUGIN__NOVA_THINPOOL_LVM = "nova-thinpool-lvm"
PLUGIN__CINDER_THINPOOL_LVM = "cinder-thinpool-lvm"
PLUGIN__CINDER_THINPOOL_LVM_META = "cinder-thinpool-lvm-meta"
PLUGIN__EXAMPLE = "example"

# ADD_NEW_PLUGIN: add plugin name to list
PLUGIN_NAME_LIST = [PLUGIN__CPU,
                    PLUGIN__MEM,
                    PLUGIN__DF,
                    PLUGIN__EXAMPLE]


# ADD_NEW_PLUGIN: add alarm id and plugin to dictionary
# ALARM_ID_TO_PLUGIN_DICT = {}
# ALARM_ID_TO_PLUGIN_DICT[ALARM_ID__CPU] = PLUGIN__CPU
# ALARM_ID_TO_PLUGIN_DICT[ALARM_ID__MEM] = PLUGIN__MEM
# ALARM_ID_TO_PLUGIN_DICT[ALARM_ID__DF] = PLUGIN__DF
# ALARM_ID_TO_PLUGIN_DICT[ALARM_ID__EXAMPLE] = PLUGIN__EXAMPLE


# PluginObject Class
class PluginObject:

    dbObj = None                           # shared database connection obj
    host = None                            # saved hostname
    database_setup = False                 # state of database setup
    database_setup_in_progress = False     # connection mutex

    def __init__(self, id, plugin):
        """
        PluginObject Class constructor
        """

        # plugin specific static class members.
        self.id = id               # alarm id ; 100.1??
        self.plugin = plugin       # name of the plugin ; df, cpu, memory ...
        self.plugin_instance = ""  # the instance name for the plugin
        self.resource_name = ""    # The top level name of the resource
        self.instance_name = ""    # The instanhce name

        # Instance specific learned static class members.
        self.entity_id = ""        # fm entity id host=<hostname>.<instance>
        self.instance = ""         # <plugin>_<instance>

        # [ 'float value string','float threshold string]
        self.values = []
        self.threshold = float(0)  # float value of threshold
        self.value = float(0)      # float value of reading

        # Common static class members.
        self.repair = ""
        self.alarm_type = fm_constants.FM_ALARM_TYPE_7
        self.cause = fm_constants.ALARM_PROBABLE_CAUSE_50
        self.suppression = True
        self.service_affecting = False

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
        # This dictionary is used to associate a instance with its object.
        self.instance_objects = {}

    def _ilog(self, string):
        """
        Create a collectd notifier info log with the specified string.
        """
        collectd.info('%s %s : %s' % (PLUGIN, self.plugin, string))

    def _llog(self, string):
        """
        Create a collectd notifier info log with the specified string
        if debug_lists is True.
        """
        if debug_lists:
            collectd.info('%s %s : %s' % (PLUGIN, self.plugin, string))

    def _elog(self, string):
        """
        Create a collectd notifier error log with the specified string.
        """
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
        """ Log the state of the specified object. """

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
    #           Parse the notification log
    #           Generate a log entry if the sample value changes more than
    #             step value.
    #
    ##########################################################################

    def _manage_change(self, nObject):
        """ Log resource instance value on step state change. """

        # filter out messages to ignore ; notifications that have no value
        if "has not been updated for" in nObject.message:
            collectd.debug("%s NOT UPDATED: %s" % (PLUGIN, self.entity_id))
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
                # get the threshold if its there
                if len(self.values) == 2:
                    self.threshold = float(self.values[1])

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
            reading_type = "% usage"
            tmp = str(self.value).split('.')
            if len(tmp[0]) == 1:
                pre = ':  '
            else:
                pre = ': '
            collectd.info("%s reading%s%2.2f %s - %s" %
                          (PLUGIN,
                           pre,
                           self.value,
                           reading_type,
                           self.instance_name))
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
        """
        Check for a severity change
        """

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
        """
        Manage the alarm severity lists and report state change.
        """

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
    # Name    : _create_instance_objects
    #
    # Purpose : Create a list of instance objects for 'self' type plugin and
    #           add those objects to the parnet's instance_objects dictionary.
    #
    ##########################################################################
    def _create_instance_objects(self):
        """
        Create, initialize and add an instance object to this/self plugin
        """

        # ADD_NEW_PLUGIN: for plugins that have instances you need to
        #                 add support for creating those instances and adding
        #                 those instances to the parent instance_objects list.

        # Currently only the DF plugin has subordinate instance objects.
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
                # build the plugin instance name from the mount point
                if mp == '/':
                    inst_obj.plugin_instance = 'root'
                else:
                    inst_obj.plugin_instance = mp[1:].replace('/', '-')

                inst_obj.entity_id = _build_entity_id(PLUGIN__DF,
                                                      inst_obj.plugin_instance)

                # add this subordinate object to the parent's
                # instance object list
                self.instance_objects[inst_obj.entity_id] = inst_obj

                collectd.info("%s monitoring %s usage" %
                              (PLUGIN, mp))


PluginObject.host = os.uname()[1]


# ADD_NEW_PLUGIN: add plugin to this table
# This instanciates the plugin objects
PLUGINS = {PLUGIN__CPU: PluginObject(ALARM_ID__CPU, PLUGIN__CPU),
           PLUGIN__MEM: PluginObject(ALARM_ID__MEM, PLUGIN__MEM),
           PLUGIN__DF: PluginObject(ALARM_ID__DF, PLUGIN__DF),
           PLUGIN__EXAMPLE: PluginObject(ALARM_ID__EXAMPLE, PLUGIN__EXAMPLE)}


def _get_base_object(alarm_id):
    """
    Get the alarm object for the specified alarm id.
    """
    for plugin in PLUGIN_NAME_LIST:
        if PLUGINS[plugin].id == alarm_id:
            return PLUGINS[plugin]
    return None


def _get_object(alarm_id, eid):
    """
    Get the plugin object for the specified alarm id and eid
    """

    base_obj = _get_base_object(alarm_id)
    if len(base_obj.instance_objects):
        try:
            return(base_obj.instance_objects[eid])
        except:
            collectd.debug("%s %s has no instance objects" %
                           (PLUGIN, base_obj.plugin))
    return base_obj


def is_uuid_like(val):
    """Returns validation of a value as a UUID.

    For our purposes, a UUID is a canonical form string:
    aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
    """
    try:
        return str(uuid.UUID(val)) == val
    except (TypeError, ValueError, AttributeError):
        return False


def _build_entity_id(plugin, plugin_instance):
    """
    Builds an entity id string based on the collectd notification object.
    """

    entity_id = 'host='
    entity_id += PluginObject.host

    if plugin == PLUGIN__DF:
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

    # collectd.info("%s entity_id : %s" % (PLUGIN, entity_id))

    return entity_id


def _get_df_mountpoints():
    """
    """

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


def _print_state(obj=None):
    """
    Print the current object state
    """
    objs = []
    if obj is None:
        objs.append(_get_base_object(ALARM_ID__CPU))
        objs.append(_get_base_object(ALARM_ID__MEM))
        objs.append(_get_base_object(ALARM_ID__DF))
    else:
        objs.append(obj)
    for o in objs:
        collectd.info("%s PLUGIN %2d [%6s:%2.2f:%s] [w:%s f:%s] %d" %
                      (PLUGIN,
                       len(o.instance_objects),
                       o.plugin,
                       o.value,
                       o.entity_id,
                       o.warnings,
                       o.failures,
                       o.count))
        if len(o.instance_objects):
            for inst_obj in o.instance_objects:
                collectd.info("%s INSTANCE [%6s:%2.2f:%s] [w:%s f:%s] %d" %
                              (PLUGIN,
                               inst_obj.plugin,
                               inst_obj.value,
                               inst_obj.entity_id,
                               inst_obj.warnings,
                               inst_obj.failures,
                               inst_obj.count))


def _database_setup(database):
    """
    Setup the influx database for collectd resource samples
    """

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
                'collectd samples', '4w', 1, database, True)
        except Exception as ex:
            if str(ex) == 'database already exists':
                try:
                    collectd.info("%s influxdb:collectd %s" %
                                  (PLUGIN, str(ex)))
                    PluginObject.dbObj.create_retention_policy(
                        'collectd samples', '4w', 1, database, True)
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
            retention = \
                PluginObject.dbObj.get_list_retention_policies(database)
            collectd.info("%s influxdb:%s samples retention policy: %s" %
                          (PLUGIN, database, retention))
            collectd.info("%s influxdb:%s is setup" % (PLUGIN, database))
            PluginObject.database_setup = True
    else:
        collectd.error("%s influxdb:%s setup %s" %
                       (PLUGIN, database, error_str))


def _clear_alarm_for_missing_filesystems():
    """
    Clear alarmed file systems that are no longer mounted or present
    """

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
            obj = df_base_obj.instance_objects[eid]

            # only care about df (file system plugins)
            if obj.plugin == PLUGIN__DF and \
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
    return 0


# Collectd calls this function on startup.
# Initialize each plugin object with plugin specific data.
# Query FM for existing alarms and run with that starting state.
def init_func():
    """ Collectd FM Notifier Initialization Function """

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

    # Constant Memory Plugin Object settings
    obj = PLUGINS[PLUGIN__MEM]
    obj.resource_name = "Memory"
    obj.instance_name = PLUGIN__MEM
    obj.repair = "Monitor and if condition persists, "
    obj.repair += "contact next level of support; "
    obj.repair += "may require additional memory on Host."
    collectd.info("%s monitoring %s usage" % (PLUGIN, obj.resource_name))

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
                eid = alarm.entity_instance_id
                # ignore alarms not for this host
                if PluginObject.host not in eid:
                    continue

                base_obj = _get_base_object(alarm_id)
                if base_obj is None:
                    # Handle unrecognized alarm by clearing it ;
                    # should never happen since we are iterating
                    # over an internal alarm_id list.
                    if api.clear_fault(alarm_id, eid) is False:
                        collectd.error("%s %s:%s not found ; clear failed" %
                                       (PLUGIN,
                                        alarm_id,
                                        eid))
                    else:
                        collectd.error("%s %s:%s not found ; cleared" %
                                       (PLUGIN,
                                        alarm_id,
                                        eid))
                    continue

                collectd.info('%s found %s alarm with %s severity [%s:%s:%s]' %
                              (PLUGIN,
                               base_obj.id,
                               alarm.severity,
                               base_obj.plugin,
                               alarm_id,
                               eid))
                if alarm.severity == "critical":
                    sev = "failure"
                elif alarm.severity == "major":
                    sev = "warning"
                else:
                    sev = "okay"
                    continue

                # Load the alarm severity by doing a plugin/instance lookup.
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
        # instances's object instead. if that object does not yet exists
        # then create it
        eid = ''
        if nObject.plugin_instance:
            # Build the entity_id from the parent object if needed
            eid = _build_entity_id(nObject.plugin, nObject.plugin_instance)
            try:
                inst_obj = base_obj.instance_objects[eid]
                if inst_obj is None:
                    collectd.error("%s %s:%s instance object is None" %
                                   (PLUGIN,
                                    nObject.plugin,
                                    nObject.plugin_instance))
                    return 0
            except:
                # o.k. , not in the list yet, lets create one
                collectd.error("%s %s:%s instance object not found" %
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

        # TODO: Needed ?
        if not len(obj.instance):
            obj.instance = nObject.plugin
            if nObject.plugin_instance:
                obj.instance += '_' + nObject.plugin_instance

        # TODO: Needed ?
        # update the object with the eid if its not already set.
        if not len(obj.entity_id):
            obj.entity_id = eid

    else:
        collectd.debug("%s notification for unknown plugin: %s %s" %
                      (PLUGIN, nObject.plugin, nObject.plugin_instance))
        return 0

    # _print_state(obj)

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
        if api.clear_fault(base_obj.id, obj.entity_id) is False:
            collectd.error("%s %s:%s clear_fault failed" %
                           (PLUGIN, base_obj.id, obj.entity_id))
            return 0
    else:
        reason = obj.resource_name
        reason += " threshold exceeded"
        if obj.threshold:
            reason += "; {:2.0f}".format(obj.threshold) + "%"
            # reason += "; {:2.2f}".format(obj.threshold) + "%"
        if obj.value:
            reason += ", actual " + "{:2.0f}".format(obj.value) + "%"

        fault = fm_api.Fault(
            alarm_id=base_obj.id,
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
        if is_uuid_like(alarm_uuid) is False:
            collectd.error("%s %s:%s set_fault failed:%s" %
                           (PLUGIN, base_obj.id, obj.entity_id, alarm_uuid))
            return 0

    # update the lists now that
    base_obj._manage_alarm(obj.entity_id, severity_str)

    collectd.info("%s %s alarm %s:%s %s:%s thld:%2.2f value:%2.2f" % (
                  PLUGIN,
                  _alarm_state,
                  base_obj.id,
                  severity_str,
                  obj.instance,
                  obj.entity_id,
                  obj.threshold,
                  obj.value))

    # Debug only: comment out for production code.
    # obj._state_audit("change")

collectd.register_init(init_func)
collectd.register_notification(notifier_func)
