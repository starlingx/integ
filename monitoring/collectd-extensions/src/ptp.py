#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
############################################################################
#
# This file is the collectd 'Precision Time Protocol' Service Monitor.
#
# Algorithm:
#
# while not config ; check again
# while not init ; retry
# if startup
#   clear all ptp alarms
# if ptp enabled
#   if ptp not running
#     raise 'process' alarm
#  else
#     read grand master and current skew
#     if not controller and is grand master
#       raise 'no lock' alarm
#     if skew is out-of-tolerance
#       raise out-of-tolerance alarm
#
#
#  manage alarm state throught
#     retry on alarm state change failures
#     only make raise/clear alarm calls on severity state changes
#
############################################################################
import os
import collectd
import subprocess
import tsconfig.tsconfig as tsc
import plugin_common as pc
from fm_api import constants as fm_constants
from fm_api import fm_api

debug = False

# Fault manager API Object
api = fm_api.FaultAPIsV2()

PLUGIN_ALARMID = "100.119"

# name of the plugin - all logs produced by this plugin are prefixed with this
PLUGIN = 'ptp plugin'

# Service name
PTP = 'Precision Time Protocol (PTP)'

# Interface Monitoring Interval in seconds
PLUGIN_AUDIT_INTERVAL = 60

# Sample Data 'type' and 'instance' database field values.
PLUGIN_TYPE = 'time_offset'
PLUGIN_TYPE_INSTANCE = 'nsec'

# Primary PTP service name
PLUGIN_SERVICE = 'ptp4l.service'

# Plugin configuration file
#
# This plugin looks for the timestamping mode in the ptp4l config file.
#   time_stamping           hardware
#
PLUGIN_CONF_FILE = '/etc/ptp4l.conf'
PLUGIN_CONF_TIMESTAMPING = 'time_stamping'

# Tools used by plugin
SYSTEMCTL = '/usr/bin/systemctl'
ETHTOOL = '/usr/sbin/ethtool'
PLUGIN_STATUS_QUERY_EXEC = '/usr/sbin/pmc'

# Query PTP service administrative (enabled/disabled) state
#
# > systemctl is-enabled ptp4l
# enabled
# > systemctl disable ptp4l
# > systemctl is-enabled ptp4l
# disabled

SYSTEMCTL_IS_ENABLED_OPTION = 'is-enabled'
SYSTEMCTL_IS_ENABLED_RESPONSE = 'enabled'
SYSTEMCTL_IS_DISABLED_RESPONSE = 'disabled'

# Query PTP service activity (active=running / inactive) state
#
# > systemctl is-active ptp4l
# active
# > systemctl stop ptp4l
# > systemctl is-active ptp4l
# inactive

SYSTEMCTL_IS_ACTIVE_OPTION = 'is-active'
SYSTEMCTL_IS_ACTIVE_RESPONSE = 'active'
SYSTEMCTL_IS_INACTIVE_RESPONSE = 'inactive'

# Alarm Cause codes ; used to specify what alarm EID to assert or clear.
ALARM_CAUSE__NONE = 0
ALARM_CAUSE__PROCESS = 1
ALARM_CAUSE__OOT = 2
ALARM_CAUSE__NO_LOCK = 3
ALARM_CAUSE__UNSUPPORTED_HW = 4
ALARM_CAUSE__UNSUPPORTED_SW = 5
ALARM_CAUSE__UNSUPPORTED_LEGACY = 6

# Run Phase
RUN_PHASE__INIT = 0
RUN_PHASE__DISABLED = 1
RUN_PHASE__NOT_RUNNING = 2
RUN_PHASE__SAMPLING = 3

# Clock Sync Out-Of-Tolerance thresholds
OOT_MINOR_THRESHOLD = int(1000)
OOT_MAJOR_THRESHOLD = int(1000000)

# Instantiate the common plugin control object
obj = pc.PluginObject(PLUGIN, "")


# Create an alarm management class
class PTP_alarm_object:

    def __init__(self, interface=None):

        self.severity = fm_constants.FM_ALARM_SEVERITY_CLEAR
        self.cause = fm_constants.ALARM_PROBABLE_CAUSE_50
        self.alarm = ALARM_CAUSE__NONE
        self.interface = interface
        self.raised = False
        self.reason = ''
        self.repair = ''
        self.eid = ''


