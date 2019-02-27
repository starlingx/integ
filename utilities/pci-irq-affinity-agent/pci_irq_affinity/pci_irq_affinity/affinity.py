#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#

""" Define pci_irq_affinity_provider class"""

import utils as pci_utils
from driver import AffinePciIrqDriver
from nova_provider import novaClient
from log import LOG


class pci_irq_affinity_provider:
    def __init__(self):
        self.affinePciIrqDriver = AffinePciIrqDriver()
        self.inst_dict = {}

    def reset_irq_affinity(self, uuid, irqs=None, msi_irqs=None):
        """Reset irq affinity for instance

        The instance has already been deleted or
        related PCI not used by it anymore.
        """
        if irqs or msi_irqs:
            # reset irq affinity for specified irqs
            _irqs = irqs
            _msi_irqs = msi_irqs

        elif uuid in self.inst_dict:
            # reset all irq affinity for deleted instance
            _irqs = self.inst_dict[uuid][0]
            _msi_irqs = self.inst_dict[uuid][1]
        else:
            LOG.debug("No pci affinity need to be reset for instance=%s!" % uuid)
            return

        try:
            with open('/proc/irq/default_smp_affinity') as f:
                cpulist = f.readline().strip()
            LOG.debug("default smp affinity bitmap:%s" % cpulist)

            for x in [_irqs, _msi_irqs]:
                if len(x) > 0:
                    pci_utils.set_irq_affinity(True, x, cpulist)

        except Exception as e:
            LOG.error("Failed to reset smp affinity! error=%s" % e)

        LOG.info("Reset smp affinity done for instance=%s!" % uuid)

    def instance_irq_pcpulist_update(self, uuid, irqs, msi_irqs, cpulist):
        if uuid in self.inst_dict:
            _prev = self.inst_dict[uuid]
            # get irqs that not appear anymore.
            _irqs = _prev[0].difference(irqs)
            _msi_irqs = _prev[1].difference(msi_irqs)

            # reset pci affinity for those pcis not used by intance anymore
            if (len(_irqs) + len(_msi_irqs)) > 0:
                self.reset_irq_affinity(uuid, _irqs, _msi_irqs)

        self.inst_dict[uuid] = [irqs, msi_irqs, cpulist]
        LOG.debug(self.inst_dict)

    def affine_pci_dev_instance(self, instance, wait_for_irqs=True):
        if instance is not None:
            if instance.get_cpu_policy() == 'dedicated' and instance.get_pci_devices():
                LOG.debug("Instance=%s use dedicated cpu policy!!!" % instance.uuid)
                irqs, msi_irqs, cpulist = \
                    self.affinePciIrqDriver.affine_pci_dev_irqs(instance, wait_for_irqs)
                # record instance on which pci affinity has been applied
                self.instance_irq_pcpulist_update(instance.uuid, irqs, msi_irqs, cpulist)
                return

    def audit_pci_irq_affinity(self):
        # audit instance PCI devices periodically
        filters = {'vm_state': 'active',
                   'task_state': None,
                   'deleted': False}
        instances = novaClient.get_instances(filters)
        for inst in instances:
            self.affine_pci_dev_instance(inst, wait_for_irqs=False)


pciIrqAffinity = pci_irq_affinity_provider()
