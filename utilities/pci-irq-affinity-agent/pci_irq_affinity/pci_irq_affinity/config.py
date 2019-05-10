#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#

""" Define configuration info for pci-irq-affinity-agent"""

from six.moves import configparser
from oslo_config import cfg

pci_irq_affinity_opts = [
    cfg.IntOpt('pci_affine_interval',
               default=60,
               help='Number of seconds between pci affinity updates'),
    cfg.IntOpt('msi_irq_timeout',
               default=45,
               help='Number of seconds to wait for msi irq configuration'),
    cfg.IntOpt('msi_irq_since',
               default=6,
               help='Number of seconds to wait for msi irqs to stabilize.'),
    cfg.IntOpt('msi_irq_check_interval',
               default=2,
               help='Check interval in seconds for msi irqs to stabilize.'),
    cfg.StrOpt('config_file',
               default='/etc/pci_irq_affinity/config.ini',
               help='Get config info from specific config file.'),
]

CONF = cfg.CONF


def register_opts(conf):
    conf.register_opts(pci_irq_affinity_opts)


register_opts(CONF)

sysconfig = configparser.ConfigParser()
sysconfig.read(CONF.config_file)