# Plugin specific control class and object.
class PTP_ctrl_object:

    def __init__(self):

        self.gm_log_throttle = 0
        self.nolock_alarm_object = None
        self.process_alarm_object = None
        self.oot_alarm_object = None


ctrl = PTP_ctrl_object()


# Alarm object list, one entry for each interface and alarm cause case
ALARM_OBJ_LIST = []


# UT verification utilities
def assert_all_alarms():
    for o in ALARM_OBJ_LIST:
        raise_alarm(o.alarm, o.interface, 0)


def clear_all_alarms():
    for o in ALARM_OBJ_LIST:
        if clear_alarm(o.eid) is True:
            msg = 'cleared'
        else:
            msg = 'clear failed'
        collectd.info("%s %s:%s alarm %s" %
                      (PLUGIN, PLUGIN_ALARMID, o.eid, msg))


def print_alarm_object(o):
    collectd.info("%s Interface:%s  Cause: %d  Severity:%s  Raised:%d" %
                  (PLUGIN,
                   o.interface,
                   o.alarm,
                   o.severity,
                   o.raised))
    collectd.info("%s Entity:[%s]" % (PLUGIN, o.eid))
    collectd.info("%s Reason:[%s]" % (PLUGIN, o.reason))
    collectd.info("%s Repair:[%s]" % (PLUGIN, o.repair))


def print_alarm_objects():
    for o in ALARM_OBJ_LIST:
        print_alarm_object(o)


# Interface:Supported Modes dictionary. key:value
#
# interface:modes
#
interfaces = {}


#####################################################################
#
# Name       : _get_supported_modes
#
# Description: Invoke ethtool -T <interface> and load its
#              time stamping capabilities.
#
#                 hardware, software or legacy.
#
# Parameters : The name of the physical interface to query the
#              supported modes for.
#
# Interface Capabilities Output Examples:
#
# vbox prints this as it only supports software timestamping
#    software-transmit     (SOF_TIMESTAMPING_TX_SOFTWARE)
#    software-receive      (SOF_TIMESTAMPING_RX_SOFTWARE)
#
# full support output looks like this
#    hardware-transmit     (SOF_TIMESTAMPING_TX_HARDWARE)
#    software-transmit     (SOF_TIMESTAMPING_TX_SOFTWARE)
#    hardware-receive      (SOF_TIMESTAMPING_RX_HARDWARE)
#    software-receive      (SOF_TIMESTAMPING_RX_SOFTWARE)
#    hardware-raw-clock    (SOF_TIMESTAMPING_RAW_HARDWARE)
#
# Only legacy support output looks like this
#    hardware-raw-clock    (SOF_TIMESTAMPING_RAW_HARDWARE)
#
# Provisionable PTP Modes are
#    hardware   -> hardware-transmit/receive
#    software   -> software-transmit/receive
#    legacy     -> hardware-raw-clock

TIMESTAMP_MODE__HW = 'hardware'
TIMESTAMP_MODE__SW = 'software'
TIMESTAMP_MODE__LEGACY = 'legacy'


#
# Returns  : a list of supported modes
#
#####################################################################
def _get_supported_modes(interface):
    """Get the supported modes for the specified interface"""

    hw_tx = hw_rx = sw_tx = sw_rx = False
    modes = []
    data = subprocess.check_output([ETHTOOL, '-T', interface]).split('\n')
    if data:
        collectd.debug("%s 'ethtool -T %s' output:%s\n" %
                       (PLUGIN, interface, data))
        check_for_modes = False
        for i in range(0, len(data)):
            collectd.debug("%s data[%d]:%s\n" % (PLUGIN, i, data[i]))
            if 'Capabilities' in data[i]:

                # start of capabilities list
                check_for_modes = True

            elif check_for_modes is True:

                if 'PTP Hardware Clock' in data[i]:
                    # no more modes after this label
                    break
                elif 'hardware-transmit' in data[i]:
                    hw_tx = True
                elif 'hardware-receive' in data[i]:
                    hw_rx = True
                elif 'software-transmit' in data[i]:
                    sw_tx = True
                elif 'software-receive' in data[i]:
                    sw_rx = True
                elif 'hardware-raw-clock' in data[i]:
                    modes.append(TIMESTAMP_MODE__LEGACY)

        if sw_tx is True and sw_rx is True:
            modes.append(TIMESTAMP_MODE__SW)

        if hw_tx is True and hw_rx is True:
            modes.append(TIMESTAMP_MODE__HW)

        if modes:
            collectd.debug("%s %s interface PTP capabilities: %s" %
                           (PLUGIN, interface, modes))
        else:
            collectd.info("%s no capabilities advertised for %s" %
                          (PLUGIN, interface))

    else:
        collectd.info("%s no ethtool output for %s" % (PLUGIN, interface))
        return None

    return modes


