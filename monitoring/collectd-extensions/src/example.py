#
# Copyright (c) 2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import os
import random
import collectd

PLUGIN = 'random number plugin'

# static variables


# define a class here that will persist over read calls
class ExampleObject:
    hostname = ""
    plugin_data = ['1', '100']


obj = ExampleObject()


# The config function - called once on collectd process startup
def config_func(config):
    """Configure the plugin"""

    for node in config.children:
        key = node.key.lower()
        val = node.values[0]

        if key == 'data':
            obj.plugin_data = str(val).split(' ')
            collectd.info("%s configured data '%d:%d'" %
                          (PLUGIN,
                           int(obj.plugin_data[0]),
                           int(obj.plugin_data[1])))
            return 0

    collectd.info('%s config function' % PLUGIN)
    return 0


# The init function - called once on collectd process startup
def init_func():

    # get current hostname
    obj.hostname = os.uname()[1]
    return 0


# The sample read function - called on every audit interval
def read_func():

    # do the work to create the sample
    low = int(obj.plugin_data[0])
    high = int(obj.plugin_data[1])
    sample = random.randint(low, high)

    # Dispatch usage value to collectd
    val = collectd.Values(host=obj.hostname)
    val.plugin = 'example'
    val.type = 'percent'
    val.type_instance = 'used'
    val.dispatch(values=[sample])
    return 0


# register the config, init and read functions
collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func)
