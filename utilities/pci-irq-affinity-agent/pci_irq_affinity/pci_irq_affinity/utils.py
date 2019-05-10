#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#

""" Define utility functions for this agent"""

import os
import errno
from itertools import groupby

from log import LOG
import instance


def list_to_range(input_list=None):
    """Convert a list into a string of comma separate ranges.

    E.g.,  [1,2,3,8,9,15] is converted to '1-3,8-9,15'
    """
    if input_list is None:
        return ''
    if len(input_list) < 3:
        return ','.join(str(x) for x in input_list)
    else:
        G = (list(x) for _, x in groupby(enumerate(input_list),
                                         lambda i, x: i - x))
        return ','.join(
            '-'.join(map(str, (g[0][1], g[-1][1])[:len(g)])) for g in G)


def parse_cpu_spec(spec):
    """Parse a CPU set specification.

    Each element in the list is either a single CPU number, a range of
    CPU numbers, or a caret followed by a CPU number to be excluded
    from a previous range.

    :param spec: cpu set string eg "1-4,^3,6"

    :returns: a set of CPU indexes
    """
    cpuset_ids = set()
    cpuset_reject_ids = set()
    for rule in spec.split(','):
        rule = rule.strip()
        # Handle multi ','
        if len(rule) < 1:
            continue
        # Note the count limit in the .split() call
        range_parts = rule.split('-', 1)
        if len(range_parts) > 1:
            reject = False
            if range_parts[0] and range_parts[0][0] == '^':
                reject = True
                range_parts[0] = str(range_parts[0][1:])

            # So, this was a range; start by converting the parts to ints
            try:
                start, end = [int(p.strip()) for p in range_parts]
            except ValueError:
                raise Exception("Invalid range expression %r" % rule)
            # Make sure it's a valid range
            if start > end:
                raise Exception("Invalid range expression %r" % rule)
            # Add available CPU ids to set
            if not reject:
                cpuset_ids |= set(range(start, end + 1))
            else:
                cpuset_reject_ids |= set(range(start, end + 1))
        elif rule[0] == '^':
            # Not a range, the rule is an exclusion rule; convert to int
            try:
                cpuset_reject_ids.add(int(rule[1:].strip()))
            except ValueError:
                raise Exception("Invalid exclusion expression %r" % rule)
        else:
            # OK, a single CPU to include; convert to int
            try:
                cpuset_ids.add(int(rule))
            except ValueError:
                raise Exception("Invalid inclusion expression %r" % rule)

    # Use sets to handle the exclusion rules for us
    cpuset_ids -= cpuset_reject_ids

    return cpuset_ids


def _get_pci_irq_affinity_mask(extra_spec):
    """Parse pci irq affinity mask based on flavor extra-spec.

    Returns set of vcpu ids with corresponding pci irq affinity mask.
    """

    if 'hw:pci_irq_affinity_mask' in extra_spec:
        pci_irq_affinity_mask = extra_spec['hw:pci_irq_affinity_mask']
        LOG.info("pci_irq_affinity_mask: %s" % pci_irq_affinity_mask)
    else:
        LOG.info('Not set pci_irq_affinity_mask!')
        return None

    cpuset_ids = parse_cpu_spec(pci_irq_affinity_mask)
    if not cpuset_ids:
        raise Exception("No CPUs available after parsing %r" % pci_irq_affinity_mask)
    return cpuset_ids


def get_irqs_by_pci_address(pci_addr):
    """Get list of PCI IRQs based on a VF's pci address

    Raises PciDeviceNotFoundById in case the pci device is not found,
    or when there is an underlying problem getting associated irqs.
    :param pci_addr: PCI address
    :return: irqs, msi_irqs
    """
    irqs = set()
    msi_irqs = set()

    dev_path = "/sys/bus/pci/devices/%s" % (pci_addr)
    if not os.path.isdir(dev_path):
        raise Exception("PciDeviceNotFoundById id = %r" % pci_addr)

    _irqs = set()
    irq_path = "%s/irq" % (dev_path)
    try:
        with open(irq_path) as f:
            _irqs.update([int(x) for x in f.readline().split() if int(x) > 0])
    except Exception as e:
        LOG.error('get_irqs_by_pci_address: '
                  'pci_addr=%(A)s: irq_path=%(P)s; error=%(E)s',
                  {'A': pci_addr, 'P': irq_path, 'E': e})
        raise Exception("PciDeviceNotFoundById id = %r" % pci_addr)

    _msi_irqs = set()
    msi_path = "%s/msi_irqs" % (dev_path)
    try:
        _msi_irqs.update([int(x) for x in os.listdir(msi_path) if int(x) > 0])
    except OSError as e:
        # msi_path disappears during configuration; do not treat
        # non-existance as fatal
        if e.errno == errno.ENOENT:
            return (irqs, msi_irqs)
        else:
            LOG.error('get_irqs_by_pci_address: '
                      'pci_addr=%(A)s: msi_path=%(P)s; error=%(E)s',
                      {'A': pci_addr, 'P': msi_path, 'E': e})
            raise Exception("PciDeviceNotFoundById id = %r" % pci_addr)
    except Exception as e:
        LOG.error('get_irqs_by_pci_address: '
                  'pci_addr=%(A)s: msi_path=%(P)s; error=%(E)s',
                  {'A': pci_addr, 'P': msi_path, 'E': e})
        raise Exception("PciDeviceNotFoundById id = %r" % pci_addr)

    # Return only configured irqs, ignore any that are missing.
    for irq in _irqs:
        irq_path = "/proc/irq/%s" % (irq)
        if os.path.isdir(irq_path):
            irqs.update([irq])
    for irq in _msi_irqs:
        irq_path = "/proc/irq/%s" % (irq)
        if os.path.isdir(irq_path):
            msi_irqs.update([irq])
    return (irqs, msi_irqs)


