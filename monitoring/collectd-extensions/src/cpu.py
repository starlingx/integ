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
import time
import collectd

debug = False

PASS = 0
FAIL = 1

PATH = '/proc/cpuinfo'
COMPUTE_RESERVED_CONF = '/etc/nova/compute_reserved.conf'

PLUGIN = 'platform cpu usage plugin'


# CPU Control class
class CPU:
    hostname = ""            # hostname for sample notification message
    usage = float(0.0)       # float value of cpu usage

    processors = int(0)      # number of processors for all cpus case
    cpu_list = []            # list of CPUs to calculate combined usage for
    cpu_time = []            # schedstat time for each CPU
    cpu_time_last = []       # last schedstat time for each CPU
    time_last = float(0.0)   # float of the time the last sample was taken

    def log_error(self, err_str):
        """ Print an error log with plugin name prefixing the log """

        collectd.error("%s %s" % (PLUGIN, err_str))

# Instantiate the class
c = CPU()


# The collectd configuration interface
# collectd needs this defined ; but not used/needed.
def config_func(config):
    collectd.info('%s config function' % PLUGIN)


# Get the platform cpu list and number of cpus reported by /proc/cpuinfo
def init_func():
    # get current hostname
    c.hostname = os.uname()[1]

    collectd.info('%s init function for %s' % (PLUGIN, c.hostname))

    raw_list = ""
    if os.path.exists(COMPUTE_RESERVED_CONF):
        with open(COMPUTE_RESERVED_CONF, 'r') as infile:
            for line in infile:
                if 'PLATFORM_CPU_LIST' in line:
                    val = line.split("=")
                    raw_list = val[1].strip('\n')[1:-1].strip('"')
                    break
    if raw_list:

        # Convert the cpu list fetched from the compute
        # reserved file into an integer list.
        # Handle mix of number list #,# and number range #-#
        split_list = raw_list.split(',')
        if debug:
            collectd.info('%s split list: %s' % (PLUGIN, split_list))
        for cpu in split_list:
            if cpu.find('-') == -1:
                # add individual cpu # with assumed ',' delimiter
                c.cpu_list.append(int(cpu))
            else:
                # add all in range #-#
                cpu_range = cpu.split('-')
                if len(cpu_range) == 2:
                    first = int(cpu_range[0])
                    last = int(cpu_range[1]) + 1
                    # add each
                    for i in list(range(first, last)):
                        c.cpu_list.append(i)

        # with the full CPU list in hand we can now just read their samples
        if debug:
            collectd.info('%s full cpu list: %s' %
                          (PLUGIN, c.cpu_list))

    try:
        f = open('/proc/cpuinfo')
    except EnvironmentError as e:
        collectd.error(str(e), UserWarning)
    else:

        if len(c.cpu_list) == 0:
            _want_all_cpus = True
        else:
            _want_all_cpus = False

        c.processors = 0
        for line in f:
            name_value = [s.strip() for s in line.split(':', 1)]
            if len(name_value) != 2:
                continue

            name, value = name_value
            if 'rocessor' in name:
                if _want_all_cpus is True:
                    c.cpu_list.append(int(c.processors))
                c.processors += 1

        collectd.info('%s has found %d cpus total' %
                      (PLUGIN, c.processors))
        collectd.info('%s monitoring %d cpus %s' %
                      (PLUGIN, len(c.cpu_list), c.cpu_list))
        f.close()


# Calculate the CPU usage sample
def read_func():
    try:
        f = open('/proc/schedstat')
    except EnvironmentError as e:
        c.log_error('file open failed ; ' + str(e))
        return FAIL
    else:
        # schedstat time for each CPU
        c.cpu_time = []

        # Loop over each line ...
        #  get the output version ; only 15 is supported
        #  get the cpu time from each line staring with 'cpux ....'
        for line in f:

            # break each line into name/value pairs
            line_split = [s.strip() for s in line.split(' ', 1)]
            name, value = line_split

            # get the output version.
            if 'ersion' in name:
                try:
                    c.version = int(value)
                except ValueError as e:
                    c.log_error('got invalid schedstat version ; ' + str(e))

                    # TODO: Consider exiting here and raising alarm.
                    # Calling this type of exit will stop the plugin.
                    # sys._exit()
                    return FAIL

            # only version 15 is supported
            if c.version == 15:
                if 'cpu' in name:
                    # get the cpu number for each line
                    if int(name.replace('cpu', '')) in c.cpu_list:
                        _in_list = True
                    else:
                        _in_list = False

                    # get cpu time for each cpu that is valid
                    if len(c.cpu_list) == 0 or _in_list is True:
                        _schedstat = value
                        value_split = value.split(' ')
                        c.cpu_time.append(float(value_split[6]))
                        if debug:
                            collectd.info('%s %s schedstat is %s [%s]' %
                                          (PLUGIN, name, value_split[6],
                                           _schedstat))
            else:
                collectd.error('%s unsupported schedstat version [%d]' %
                              (PLUGIN, c.version))
                return 0

        f.close()

    # Now that we have the cpu time recorded for each cpu
    _time_delta = float(0)
    _cpu_count = int(0)
    if len(c.cpu_time_last) == 0:
        c.time_last = time.time()
        if c.cpu_list:
            # This is a compute node.
            # Do not include vswitch or pinned cpus in calculation.
            for cpu in c.cpu_list:
                c.cpu_time_last.append(float(c.cpu_time[_cpu_count]))
                _cpu_count += 1
        if debug:
            collectd.info('%s cpu time ; first pass ; %s' %
                          (PLUGIN, c.cpu_time))
        return PASS
    else:
        _time_this = time.time()
        _time_delta = _time_this - c.time_last
        c.total_avg_cpu = 0
        cpu_occupancy = []
        if debug:
            collectd.info('%s cpu time ; this pass ; %s -> %s' %
                          (PLUGIN, c.cpu_time_last, c.cpu_time))

    if c.cpu_list:
        # This is a compute node.
        # Do not include vswitch or pinned cpus in calculation.
        for cpu in c.cpu_list:
            if cpu >= c.processors:
                c.log_error(' got out of range cpu number')
            else:
                _delta = (c.cpu_time[_cpu_count] - c.cpu_time_last[_cpu_count])
                _delta = _delta / 1000000 / _time_delta
                cpu_occupancy.append(float((100*(_delta))/1000))
                c.total_avg_cpu += cpu_occupancy[_cpu_count]
                if debug:
                    collectd.info('%s cpu %d - count:%d [%s]' %
                                  (PLUGIN, cpu, _cpu_count, cpu_occupancy))
                _cpu_count += 1

    else:
        collectd.info('%s no cpus to monitor' % PLUGIN)
        return 0

    c.usage = c.total_avg_cpu / _cpu_count
    if debug:
        collectd.info('%s reports %.2f %% usage (averaged)' %
                      (PLUGIN, c.usage))

    # Prepare for next audit ; mode now to last
    # c.cpu_time_last = []
    c.cpu_time_last = c.cpu_time
    c.time_last = _time_this

    # Dispatch usage value to collectd
    val = collectd.Values(host=c.hostname)
    val.plugin = 'cpu'
    val.type = 'percent'
    val.type_instance = 'used'
    val.dispatch(values=[c.usage])

    return 0


collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func)
