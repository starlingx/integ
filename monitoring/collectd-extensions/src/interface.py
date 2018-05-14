#
# Copyright (c) 2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
############################################################################
#
# This is the Host Interface Monitor plugin for Collectd.
#
# Only mgmnt , infra and oam interfaces are supported with the following
# mapping specified in /etc/platform/platform.conf
#
# mgmnt - management_interface     | all hosts  | manditory
# infa  - infrastructure_interface | any host   | optional
#   oam - oam_interface            | controller | manditory
#
# This plugin reports link state inb the following way.
#
# The plugin init function learns interface names from platform.conf
#
#
############################################################################
import os
import random
import collectd
import tsconfig.tsconfig as tsc

PLUGIN = 'interface plugin'

# static variables

PLATFORM_CONF_MGMNT_LABEL = "management_interface="
PLATFORM_CONF_INFRA_LABEL = "infrastructure_interface="
PLATFORM_CONF_OAM_LABEL = "oam_interface="

NETWORK_MGMNT = 'mgmnt'
NETWORK_INFRA = 'infra'
NETWORK_OAM = 'oam'


class iface:
    def __init__(self, n, m, s):
        self.master = {'network': n, 'name': m, 'state': 'down', 'slaves': s}
        self.slave1 = {}
        self.slave2 = {}
        self.state = int(100)


class object:
    hostname = ''

    def __init__(self):
        self.NETWORKS = {}
        self.NETWORKS[NETWORK_MGMNT] = None
        self.NETWORKS[NETWORK_INFRA] = None
        self.NETWORKS[NETWORK_OAM] = None

obj = object()


# The config function - called once on collectd process startup
def config_func(config):
    """
    Configure the plugin
    """

    collectd.debug('%s config function' % PLUGIN)
    return 0


# The init function - called once on collectd process startup
def init_func():

    # get current hostname
    obj.hostname = os.uname()[1]

    # get the master interface names from /etc/platform/platform.conf
    with open(tsc.PLATFORM_CONF_FILE, 'r') as infile:
        for line in infile:

            # Management Interface
            if PLATFORM_CONF_MGMNT_LABEL in line:
                name = line.split('=')[1].replace('\n', '')
                obj.NETWORKS[NETWORK_MGMNT] = iface(NETWORK_MGMNT, name, 0)
                collectd.info("%s monitoring mgmnt interface : %s" %
                              (PLUGIN,
                               obj.NETWORKS[NETWORK_MGMNT].master['name']))

            # Infrastructure Interface
            elif PLATFORM_CONF_INFRA_LABEL in line:
                name = line.split('=')[1].replace('\n', '')
                obj.NETWORKS[NETWORK_INFRA] = iface(NETWORK_INFRA, name, 0)
                collectd.info("%s monitoring infra interface : %s" %
                              (PLUGIN,
                               obj.NETWORKS[NETWORK_INFRA].master['name']))

            # OAM Interface
            elif PLATFORM_CONF_OAM_LABEL in line:
                name = line.split('=')[1].replace('\n', '')
                obj.NETWORKS[NETWORK_OAM] = iface(NETWORK_OAM, name, 0)
                collectd.info("%s monitoring oam interface: %s" %
                              (PLUGIN,
                               obj.NETWORKS[NETWORK_OAM].master['name']))

    return 0


# The sample read function - called on every audit interval
def read_func():

    if obj.NETWORKS[NETWORK_MGMNT].state == 0:
        obj.NETWORKS[NETWORK_MGMNT].state = 100
    else:
        obj.NETWORKS[NETWORK_MGMNT].state -= 25

    # Dispatch usage value to collectd
    val = collectd.Values(host=obj.hostname)
    val.plugin = 'interface'
    val.plugin_instance = 'mgmnt'
    val.type = 'absolute'
    val.type_instance = 'used'
    val.dispatch(values=[obj.NETWORKS[NETWORK_MGMNT].state])
    return 0


# register the config, init and read functions
collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func)
