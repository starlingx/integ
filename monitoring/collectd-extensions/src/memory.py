#
# Copyright (c) 2018-2019 Wind River Systems, Inc.
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
#    - if 'worker_reserved.conf exists then query/store PLATFORM_CPU_LIST
#
############################################################################
import os
import collectd

debug = False

PLUGIN = 'platform memory usage'
PLUGIN_NUMA = 'numa memory usage'
PLUGIN_HUGE = 'hugepage memory usage'


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
    HugePages_Free = 0
    Hugepagesize = 0
    AnonPages = 0
    FilePages = 0

    # derived values
    avail = 0
    total = 0
    strict = 0


# Instantiate the class
obj = MEM()


def log_meminfo(plugin, name, meminfo):
    """Log the supplied meminfo"""

    if debug is False:
        return

    collectd.info("%s %s" % (plugin, name))
    collectd.info("%s ---------------------------" % plugin)
    collectd.info("%s memTotal_kB    : %f" % (plugin, meminfo.memTotal_kB))
    collectd.info("%s memFree_kB     : %f" % (plugin, meminfo.memFree_kB))
    collectd.info("%s Buffers        : %f" % (plugin, meminfo.buffers))
    collectd.info("%s Cached         : %f" % (plugin, meminfo.cached))
    collectd.info("%s SReclaimable   : %f" % (plugin, meminfo.SReclaimable))
    collectd.info("%s CommitLimit    : %f" % (plugin, meminfo.CommitLimit))
    collectd.info("%s Committed_AS   : %f" % (plugin, meminfo.Committed_AS))
    collectd.info("%s HugePages_Total: %f" % (plugin, meminfo.HugePages_Total))
    collectd.info("%s HugePages_Free : %f" % (plugin, meminfo.HugePages_Free))
    collectd.info("%s Hugepagesize   : %f" % (plugin, meminfo.Hugepagesize))
    collectd.info("%s AnonPages      : %f" % (plugin, meminfo.AnonPages))


def config_func(config):
    """Configure the memory usage plugin"""

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


# Load the hostname and kernel memory 'overcommit' setting.
def init_func():
    # get current hostname
    obj.hostname = os.uname()[1]

    # get strict setting
    #
    # a value of 0 means "heuristic overcommit"
    # a value of 1 means "always overcommit"
    # a value of 2 means "don't overcommit".
    #
    # set strict true strict=1 if value is = 2
    # otherwise strict is false strict=0 (default)

    fn = '/proc/sys/vm/overcommit_memory'
    if os.path.exists(fn):
        with open(fn, 'r') as infile:
            for line in infile:
                if int(line) == 2:
                    obj.strict = 1
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
        return 0

    # setup the sample structure
    val = collectd.Values(host=obj.hostname)
    val.type = 'percent'
    val.type_instance = 'used'

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
    obj.HugePages_Free = float(meminfo['HugePages_Free'])
    obj.Hugepagesize = float(meminfo['Hugepagesize'])
    obj.AnonPages = float(meminfo['AnonPages'])

    log_meminfo(PLUGIN, "/proc/meminfo", obj)

    obj.avail = float(float(obj.memFree_kB) +
                      float(obj.buffers) +
                      float(obj.cached) +
                      float(obj.SReclaimable))
    obj.total = float(float(obj.avail) +
                      float(obj.AnonPages))

    if obj.strict == 1:
        obj.value = float(float(obj.Committed_AS) / float(obj.CommitLimit))
    else:
        obj.value = float(float(obj.AnonPages) / float(obj.total))
    obj.value = float(float(obj.value) * 100)

    if debug is True:
        collectd.info("%s ---------------------------" % PLUGIN)
        collectd.info("%s memAvail: %d" % (PLUGIN, obj.avail))
        collectd.info("%s memTotal: %d" % (PLUGIN, obj.total))
        collectd.info('%s reports %.2f %% usage' % (PLUGIN, obj.value))

    # Dispatch usage value to collectd
    val.plugin = 'memory'
    val.plugin_instance = 'platform'
    val.dispatch(values=[obj.value])

    #####################################################################
    # Now get the Numa Node Memory Usage
    #####################################################################
    numa_node_files = []
    fn = "/sys/devices/system/node/"
    files = os.listdir(fn)
    for file in files:
        if 'node' in file:
            numa_node_files.append(fn + file + '/meminfo')

    for numa_node in numa_node_files:
        meminfo = {}
        try:
            with open(numa_node) as fd:
                for line in fd:
                    meminfo[line.split()[2][0:-1]] = line.split()[3].strip()

            obj.memFree_kB = float(meminfo['MemFree'])
            obj.FilePages = float(meminfo['FilePages'])
            obj.SReclaimable = float(meminfo['SReclaimable'])
            obj.AnonPages = float(meminfo['AnonPages'])
            obj.HugePages_Total = float(meminfo['HugePages_Total'])
            obj.HugePages_Free = float(meminfo['HugePages_Free'])

            log_meminfo(PLUGIN, numa_node, obj)

            avail = float(float(obj.memFree_kB) +
                          float(obj.FilePages) +
                          float(obj.SReclaimable))
            total = float(float(avail) +
                          float(obj.AnonPages))
            obj.value = float(float(obj.AnonPages)) / float(total)
            obj.value = float(float(obj.value) * 100)

            # Dispatch usage value to collectd for this numa node
            val.plugin_instance = numa_node.split('/')[5]
            val.dispatch(values=[obj.value])

            collectd.debug('%s reports %s at %.2f %% usage (%s)' %
                           (PLUGIN_NUMA,
                            val.plugin,
                            obj.value,
                            val.plugin_instance))

            # Numa Node Huge Page Memory Monitoring
            #
            # Only monitor if there is Huge Page Memory
            if obj.HugePages_Total > 0:
                obj.value = \
                    float(float(obj.HugePages_Total -
                                obj.HugePages_Free)) / \
                    float(obj.HugePages_Total)
                obj.value = float(float(obj.value) * 100)

                # Dispatch huge page memory usage value
                # to collectd for this numa node.
                val.plugin_instance = numa_node.split('/')[5] + '_hugepages'
                val.dispatch(values=[obj.value])

                collectd.debug('%s reports %s at %.2f %% usage (%s)' %
                               (PLUGIN_HUGE,
                                val.plugin,
                                obj.value,
                                val.plugin_instance))

        except EnvironmentError as e:
            collectd.error("%s unable to read from %s ; str(e)" %
                           (PLUGIN_NUMA, str(e)))

    return 0


collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func)