#####################################################################
#
# Name       : get_alarm_object
#
# Description: Search the alarm list based on the alarm cause
#              code and interface.
#
# Returns    : Alarm object if found ; otherwise None
#
#####################################################################
def get_alarm_object(alarm, interface=None):
    """Alarm object lookup"""

    for o in ALARM_OBJ_LIST:
        # print_alarm_object(o)
        if interface is None:
            if o.alarm == alarm:
                return o
        else:
            if o.interface == interface:
                if o.alarm == alarm:
                    return o

    collectd.info("%s alarm object lookup failed ; %d:%s" %
                  (PLUGIN, alarm, interface))
    return None


#####################################################################
#
# Name       : clear_alarm
#
# Description: Clear the ptp alarm with the specified entity ID.
#
# Returns    : True if operation succeeded
#              False if there was an error exception.
#
# Assumptions: Caller can decide to retry based on return status.
#
#####################################################################
def clear_alarm(eid):
    """Clear the ptp alarm with the specified entity ID"""

    try:
        if api.clear_fault(PLUGIN_ALARMID, eid) is True:
            collectd.info("%s %s:%s alarm cleared" %
                          (PLUGIN, PLUGIN_ALARMID, eid))
        else:
            collectd.info("%s %s:%s alarm clear ; None found" %
                          (PLUGIN, PLUGIN_ALARMID, eid))
        return True

    except Exception as ex:
        collectd.error("%s 'clear_fault' exception ; %s:%s ; %s" %
                       (PLUGIN, PLUGIN_ALARMID, eid, ex))
        return False


#####################################################################
#
# Name       : raise_alarm
#
# Description: Assert a specific PTP alarm based on the alarm cause
#              code and interface.
#
#              Handle special case cause codes
#              Handle failure to raise fault
#
# Assumptions: Short circuited Success return if the alarm is
#              already known to be asserted.
#
# Returns    : False on Failure
#               True on Success
#
#####################################################################
def raise_alarm(alarm_cause, interface=None, data=0):
    """Assert a cause based PTP alarm"""

    collectd.debug("%s Raising Alarm %d" % (PLUGIN, alarm_cause))

    alarm = get_alarm_object(alarm_cause, interface)
    if alarm is None:
        # log created for None case in the get_alarm_object util
        return True

    # copy the reason as it might be updated for the OOT,
    # most typical, case.
    reason = alarm.reason

    # Handle some special cases
    #

    if alarm_cause == ALARM_CAUSE__OOT:
        # If this is an out of tolerance alarm then add the
        # out of tolerance reading to the reason string before
        # asserting the alarm.
        #
        # Keep the alarm updated with the latest sample reading
        # and severity even if its already asserted.
        if abs(float(data)) > 100000000000:
            reason += 'more than 100 seconds'
        elif abs(float(data)) > 10000000000:
            reason += 'more than 10 seconds'
        elif abs(float(data)) > 1000000000:
            reason += 'more than 1 second'
        elif abs(float(data)) > 1000000:
            reason += str(abs(int(data)) / 1000000)
            reason += ' millisecs'
        elif abs(float(data)) > 1000:
            reason += str(abs(int(data)) / 1000)
            reason += ' microsecs'
        else:
            reason += str(float(data))
            reason += ' ' + PLUGIN_TYPE_INSTANCE

    elif alarm.raised is True:
        # If alarm already raised then exit.
        #
        # All other alarms are a Major so there is no need to
        # track a change in severity and update accordingly.
        return True

    elif alarm_cause == ALARM_CAUSE__PROCESS:
        reason = 'Provisioned ' + PTP + ' \'' + obj.mode
        reason += '\' time stamping mode seems to be unsupported by this host'

    try:
        fault = fm_api.Fault(
            alarm_id=PLUGIN_ALARMID,
            alarm_state=fm_constants.FM_ALARM_STATE_SET,
            entity_type_id=fm_constants.FM_ENTITY_TYPE_HOST,
            entity_instance_id=alarm.eid,
            severity=alarm.severity,
            reason_text=reason,
            alarm_type=obj.alarm_type,
            probable_cause=alarm.cause,
            proposed_repair_action=alarm.repair,
            service_affecting=False,  # obj.service_affecting,
            suppression=True)         # obj.suppression)

        alarm_uuid = api.set_fault(fault)
        if pc.is_uuid_like(alarm_uuid) is False:

            # Don't _add_unreachable_server list if the fm call failed.
            # That way it will be retried at a later time.
            collectd.error("%s %s:%s set_fault failed:%s" %
                           (PLUGIN, PLUGIN_ALARMID, alarm.eid, alarm_uuid))
            return False

        else:
            collectd.info("%s %s:%s:%s alarm raised" %
                          (PLUGIN, PLUGIN_ALARMID, alarm.eid, alarm.severity))
            alarm.raised = True
            return True

    except Exception as ex:
        collectd.error("%s 'set_fault' exception ; %s:%s:%s ; %s" %
                       (PLUGIN,
                        PLUGIN_ALARMID,
                        alarm.eid,
                        alarm.severity,
                        ex))
    return False


