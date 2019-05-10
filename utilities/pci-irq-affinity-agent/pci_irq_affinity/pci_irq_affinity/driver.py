#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#

""" Define AffinePciIrqDriver class"""

from oslo_service import loopingcall
from oslo_concurrency import lockutils
import utils as pci_utils
import instance
from config import CONF
from log import LOG
from nova_provider import novaClient

synchronized = lockutils.synchronized_with_prefix('pci_irq_affinity-')


class AffinePciIrqDriver:

    def __init__(self):
        self._msi_irq_count = {}
        self._msi_irq_since = {}
        self._msi_irq_elapsed = {}

    def affine_pci_dev_irqs(self, inst, wait_for_irqs=True):
        """Affine PCI device irqs to VM's pcpus."""

        def _wait_for_msi_irqs(self, inst):
            """Check if each pci device has the expected number of msi irqs."""
            _prev = self._msi_irq_count.copy()
            addrs = set()

            for pci_dev in inst.pci_devices:
                addr = pci_dev.address
                addrs.update([addr])
                try:
                    irqs, msi_irqs = pci_utils.get_irqs_by_pci_address(addr)
                except Exception as e:
                    msi_irqs = set()
                    LOG.error('_wait_for_msi_irqs: pci_addr=%(A)s, error=%(E)s' %
                              {'A': addr, 'E': e})
                self._msi_irq_count[addr] = len(msi_irqs)
                self._msi_irq_elapsed[addr] += \
                    CONF.msi_irq_check_interval
                if _prev[addr] == self._msi_irq_count[addr]:
                    self._msi_irq_since[addr] += \
                        CONF.msi_irq_check_interval
                else:
                    self._msi_irq_since[addr] = 0

            # Done when msi irq counts have not changed for some time
            if all((self._msi_irq_count[k] > 0) and
                   (self._msi_irq_since[k] >= CONF.msi_irq_since)
                   for k in addrs):
                raise loopingcall.LoopingCallDone()

            # Abort due to timeout
            if all(self._msi_irq_elapsed[k] >= CONF.msi_irq_timeout
                   for k in addrs):
                msg = ("reached %(timeout)s seconds timeout, waiting for "
                       "msi irqs of pci_addrs: %(addrs)s") % {
                           'timeout': CONF.msi_irq_timeout,
                           'addrs': list(addrs)}
                LOG.warning(msg)
                raise loopingcall.LoopingCallDone()

        # Determine how many msi irqs we expect to be configured.
        if len(inst.get_pci_devices()) == 0:
            return

        # Initialize msi irq tracking.
        for pci_dev in inst.pci_devices:
            if wait_for_irqs or (pci_dev.address not in self._msi_irq_count):
                self._msi_irq_count[pci_dev.address] = 0
                self._msi_irq_since[pci_dev.address] = 0
                self._msi_irq_elapsed[pci_dev.address] = 0

        # Wait for msi irqs to be configured.
        if wait_for_irqs:
            timer = loopingcall.FixedIntervalLoopingCall(
                _wait_for_msi_irqs, self, inst)
            timer.start(interval=CONF.msi_irq_check_interval).wait()

        @synchronized(inst.uuid)
        def do_affine_pci_dev_instance(refresh_need):
            """Set pci device irq affinity for this instance."""

            _irqs = set()
            _msi_irqs = set()
            # refresh instance info.
            if refresh_need:
                _inst = novaClient.get_instance(inst.uuid)
            if _inst is None:
                return

            numa_topology = _inst.get_numa_topology()
            extra_spec = _inst.get_extra_spec()
            for pci_dev in _inst.pci_devices:
                try:
                    irqs, msi_irqs, pci_numa_node, pci_cpulist = \
                        pci_utils.set_irqs_affinity_by_pci_address(
                            pci_dev.address, extra_spec, numa_topology)
                except Exception as e:
                    irqs = set()
                    msi_irqs = set()
                    pci_numa_node = None
                    pci_cpulist = ''
                    LOG.error("Could not affine irqs for pci_addr:%(A)s, "
                              "error: %(E)s" % {"A": pci_dev.address, "E": e})

                # Log irqs affined when there is a change in the counts.
                msi_irq_count = len(msi_irqs)
                if ((msi_irq_count != self._msi_irq_count[pci_dev.address]) or
                        wait_for_irqs):
                    self._msi_irq_count[pci_dev.address] = msi_irq_count
                    LOG.info(("Instance=%(U)s: IRQs affined for pci_addr=%(A)s, "
                              "dev_id=%(D)s, dev_type=%(T)s, "
                              "vendor_id=%(V)s, product_id=%(P)s, "
                              "irqs=%(I)s, msi_irqs=%(M)s, "
                              "numa_node=%(N)s, cpulist=%(C)s")
                             % {'U': inst.uuid,
                                'A': pci_dev.address,
                                'D': pci_dev.dev_id,
                                'T': pci_dev.dev_type,
                                'V': pci_dev.vendor_id,
                                'P': pci_dev.product_id,
                                'I': ', '.join(map(str, irqs)),
                                'M': ', '.join(map(str, msi_irqs)),
                                'N': pci_numa_node, 'C': pci_cpulist})
                _irqs.update(irqs)
                _msi_irqs.update(msi_irqs)
            return (_irqs, _msi_irqs, pci_cpulist)
        return do_affine_pci_dev_instance(wait_for_irqs)

