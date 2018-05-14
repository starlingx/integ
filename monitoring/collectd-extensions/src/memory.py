#
# Copyright (c) 2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
############################################################################
#
# This file is the collectd 'Platform CPU Usage' Monitor.
#
# The Platform CPU Usage is calculated as an averaged percentage of
# platform core usable since the previous sample.
#
#  Init Function:
#    - if 'compute_reserved.conf exists then query/store PLATFORM_CPU_LIST
#
############################################################################
import os
import collectd

debug = False

# general return codes
PASS = 0
FAIL = 1

PLUGIN = 'platform memory usage'


# CPU Control class
class MEM:
    hostname = ""            # hostname for sample notification message
    cmd = '/proc/meminfo'    # the query comment
    value = float(0.0)       # float value of memory usage

    # meminfo values we care about
    memTotal_kB = 0
    memFree_kB = 0
    buffers = 0
    cached = 0
    SReclaimable = 0
    CommitLimit = 0
    Committed_AS = 0
    HugePages_Total = 0
    Hugepagesize = 0
    AnonPages = 0

    # derived values
    avail = 0
    total = 0
    strict = 0


# Instantiate the class
obj = MEM()


def config_func(config):
    """
    Configure the memory usage plugin
    """

    for node in config.children:
        key = node.key.lower()
        val = node.values[0]

        if key == 'path':
            obj.cmd = str(val)
            collectd.info("%s configured query command: '%s'" %
                          (PLUGIN, obj.cmd))
            return 0

    collectd.info("%s no config command provided ; "
                  "defaulting to '%s'" %
                  (PLUGIN, obj.cmd))


# Get the platform cpu list and number of cpus reported by /proc/cpuinfo
def init_func():
    # get current hostname
    obj.hostname = os.uname()[1]

    fn = '/proc/sys/vm/overcommit_memory'
    if os.path.exists(fn):
        with open(fn, 'r') as infile:
            for line in infile:
                obj.strict = int(line)
                break

    collectd.info("%s strict:%d" % (PLUGIN, obj.strict))


# Calculate the CPU usage sample
def read_func():
    meminfo = {}
    try:
        with open(obj.cmd) as fd:
            for line in fd:
                meminfo[line.split(':')[0]] = line.split(':')[1].strip()

    except EnvironmentError as e:
        collectd.error("%s unable to read from %s ; str(e)" %
                       (PLUGIN, str(e)))
        return FAIL

    # remove the 'unit' (kB) suffix that might be on some of the lines
    for line in meminfo:
        # remove the units from the value read
        value_unit = [u.strip() for u in meminfo[line].split(' ', 1)]
        if len(value_unit) == 2:
            value, unit = value_unit
            meminfo[line] = float(value)
        else:
            meminfo[line] = float(meminfo[line])

    obj.memTotal_kB = float(meminfo['MemTotal'])
    obj.memFree_kB = float(meminfo['MemFree'])
    obj.buffers = float(meminfo['Buffers'])
    obj.cached = float(meminfo['Cached'])
    obj.SReclaimable = float(meminfo['SReclaimable'])
    obj.CommitLimit = float(meminfo['CommitLimit'])
    obj.Committed_AS = float(meminfo['Committed_AS'])
    obj.HugePages_Total = float(meminfo['HugePages_Total'])
    obj.Hugepagesize = float(meminfo['Hugepagesize'])
    obj.AnonPages = float(meminfo['AnonPages'])

    # collectd.info("%s /proc/meminfo: %s" % (PLUGIN, meminfo))
    # collectd.info("%s ---------------------------" % PLUGIN)
    # collectd.info("%s memTotal_kB    : %f" % (PLUGIN, obj.memTotal_kB))
    # collectd.info("%s memFree_kB     : %f" % (PLUGIN, obj.memFree_kB))
    # collectd.info("%s Buffers        : %f" % (PLUGIN, obj.buffers))
    # collectd.info("%s Cached         : %f" % (PLUGIN, obj.cached))
    # collectd.info("%s SReclaimable   : %f" % (PLUGIN, obj.SReclaimable))
    # collectd.info("%s CommitLimit    : %f" % (PLUGIN, obj.CommitLimit))
    # collectd.info("%s Committed_AS   : %f" % (PLUGIN, obj.Committed_AS))
    # collectd.info("%s HugePages_Total: %f" % (PLUGIN, obj.HugePages_Total))
    # collectd.info("%s AnonPages      : %f" % (PLUGIN, obj.AnonPages))

    obj.avail = float(float(obj.memFree_kB) +
                      float(obj.buffers) +
                      float(obj.cached) +
                      float(obj.SReclaimable))
    obj.total = float(float(obj.avail) +
                      float(obj.AnonPages))

    # collectd.info("%s ---------------------------" % PLUGIN)
    # collectd.info("%s memTotal: %d" % (PLUGIN, obj.avail))
    # collectd.info("%s memAvail: %d" % (PLUGIN, obj.total))

    if obj.strict == 1:
        obj.value = float(float(obj.Committed_AS) / float(obj.CommitLimit))
    else:
        obj.value = float(float(obj.AnonPages) / float(obj.total))

    obj.value = float(float(obj.value) * 100)

    # get numa node memory
    # numa_node_files = []
    # fn = "/sys/devices/system/node/"
    # files = os.listdir(fn)
    # for file in files:
    #    if 'node' in file:
    #        numa_node_files.append(fn + file)
    # collectd.info("%s numa node files: %s" %
    #               (PLUGIN, numa_node_files))

    collectd.debug('%s reports %.2f %% usage' %
                  (PLUGIN, obj.value))

    # Dispatch usage value to collectd
    val = collectd.Values(host=obj.hostname)
    val.plugin = 'memory'
    val.type = 'percent'
    val.type_instance = 'used'
    val.dispatch(values=[obj.value])

    return PASS


collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func)
