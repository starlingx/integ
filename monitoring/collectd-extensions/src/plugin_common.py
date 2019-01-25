#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
############################################################################
#
# This file contains common collectd plugin constructs and utilities
#
############################################################################

import collectd
import json
import uuid
import httplib2
import socket
import os
from fm_api import constants as fm_constants
import tsconfig.tsconfig as tsc

# http request constants
PLUGIN_TIMEOUT = 10
PLUGIN_HTTP_HEADERS = {'Accept': 'application/json', 'Connection': 'close'}

MIN_AUDITS_B4_FIRST_QUERY = 2


class PluginObject(object):

    def __init__(self, plugin, url):

        # static variables set in init_func
        self.plugin = plugin             # the name of this plugin
        self.hostname = ''               # the name of this host
        self.port = 0                    # the port number for this plugin

        # dynamic gate variables
        self.config_complete = False     # set to True once config is complete
        self.config_done = False         # set true if config_func completed ok
        self.init_done = False           # set true if init_func completed ok

        # dynamic variables set in read_func
        self.usage = float(0)            # last usage value recorded as float
        self.audits = 0                  # number of audit since init

        # http and json specific variables
        self.url = url                   # target url
        self.jresp = None                # used to store the json response
        self.resp = ''

        # Log controls
        self.config_logged = False       # used to log once the plugin config
        self.error_logged = False        # used to prevent log flooding
        self.log_throttle_count = 0      # used to count throttle logs
        self.INIT_LOG_THROTTLE = 10      # the init log throttle threshold

        collectd.debug("%s Common PluginObject constructor [%s]" %
                       (plugin, url))

    ###########################################################################
    #
    # Name       : init_ready
    #
    # Description: Test for init ready condition
    #
    # Parameters : plugin name
    #
    # Returns    : False if initial config complete is not done
    #              True if initial config complete is done
    #
    ###########################################################################

    def init_ready(self):
        """ Test for system init ready state """

        if os.path.exists(tsc.INITIAL_CONFIG_COMPLETE_FLAG) is False:
            self.log_throttle_count += 1
            if self.log_throttle_count > self.INIT_LOG_THROTTLE:
                collectd.info("%s initialization needs retry" % self.plugin)
                self.log_throttle_count = 0
            return False
        else:
            self.log_throttle_count = 0

        return True

    ###########################################################################
    #
    # Name       : gethostname
    #
    # Description: load the hostname
    #
    # Parameters : plugin name
    #
    # Returns    : Success - hostname
    #              Failure - None
    #
    # Updates    : obj.hostname
    #
    ###########################################################################
    def gethostname(self):
        """ Fetch the hostname """

        # get current hostname
        try:
            hostname = socket.gethostname()
            if hostname:
                return hostname
        except:
            collectd.error("%s failed to get hostname" % self.plugin)

        return None

    ###########################################################################
    #
    # Name       : check_for_fit
    #
    # Description: load FIT data if it is present
    #
    # Fit Format : unit data -> 0 89
    #              - instance 0 value 89
    #
    # Parameters : plugin name
    #              object to update with fit
    #              name in fit file
    #              unit
    #
    # Returns    : Did a failure occur ?
    #              False = no
    #              True  = yes
    #
    # Updates    : self.usage with FIT value if FIT conditions are present
    #              and apply
    #
    ###########################################################################
    def check_for_fit(self, name, unit):
        """ Load FIT data into usage if it exists """

        fit_file = '/var/run/fit/' + name + '_data'

        if os.path.exists(fit_file):
            valid = False
            with open(fit_file, 'r') as infile:
                for line in infile:
                    try:
                        inst, val = line.split(' ')
                        if int(unit) == int(inst):
                            self.usage = float(val)
                            valid = True

                    except:
                        try:
                            val = float(line)
                            self.usage = float(val)
                            valid = True

                        except:
                            collectd.error("%s bad FIT data; ignoring" %
                                           self.plugin)

                    if valid is True:
                        collectd.info("%s %.2f usage (unit %d) (FIT)" %
                                      (self.plugin, unit, self.usage))
                        return False

        return True

    ###########################################################################
    #
    # Name       : make_http_request
    #
    # Description: Issue an http request to the specified URL.
    #              Load and return the response
    #              Handling execution errors
    #
    # Parameters : self as current context.
    #
    #    Optional:
    #
    #              url  - override the default self url with http address to
    #                     issue the get request to.
    #              to   - timeout override
    #              hdrs - override use of the default header list
    #
    # Updates    : self.jresp with the json string response from the request.
    #
    # Returns    : Error indication (True/False)
    #              True on error
    #              False on success
    #
    ###########################################################################
    def make_http_request(self, url=None, to=None, hdrs=None):
        """ Make a blocking HTTP Request and return result """

        try:

            # handle timeout override
            if to is None:
                to = PLUGIN_TIMEOUT

            # handle url override
            if url is None:
                url = self.url

            # handle header override
            if hdrs is None:
                hdrs = PLUGIN_HTTP_HEADERS

            http = httplib2.Http(timeout=to)
            resp = http.request(url, headers=hdrs)

        except Exception as ex:
            collectd.info("%s http request failure (%s)" %
                          (self.plugin, str(ex)))
            return True

        try:
            collectd.debug("%s Resp: %s" %
                           (self.plugin, resp[1]))

            self.resp = resp[1]
            self.jresp = json.loads(resp[1])

        except Exception as ex:
            collectd.info("%s http request parse failure (%s) (%s)" %
                          (self.plugin, str(ex), resp))
            return True
        return False


def is_uuid_like(val):
    """Returns validation of a value as a UUID.

    For our purposes, a UUID is a canonical form string:
    aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
    """
    try:
        return str(uuid.UUID(val)) == val
    except (TypeError, ValueError, AttributeError):
        return False


def get_severity_str(severity):
    """ get string that represents the specified severity """

    if severity == fm_constants.FM_ALARM_SEVERITY_CLEAR:
        return "clear"
    elif severity == fm_constants.FM_ALARM_SEVERITY_CRITICAL:
        return "critical"
    elif severity == fm_constants.FM_ALARM_SEVERITY_MAJOR:
        return "major"
    elif severity == fm_constants.FM_ALARM_SEVERITY_MINOR:
        return "minor"
    else:
        return "unknown"
