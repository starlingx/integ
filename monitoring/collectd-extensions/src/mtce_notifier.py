#
# Copyright (c) 2018-2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
#############################################################################
#
# This file is the collectd 'Maintenance' Notifier.
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
# This notifier manages requesting mtce to assert or clear its collectd
# host-degrade-cause flag based on notification messages sent from collectd.
#
# Messages to maintenance are throttled ONE_EVERY while this state is the
# same as last state.
#
# Message is sent on every state change
#  from clear  to assert or
#  from assert to clear
#
# See code comments for details.
#
############################################################################
#
# Import list

import os
import socket
import collectd
import tsconfig.tsconfig as tsc

# This plugin name
PLUGIN = 'degrade notifier'

# collectd severity definitions ;
# Note: can't seem to pull then in symbolically with a header
NOTIF_FAILURE = 1
NOTIF_WARNING = 2
NOTIF_OKAY = 4

# default mtce port.
# ... with configuration override
MTCE_CMD_RX_PORT = 2101

# same state message throttle count.
# ... only send the degrade message every 'this' number
#     while the state of assert or clear remains the same.
ONE_EVERY = 10

PLUGIN__DF = 'df'
PLUGIN__MEM = 'memory'
PLUGIN__CPU = 'cpu'

PLUGIN__VSWITCH_MEM = 'vswitch_mem'
PLUGIN__VSWITCH_CPU = 'vswitch_cpu'
PLUGIN__VSWITCH_PORT = "vswitch_port"
PLUGIN__VSWITCH_IFACE = "vswitch_iface"


PLUGIN_INTERFACE = 'interface'
PLUGIN__EXAMPLE = 'example'


# The collectd Maintenance Notifier Object
class collectdMtceNotifierObject:

    def __init__(self, port):
        """collectdMtceNotifierObject Class constructor"""
        # default maintenance port
        self.port = port
        self.addr = None

        # specifies the protocol family to use when messaging maintenance.
        # if system is IPV6, then that is learned and this 'protocol' is
        # updated with AF_INET6
        self.protocol = socket.AF_INET

        # List of plugin names that require degrade for specified severity.
        self.degrade_list__failure = [PLUGIN__DF,
                                      PLUGIN__MEM,
                                      PLUGIN__CPU,
                                      PLUGIN__VSWITCH_MEM,
                                      PLUGIN__VSWITCH_CPU,
                                      PLUGIN__VSWITCH_PORT,
                                      PLUGIN__VSWITCH_IFACE,
                                      PLUGIN_INTERFACE,
                                      PLUGIN__EXAMPLE]
        self.degrade_list__warning = [PLUGIN_INTERFACE]

        # the running list of resources that require degrade.
        # a degrade clear message is sent whenever this list is empty.
        # a degrade assert message is sent whenever this list is not empty.
        self.degrade_list = []

        # throttle down sending of duplicate degrade assert/clear messages
        self.last_state = "undef"
        self.msg_throttle = 0


# Instantiate the mtce_notifier object
# This object persists from notificaiton to notification
obj = collectdMtceNotifierObject(MTCE_CMD_RX_PORT)


def _get_active_controller_ip():
    """Get the active controller host IP"""

    try:
        obj.addr = socket.getaddrinfo('controller', None)[0][4][0]
        collectd.info("%s controller ip: %s" % (PLUGIN, obj.addr))
    except Exception as ex:
        obj.addr = None
        collectd.error("%s failed to get controller ip ; %s" %
                       (PLUGIN, str(ex)))
        return 0


def _df_instance_to_path(df_inst):
    """Convert a df instance name to a mountpoint"""

    # df_root is not a dynamic file system. Ignore that one.
    if df_inst == 'df_root':
        return '/'
    else:
        # For all others replace all '-' with '/'
        return('/' + df_inst[3:].replace('-', '/'))