def get_pci_irqs_pinned_cpuset(extra_spec=None, numa_topology=None,
                               pci_numa_node=None):
    """Get pinned cpuset where pci irq are affined.

    :param extra_spec: extra_spec
    :param pci_numa_node: numa node of a specific PCI device
    :param numa_topology: instance numa topology
    :return: cpuset, cpulist
    """
    cpuset = set()
    cpulist = ''

    LOG.debug("extra_spec:%s, topo:%s, numa_node:%s" % (extra_spec, numa_topology, pci_numa_node))
    if numa_topology is None or pci_numa_node is None or pci_numa_node < 0:
        return (cpuset, cpulist)

    # Determine full affinity cpuset, but restrict to pci's numa node
    for cell in numa_topology.cells:
        if cell.id == pci_numa_node and cell.cpu_pinning is not None:
            cpuset.update(set(cell.cpu_pinning.values()))
    LOG.info("pinning pcpu list:%s" % cpuset)

    # Use extra-spec hw:pci_irq_affinity_mask only when the instance is pinned.
    if cpuset:
        pci_cpuset = _get_pci_irq_affinity_mask(extra_spec)
        if pci_cpuset:
            cpuset = set()
            for cell in numa_topology.cells:
                if cell.cpu_pinning is not None:
                    for vcpu in cell.cpuset:
                        if vcpu in pci_cpuset:
                            vcpu_cell, pcpu = numa_topology.vcpu_to_pcpu(vcpu)
                            cpuset.update(set([pcpu]))

    cpulist = list_to_range(input_list=list(cpuset))
    return (cpuset, cpulist)


def set_irq_affinity(set_bitmap, irqs, cpulist):
    """Set irq affinity to the specified cpulist for list of irqs.

    :param set_bitmap: True: set bitmap file, False: set list file
    :param irqs: irq list
    :param cpulist: cpu list
    """
    _irqs = set()

    if set_bitmap:
        filename = 'smp_affinity'
    else:
        filename = 'smp_affinity_list'

    for irq in irqs:
        irq_aff_path = "/proc/irq/%s/%s" % (irq, filename)
        try:
            with open(irq_aff_path, 'w') as f:
                f.write(cpulist)
            _irqs.update([irq])
        except Exception as e:
            LOG.warning("Failed to write pci affine file:%(F)s, irq:%(I)s, "
                        "error=%(E)s"
                        % {"F": filename, "I": irq, "E": e})
    return _irqs


def set_irqs_affinity_by_pci_address(pci_addr, extra_spec=None,
                                     numa_topology=None):
    """Set cpu affinity for list of PCI IRQs with a VF's pci address,

    Restrict cpuset to the numa node of the PCI.
    Return list
    Raises PciDeviceNotFoundById in case the pci device is not found,
    or when there is an underlying problem getting associated irqs.
    :param pci_addr: PCI address
    :param extra_spec: extra_spec
    :param numa_topology: instance numa topology
    :return: irqs, msi_irqs, numa_node, cpulist
    """
    irqs = set()
    msi_irqs = set()
    numa_node = None
    cpulist = ''

    if numa_topology is None:
        return (irqs, msi_irqs, numa_node, cpulist)

    # Get the irqs associated with pci addr
    _irqs, _msi_irqs = get_irqs_by_pci_address(pci_addr)
    LOG.debug("pci: %s, irqs: %s, msi_irqs: %s" % (pci_addr, _irqs, _msi_irqs))

    # Obtain physical numa_node for this pci addr
    numa_path = "/sys/bus/pci/devices/%s/numa_node" % (pci_addr)
    try:
        with open(numa_path) as f:
            numa_node = [int(x) for x in f.readline().split()][0]
    except Exception as e:
        LOG.error('set_irqs_affinity_by_pci_address: '
                  'pci_addr=%(A)s: numa_path=%(P)s; error=%(E)s',
                  {'A': pci_addr, 'P': numa_path, 'E': e})
        raise Exception("PciDeviceNotFoundById id = %r" % pci_addr)
    # Skip irq configuration if there is no associated numa node
    if numa_node is None or numa_node < 0:
        return (irqs, msi_irqs, numa_node, cpulist)

    # Determine the pinned cpuset where irqs are to be affined
    cpuset, cpulist = get_pci_irqs_pinned_cpuset(extra_spec,
                                                 numa_topology,
                                                 numa_node)

    LOG.debug("cpuset where irqs are to be affined:%s or %s" % (cpuset, cpulist))

    # Skip irq configuration if there are no pinned cpus
    if not cpuset:
        return (irqs, msi_irqs, numa_node, cpulist)

    # Set IRQ affinity, but do not treat errors as fatal.
    irqs = set_irq_affinity(False, _irqs, cpulist)
    msi_irqs = set_irq_affinity(False, _msi_irqs, cpulist)
    return (irqs, msi_irqs, numa_node, cpulist)
