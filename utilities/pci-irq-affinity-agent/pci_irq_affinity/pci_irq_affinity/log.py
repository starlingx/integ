#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#

""" Define Logger class for this agent"""

import logging
import logging.handlers

_syslog_facility = 'local1'


LOG = logging.getLogger("pci-interrupt-affinity")
formatter = logging.Formatter("%(asctime)s %(threadName)s[%(process)d] "
                              "%(name)s.%(pathname)s.%(lineno)d - %(levelname)s "
                              "%(message)s")
handler = logging.handlers.SysLogHandler(address='/dev/log',
                                         facility=_syslog_facility)
handler.setFormatter(formatter)
LOG.addHandler(handler)
LOG.setLevel(logging.INFO)