# This function removes degraded file systems that are no longer present.
def _clear_degrade_for_missing_filesystems():
    """Remove degraded file systems that are no longer mounted or present"""

    for df_inst in obj.degrade_list:

        # Only file system plugins are looked at.
        # File system plugin instance names are prefixed with 'df_'
        # as the first 3 chars in the instance name.
        if df_inst[0:3] == 'df_':
            path = _df_instance_to_path(df_inst)

            # check the mount point.
            # if the mount point no longer exists then remove
            # this instance from the degrade list.
            if os.path.ismount(path) is False:
                collectd.info("%s clearing degrade for missing %s ; %s" %
                              (PLUGIN, path, obj.degrade_list))
                obj.degrade_list.remove(df_inst)

    return 0


# The collectd configuration interface
#
# Used to configure the maintenance port.
#    key = 'port'
#    val = port number
#
def config_func(config):
    """Configure the maintenance degrade notifier plugin"""

    collectd.debug('%s config function' % PLUGIN)
    for node in config.children:
        key = node.key.lower()
        val = node.values[0]

        if key == 'port':
            obj.port = int(val)
            collectd.info("%s configured mtce port: %d" %
                          (PLUGIN, obj.port))
            return 0

    obj.port = MTCE_CMD_RX_PORT
    collectd.error("%s no mtce port provided ; defaulting to %d" %
                   (PLUGIN, obj.port))


# Collectd calls this function on startup.
def init_func():
    """Collectd Mtce Notifier Initialization Function"""

    obj.host = os.uname()[1]
    collectd.info("%s %s:%s sending to mtce port %d" %
                  (PLUGIN, tsc.nodetype, obj.host, obj.port))

    collectd.debug("%s init function" % PLUGIN)