#####################################################################
#
# Name       : create_interface_alarm_objects
#
# Description: Create alarm objects for specified interface
#
#####################################################################
def create_interface_alarm_objects(interface=None):
    """Create alarm objects"""

    collectd.debug("%s Alarm Object Create: Interface:%s " %
                   (PLUGIN, interface))

    if interface is None:
        o = PTP_alarm_object()
        o.alarm = ALARM_CAUSE__PROCESS
        o.severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
        o.reason = obj.hostname + ' does not support the provisioned '
        o.reason += PTP + ' mode '
        o.repair = 'Check host hardware reference manual '
        o.repair += 'to verify that the selected PTP mode is supported'
        o.eid = obj.base_eid + '.ptp'
        o.cause = fm_constants.ALARM_PROBABLE_CAUSE_UNKNOWN  # 'unknown'
        ALARM_OBJ_LIST.append(o)
        ctrl.process_alarm_object = o

        o = PTP_alarm_object()
        o.alarm = ALARM_CAUSE__OOT
        o.severity = fm_constants.FM_ALARM_SEVERITY_CLEAR
        o.reason = obj.hostname + ' '
        o.reason += PTP + " clocking is out of tolerance by "
        o.repair = "Check quality of the clocking network"
        o.eid = obj.base_eid + '.ptp=out-of-tolerance'
        o.cause = fm_constants.ALARM_PROBABLE_CAUSE_50  # THRESHOLD CROSS
        ALARM_OBJ_LIST.append(o)
        ctrl.oot_alarm_object = o

        o = PTP_alarm_object()
        # Only applies to storage and worker nodes
        o.alarm = ALARM_CAUSE__NO_LOCK
        o.severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
        o.reason = obj.hostname
        o.reason += ' is not locked to remote PTP Grand Master'
        o.repair = 'Check network'
        o.eid = obj.base_eid + '.ptp=no-lock'
        o.cause = fm_constants.ALARM_PROBABLE_CAUSE_51  # timing-problem
        ALARM_OBJ_LIST.append(o)
        ctrl.nolock_alarm_object = o

    else:
        o = PTP_alarm_object(interface)
        o.alarm = ALARM_CAUSE__UNSUPPORTED_HW
        o.severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
        o.reason = obj.hostname + " '" + interface + "' does not support "
        o.reason += PTP + ' Hardware timestamping'
        o.repair = 'Check host hardware reference manual to verify PTP '
        o.repair += 'Hardware timestamping is supported by this interface'
        o.eid = obj.base_eid + '.ptp=' + interface
        o.eid += '.unsupported=hardware-timestamping'
        o.cause = fm_constants.ALARM_PROBABLE_CAUSE_7  # 'config error'
        ALARM_OBJ_LIST.append(o)

        o = PTP_alarm_object(interface)
        o.alarm = ALARM_CAUSE__UNSUPPORTED_SW
        o.severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
        o.reason = obj.hostname + " '" + interface + "' does not support "
        o.reason += PTP + ' Software timestamping'
        o.repair = 'Check host hardware reference manual to verify PTP '
        o.repair += 'Software timestamping is supported by this interface'
        o.eid = obj.base_eid + '.ptp=' + interface
        o.eid += '.unsupported=software-timestamping'
        o.cause = fm_constants.ALARM_PROBABLE_CAUSE_7  # 'config error'
        ALARM_OBJ_LIST.append(o)

        o = PTP_alarm_object(interface)
        o.alarm = ALARM_CAUSE__UNSUPPORTED_LEGACY
        o.severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
        o.reason = obj.hostname + " '" + interface + "' does not support "
        o.reason += PTP + " Legacy timestamping"
        o.repair = 'Check host hardware reference manual to verify PTP '
        o.repair += 'Legacy or Raw Clock is supported by this host'
        o.eid = obj.base_eid + '.ptp=' + interface
        o.eid += '.unsupported=legacy-timestamping'
        o.cause = fm_constants.ALARM_PROBABLE_CAUSE_7  # 'config error'
        ALARM_OBJ_LIST.append(o)


