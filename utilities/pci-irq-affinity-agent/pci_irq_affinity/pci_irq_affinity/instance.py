#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#

""" Define instance related class"""

from log import LOG


class numa_cell:
    def __init__(self, id, cpuset, cpu_pinning):
        self.id = id
        self.cpuset = cpuset
        self.cpu_pinning = cpu_pinning


class numa_topology:
    def __init__(self, uuid, cells):
        self.instance_uuid = uuid
        self.cells = cells

    def vcpu_to_pcpu(self, vcpu):
        for cell in self.cells:
            if vcpu in cell.cpu_pinning.keys():
                return cell, cell.cpu_pinning[vcpu]
        raise KeyError('Unable to find pCPU for vCPU %d' % vcpu)


class pci_device:
    def __init__(self, addr):
        self.address = addr
        self.dev_id = ""
        self.dev_type = ""
        self.vendor_id = ""
        self.product_id = ""


class instance:
    def __init__(self, uuid, name, extra_spec):
        self.uuid = uuid
        self.name = name
        self.extra_spec = extra_spec
        self.pci_devices = set()
        self.numa_topology = None
        self.cpu_policy = 'shared'

    def update(self, domain):
        cells = set()
        for node_id in domain['nodelist']:
            cell = numa_cell(node_id, range(domain['nr_vcpus']), domain['cpu_pinning'])
            LOG.debug("cell_id=%s, vcpuset=%s, cpu_pinning=%s"
                      % (node_id, range(domain['nr_vcpus']), domain['cpu_pinning']))
            cells.update([cell])

        self.numa_topology = numa_topology(self.uuid, cells)
        if domain['IsCpuPinned']:
            self.cpu_policy = 'dedicated'
        else:
            self.cpu_policy = 'shared'

        for pci_addr in domain['pci_addrs']:
            pci_dev = pci_device(pci_addr)
            self.pci_devices.update([pci_dev])

    def get_cpu_policy(self):
        return self.cpu_policy

    def get_numa_topology(self):
        return self.numa_topology

    def get_extra_spec(self):
        return self.extra_spec

    def get_pci_devices(self):
        return self.pci_devices