# This is the Notifier function that is called by collectd.
#
# Handling steps are
#
#  1. build resource name from notification object.
#  2. check resource against severity lists.
#  3. manage this instance's degrade state.
#  4. send mtcAgent the degrade state message.
#
def notifier_func(nObject):
    """Collectd Mtce Notifier Handler Function"""

    # Create the resource name from the notifier object.
    # format: <plugin name>_<plugin_instance_name>
    resource = nObject.plugin
    if nObject.plugin_instance:
        resource += "_" + nObject.plugin_instance

    # This block looks at the current notification severity
    # and manages the degrade_list.
    # If the specified plugin name exists in each of the warnings
    # or failure lists and there is a current severity match then
    # add that resource instance to the degrade list.
    # Conversly if this notification is OKAY then make sure this
    # resource instance is not in the degrade list (remove it if it is)
    if nObject.severity is NOTIF_OKAY:
        if obj.degrade_list and resource in obj.degrade_list:
            obj.degrade_list.remove(resource)

    elif nObject.severity is NOTIF_FAILURE:
        if obj.degrade_list__failure:
            if nObject.plugin in obj.degrade_list__failure:
                if resource not in obj.degrade_list:
                    # handle dynamic filesystems going missing over a swact
                    # or unmount and being reported as a transient error by
                    # the df plugin. Don't add it to the failed list if the
                    # mountpoint is gone.
                    add = True
                    if nObject.plugin == PLUGIN__DF:
                        path = _df_instance_to_path(resource)
                        add = os.path.ismount(path)
                    if add is True:
                        collectd.info("%s %s added to degrade list" %
                                      (PLUGIN, resource))
                        obj.degrade_list.append(resource)
        else:
            # If severity is failure and no failures cause degrade
            # then make sure this plugin is not in the degrade list,
            # Should never occur.
            if resource in obj.degrade_list:
                obj.degrade_list.remove(resource)

    elif nObject.severity is NOTIF_WARNING:
        if obj.degrade_list__warning:
            if nObject.plugin in obj.degrade_list__warning:
                if resource not in obj.degrade_list:
                    # handle dynamic filesystems going missing over a swact
                    # or unmount and being reported as a transient error by
                    # the df plugin. Don't add it to the failed list if the
                    # mountpoint is gone.
                    add = True
                    if nObject.plugin == PLUGIN__DF:
                        path = _df_instance_to_path(resource)
                        add = os.path.ismount(path)
                    if add is True:
                        collectd.info("%s %s added to degrade list" %
                                      (PLUGIN, resource))
                        obj.degrade_list.append(resource)
        else:
            # If severity is warning and no warnings cause degrade
            # then make sure this plugin is not in the degrade list.
            # Should never occur..
            if resource in obj.degrade_list:
                obj.degrade_list.remove(resource)
    else:
        collectd.info("%s unsupported severity %d" %
                      (PLUGIN, nObject.severity))
        return 0

    # running counter of notifications.
    obj.msg_throttle += 1

    # Support for Dynamic File Systems
    # --------------------------------
    # Some active controller mounted filesystems can become
    # unmounted under the watch of collectd. This can occur
    # as a result of a Swact. If an 'degrade' is raised at the
    # time an fs disappears then that state can become stuck
    # active until the next Swact. This call handles this case.
    #
    # Audit file system presence every time we get the
    # notification for the root file system.
    # Depending on the root filesystem always being there.
    if nObject.plugin == 'df' \
       and nObject.plugin_instance == 'root' \
       and len(obj.degrade_list):
        _clear_degrade_for_missing_filesystems()

    # If degrade list is empty then a clear state is sent to maintenance.
    # If degrade list is NOT empty then an assert state is sent to maintenance
    # For logging and to ease debug the code below will create a list of
    # degraded resource instances to be included in the message to maintenance
    # for mtcAgent to optionally log it.
    resources = ""
    if obj.degrade_list:
        # loop over the list,
        # limit the degraded resource list being sent to mtce to 5
        for r in obj.degrade_list[0:1:5]:
            resources += r + ','
        resources = resources[:-1]
        state = "assert"
    else:
        state = "clear"

    # Message throttling ....

    # Avoid sending the same last state message for up to ONE_EVERY count.
    # Just reduce load on mtcAgent
    if obj.last_state == state and obj.msg_throttle < ONE_EVERY:
        return 0

    # if the degrade state has changed then log it and proceed
    if obj.last_state != state:
        if obj.last_state != "undef":
            collectd.info("%s degrade %s %s" %
                          (PLUGIN,
                           state,
                           obj.degrade_list))

    # Save state for next time
    obj.last_state = state

    # Clear the message throttle counter
    obj.msg_throttle = 0

    # Send the degrade state ; assert or clear message to mtcAgent.
    # If we get a send failure then log it and set the addr to None
    # so it forces us to refresh the controller address on the next
    # notification
    try:
        mtce_socket = socket.socket(obj.protocol, socket.SOCK_DGRAM)
        if mtce_socket:
            if obj.addr is None:
                _get_active_controller_ip()
                if obj.addr is None:
                    return 0

            # Create the Maintenance message.
            message = "{\"service\":\"collectd_notifier\","
            message += "\"hostname\":\"" + nObject.host + "\","
            message += "\"degrade\":\"" + state + "\","
            message += "\"resource\":\"" + resources + "\"}"
            collectd.debug("%s: %s" % (PLUGIN, message))

            mtce_socket.settimeout(1.0)
            mtce_socket.sendto(message, (obj.addr, obj.port))
            mtce_socket.close()
        else:
            collectd.error("%s %s failed to open socket (%s)" %
                           (PLUGIN, resource, obj.addr))
    except socket.error as e:
        if e.args[0] == socket.EAI_ADDRFAMILY:
            # Handle IPV4 to IPV6 switchover:
            obj.protocol = socket.AF_INET6
            collectd.info("%s %s ipv6 addressing (%s)" %
                          (PLUGIN, resource, obj.addr))
        else:
            collectd.error("%s %s socket error (%s) ; %s" %
                           (PLUGIN, resource, obj.addr, str(e)))
            # try self correction
            obj.addr = None
            obj.protocol = socket.AF_INET

    return 0


collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_notification(notifier_func)