#####################################################################
#
# Name       : read_timestamp_mode
#
# Description: Refresh the timestamping mode if it changes
#
#####################################################################
def read_timestamp_mode():
    """Load timestamping mode"""

    if os.path.exists(PLUGIN_CONF_FILE):
        current_mode = obj.mode
        with open(PLUGIN_CONF_FILE, 'r') as infile:
            for line in infile:
                if PLUGIN_CONF_TIMESTAMPING in line:
                    obj.mode = line.split()[1].strip('\n')
                    break

        if obj.mode:
            if obj.mode != current_mode:
                collectd.info("%s Timestamping Mode: %s" %
                              (PLUGIN, obj.mode))
        else:
            collectd.error("%s failed to get Timestamping Mode" % PLUGIN)
    else:
        collectd.error("%s failed to load ptp4l configuration" % PLUGIN)
        obj.mode = None


#####################################################################
#
# Name       : init_func
#
# Description: The collectd initialization entrypoint for
#              this plugin
#
# Assumptions: called only once
#
# Algorithm  : check for no
#
#
#####################################################################
def init_func():

    if obj.init_ready() is False:
        return False

    obj.hostname = obj.gethostname()
    obj.base_eid = 'host=' + obj.hostname

    # Create the interface independent alarm objects.
    create_interface_alarm_objects()

    # load monitored interfaces and supported modes
    if os.path.exists(PLUGIN_CONF_FILE):
        with open(PLUGIN_CONF_FILE, 'r') as infile:
            for line in infile:
                # The PTP interfaces used are specified in the ptp4l.conf
                #  file as [interface]. There may be more than one.
                # Presently there is no need to track the function of the
                # interface ; namely mgmnt or oam.
                if line[0] == '[':
                    interface = line.split(']')[0].split('[')[1]
                    if interface and interface != 'global':
                        interfaces[interface] = _get_supported_modes(interface)
                        create_interface_alarm_objects(interface)

                if PLUGIN_CONF_TIMESTAMPING in line:
                    obj.mode = line.split()[1].strip('\n')

        if obj.mode:
            collectd.info("%s Timestamping Mode: %s" %
                          (PLUGIN, obj.mode))
        else:
            collectd.error("%s failed to get Timestamping Mode" % PLUGIN)
    else:
        collectd.error("%s failed to load ptp4l configuration" % PLUGIN)
        obj.mode = None

    for key, value in interfaces.items():
        collectd.info("%s interface %s supports timestamping modes: %s" %
                      (PLUGIN, key, value))

    # remove '# to dump alarm object data
    # print_alarm_objects()

    if tsc.nodetype == 'controller':
        obj.controller = True

    obj.virtual = obj.is_virtual()
    obj.init_done = True
    obj.log_throttle_count = 0
    collectd.info("%s initialization complete" % PLUGIN)


#####################################################################
#
# Name       : read_func
#
# Description: The collectd audit entrypoint for PTP Monitoring
#
# Assumptions: collectd calls init_func one time.
#
#
#              retry init if needed
#              retry fm connect if needed
#              check service enabled state
#              check service running state
#                 error -> alarm host=<hostname>.ptp
#              check
#
#####################################################################
def read_func():

    if obj.virtual is True:
        return 0

    # check and run init until it reports init_done True
    if obj.init_done is False:
        if not (obj.log_throttle_count % obj.INIT_LOG_THROTTLE):
            collectd.info("%s re-running init" % PLUGIN)
        obj.log_throttle_count += 1
        init_func()
        return 0

    if obj.fm_connectivity is False:

        try:
            # query FM for existing alarms.
            alarms = api.get_faults_by_id(PLUGIN_ALARMID)
        except Exception as ex:
            collectd.error("%s 'get_faults_by_id' exception ; %s" %
                           (PLUGIN, ex))
            return 0

        if alarms:
            for alarm in alarms:
                collectd.debug("%s found startup alarm '%s'" %
                               (PLUGIN, alarm.entity_instance_id))

                eid = alarm.entity_instance_id
                if eid is None:
                    collectd.error("%s startup alarm query error ; no eid" %
                                   PLUGIN)
                    continue

                # get the hostname host=<hostname>.stuff
                # split over base eid and then
                # compare that to this plugin's base eid
                # ignore alarms not for this host
                if eid.split('.')[0] != obj.base_eid:
                    continue
                else:
                    # load the state of the specific alarm
                    instance = eid.split('.')[1].split('=')
                    if instance[0] == 'ptp':
                        # clear all ptp alarms on process startup
                        # just in case interface names have changed
                        # since the alarm was raised.
                        if clear_alarm(eid) is False:
                            # if we can't clear the alarm now then error out.
                            collectd.error("%s failed to clear startup "
                                           "alarm %s:%s" %
                                           (PLUGIN, PLUGIN_ALARMID, eid))
                            # try again next time around
                            return 0
                        else:
                            collectd.info("%s cleared startup alarm '%s'" %
                                          (PLUGIN, alarm.entity_instance_id))
                    else:

                        if clear_alarm(eid) is False:
                            collectd.error("%s failed to clear invalid PTP "
                                           "alarm %s:%s" %
                                           (PLUGIN, PLUGIN_ALARMID,
                                            alarm.entity_instance_id))
                            return 0
                        else:
                            collectd.info("%s cleared found invalid startup"
                                          " alarm %s:%s" %
                                          (PLUGIN,
                                           PLUGIN_ALARMID,
                                           alarm.entity_instance_id))
        else:
            collectd.info("%s no startup alarms found" % PLUGIN)

        obj.config_complete = True
        obj.fm_connectivity = True
        # assert_all_alarms()

    # This plugin supports PTP in-service state change by checking
    # service state on every audit ; every 5 minutes.
    data = subprocess.check_output([SYSTEMCTL,
                                    SYSTEMCTL_IS_ENABLED_OPTION,
                                    PLUGIN_SERVICE])
    collectd.debug("%s PTP admin state:%s" % (PLUGIN, data.rstrip()))

    if data.rstrip() == SYSTEMCTL_IS_DISABLED_RESPONSE:

        # Manage execution phase
        if obj.phase != RUN_PHASE__DISABLED:
            obj.phase = RUN_PHASE__DISABLED
            obj.log_throttle_count = 0

        if not (obj.log_throttle_count % obj.INIT_LOG_THROTTLE):
            collectd.info("%s PTP Service Disabled" % PLUGIN)
        obj.log_throttle_count += 1

        for o in ALARM_OBJ_LIST:
            if o.raised is True:
                if clear_alarm(o.eid) is True:
                    o.raised = False
                else:
                    collectd.error("%s %s:%s clear alarm failed "
                                   "; will retry" %
                                   (PLUGIN, PLUGIN_ALARMID, o.eid))
        return 0

    data = subprocess.check_output([SYSTEMCTL,
                                    SYSTEMCTL_IS_ACTIVE_OPTION,
                                    PLUGIN_SERVICE])

    if data.rstrip() == SYSTEMCTL_IS_INACTIVE_RESPONSE:

        # Manage execution phase
        if obj.phase != RUN_PHASE__NOT_RUNNING:
            obj.phase = RUN_PHASE__NOT_RUNNING
            obj.log_throttle_count = 0

        if ctrl.process_alarm_object.alarm == ALARM_CAUSE__PROCESS:
            if ctrl.process_alarm_object.raised is False:
                collectd.error("%s PTP service enabled but not running" %
                               PLUGIN)
                if raise_alarm(ALARM_CAUSE__PROCESS) is True:
                    ctrl.process_alarm_object.raised = True

        # clear all other alarms if the 'process' alarm is raised
        elif ctrl.process_alarm_object.raised is True:
            if clear_alarm(ctrl.process_alarm_object.eid) is True:
                msg = 'cleared'
                ctrl.process_alarm_object.raised = False
            else:
                msg = 'failed to clear'
            collectd.info("%s %s %s:%s" %
                          (PLUGIN, msg, PLUGIN_ALARMID,
                           ctrl.process_alarm_object.eid))
        return 0

    # Handle clearing the 'process' alarm if it is asserted and
    # the process is now running
    if ctrl.process_alarm_object.raised is True:
        if clear_alarm(ctrl.process_alarm_object.eid) is True:
            ctrl.process_alarm_object.raised = False
            collectd.info("%s PTP service enabled and running" % PLUGIN)

    # Auto refresh the timestamping mode in case collectd runs
    # before the ptp manifest or the mode changes on the fly by
    # an in-service manifest.
    # Every 4 audits.
    obj.audits += 1
    if not obj.audits % 4:
        read_timestamp_mode()

    # Manage execution phase
    if obj.phase != RUN_PHASE__SAMPLING:
        obj.phase = RUN_PHASE__SAMPLING
        obj.log_throttle_count = 0

    # Let's read the clock info, Grand Master sig and skew
    #
    # sudo /usr/sbin/pmc -u -b 0 'GET TIME_STATUS_NP'
    #
    data = subprocess.check_output([PLUGIN_STATUS_QUERY_EXEC,
                                    '-u', '-b', '0', 'GET TIME_STATUS_NP'])

    got_master_offset = False
    master_offset = 0
    my_identity = ''
    gm_identity = ''
    gm_present = False
    obj.resp = data.split('\n')
    for line in obj.resp:
        if 'RESPONSE MANAGEMENT TIME_STATUS_NP' in line:
            collectd.debug("%s key       : %s" %
                           (PLUGIN, line.split()[0].split('-')[0]))
            my_identity = line.split()[0].split('-')[0]
        if 'master_offset' in line:
            collectd.debug("%s Offset    : %s" % (PLUGIN, line.split()[1]))
            master_offset = float(line.split()[1])
            got_master_offset = True
        if 'gmPresent' in line:
            collectd.debug("%s gmPresent : %s" % (PLUGIN, line.split()[1]))
            gm_present = line.split()[1]
        if 'gmIdentity' in line:
            collectd.debug("%s gmIdentity: %s" % (PLUGIN, line.split()[1]))
            gm_identity = line.split()[1]

    # Handle case where this host is the Grand Master
    #   ... or assumes it is.
    if my_identity == gm_identity:

        if obj.controller is False:

            # Compute and storage nodes should not be the Grand Master
            if ctrl.nolock_alarm_object.raised is False:
                if raise_alarm(ALARM_CAUSE__NO_LOCK, None, 0) is True:
                    ctrl.nolock_alarm_object.raised = True

            # produce a throttled log while this host is not locked to the GM
            if not (obj.log_throttle_count % obj.INIT_LOG_THROTTLE):
                collectd.info("%s %s not locked to remote Grand Master "
                              "(%s)" % (PLUGIN, obj.hostname, gm_identity))
            obj.log_throttle_count += 1

            # No samples for storage and compute nodes that are not
            # locked to a Grand Master
            return 0

        else:
            # Controllers can be a Grand Master ; throttle the log
            if not (obj.log_throttle_count % obj.INIT_LOG_THROTTLE):
                collectd.info("%s %s is Grand Master:%s" %
                              (PLUGIN, obj.hostname, gm_identity))
            obj.log_throttle_count += 1

            # The Grand Master will always be 0 so there is no point
            # creating a sample for it.
            return 0

    # Handle clearing nolock alarm for computes and storage nodes
    elif obj.controller is False:
        if ctrl.nolock_alarm_object.raised is True:
            if clear_alarm(ctrl.nolock_alarm_object.eid) is True:
                ctrl.nolock_alarm_object.raised = False

    # Keep this FIT test code but make it commented out for security
    # if os.path.exists('/var/run/fit/ptp_data'):
    #     master_offset = 0
    #     with open('/var/run/fit/ptp_data', 'r') as infile:
    #         for line in infile:
    #             master_offset = int(line)
    #             got_master_offset = True
    #             collectd.info("%s using ptp FIT data skew:%d" %
    #                           (PLUGIN, master_offset))
    #             break

    # Send sample and Manage the Out-Of-Tolerance alarm
    if got_master_offset is True:

        if not (obj.log_throttle_count % obj.INIT_LOG_THROTTLE):
            collectd.info("%s %s is collecting samples [%5d] "
                          "with Grand Master %s" %
                          (PLUGIN, obj.hostname,
                           float(master_offset), gm_identity))

        obj.log_throttle_count += 1

        # setup the sample structure and dispatch
        val = collectd.Values(host=obj.hostname)
        val.type = PLUGIN_TYPE
        val.type_instance = PLUGIN_TYPE_INSTANCE
        val.plugin = 'ptp'
        val.dispatch(values=[float(master_offset)])

        # Manage the sample OOT alarm severity
        severity = fm_constants.FM_ALARM_SEVERITY_CLEAR
        if abs(master_offset) > OOT_MAJOR_THRESHOLD:
            severity = fm_constants.FM_ALARM_SEVERITY_MAJOR
        elif abs(master_offset) > OOT_MINOR_THRESHOLD:
            severity = fm_constants.FM_ALARM_SEVERITY_MINOR

        # Handle clearing of Out-Of-Tolerance alarm
        if severity == fm_constants.FM_ALARM_SEVERITY_CLEAR:
            if ctrl.oot_alarm_object.raised is True:
                if clear_alarm(ctrl.oot_alarm_object.eid) is True:
                    ctrl.oot_alarm_object.severity = \
                        fm_constants.FM_ALARM_SEVERITY_CLEAR
                    ctrl.oot_alarm_object.raised = False

        else:
            # Special Case:
            # -------------
            # Don't raise minor alarm when in software timestamping mode.
            # Too much skew in software or legacy mode ; alarm would bounce.
            # TODO: Consider making ptp a real time process
            if severity == fm_constants.FM_ALARM_SEVERITY_MINOR \
                    and obj.mode != 'hardware':
                return 0

            # Handle debounce of the OOT alarm.
            # Debounce by 1 for the same severity level.
            if ctrl.oot_alarm_object.severity != severity:
                ctrl.oot_alarm_object.severity = severity

            # This will keep refreshing the alarm text with the current
            # skew value while still debounce on state transitions.
            #
            # Precision ... (PTP) clocking is out of tolerance by 1004 nsec
            #
            elif severity == fm_constants.FM_ALARM_SEVERITY_MINOR:
                # Handle raising the Minor OOT Alarm.
                rc = raise_alarm(ALARM_CAUSE__OOT, None, master_offset)
                if rc is True:
                    ctrl.oot_alarm_object.raised = True

            elif severity == fm_constants.FM_ALARM_SEVERITY_MAJOR:
                # Handle raising the Major OOT Alarm.
                rc = raise_alarm(ALARM_CAUSE__OOT, None, master_offset)
                if rc is True:
                    ctrl.oot_alarm_object.raised = True

            # Record the value that is alarmable
            if severity != fm_constants.FM_ALARM_SEVERITY_CLEAR:
                collectd.info("%s Grand Master ID: %s ; "
                              "HOST ID: %s ; "
                              "GM Present:%s ; "
                              "Skew:%5d" % (PLUGIN,
                                            gm_identity,
                                            my_identity,
                                            gm_present,
                                            master_offset))
    else:
        collectd.info("%s No Clock Sync" % PLUGIN)

    return 0


collectd.register_init(init_func)
collectd.register_read(read_func, interval=PLUGIN_AUDIT_INTERVAL)
