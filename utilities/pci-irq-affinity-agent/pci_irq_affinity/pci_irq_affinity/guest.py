#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#

""" Encapsulate libvirt related interfaces"""

import libvirt
import os
import sys
import signal
from xml.dom import minidom
from xml.etree import ElementTree
from log import LOG

debug = 0
# libvirt timeout parameters
LIBVIRT_TIMEOUT_SEC = 5.0
total_cpus = 0


def range_to_list(csv_range=None):
    """Convert a string of comma separate ranges into an expanded list of integers.

    E.g., '1-3,8-9,15' is converted to [1,2,3,8,9,15]
    """
    if not csv_range:
        return []
    xranges = [(lambda L: range(L[0], L[-1] + 1))(map(int, r.split('-')))
               for r in csv_range.split(',')]
    return [y for x in xranges for y in x]


def _translate_virDomainState(state):
    """Return human readable virtual domain state string."""
    states = {}
    states[0] = 'NOSTATE'
    states[1] = 'Running'
    states[2] = 'Blocked'
    states[3] = 'Paused'
    states[4] = 'Shutdown'
    states[5] = 'Shutoff'
    states[6] = 'Crashed'
    states[7] = 'pmSuspended'
    states[8] = 'Last'
    return states[state]


def _mask_to_cpulist(mask=0):
    """Create cpulist from mask, list in socket-core-thread enumerated order.

    :param extended: extended info
    :param mask: cpuset mask
    :returns cpulist: list of cpus in socket-core-thread enumerated order
    """
    cpulist = []
    if mask is None or mask <= 0:
        return cpulist

    # Assume max number of cpus for now...
    max_cpus = 1024
    for cpu in range(max_cpus):
        if ((1 << cpu) & mask):
            cpulist.append(cpu)
    return cpulist


class suppress_stdout_stderr(object):
    """A context manager for doing a "deep suppression" of stdout and stderr in Python

    i.e. will suppress all print, even if the print originates in a compiled C/Fortran
    sub-function.
    This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).
    """
    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close the null files
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError('timeout')


def connect_to_libvirt():
    """Connect to local libvirt."""
    duri = "qemu:///system"
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, LIBVIRT_TIMEOUT_SEC)
        with suppress_stdout_stderr():
            conn = libvirt.openReadOnly(duri)
        signal.alarm(0)
    except TimeoutError:
        conn = None
        raise
    except Exception as e:
        conn = None
        raise
    finally:
        signal.alarm(0)
        return conn


def get_host_cpu_topology():
    """Enumerate logical cpu topology using socket_id, core_id, thread_id.

    This generates the following dictionary:
    topology[socket_id][core_id][thread_id] = cpu_id
    """
    global total_cpus

    # Connect to local libvirt hypervisor
    conn = connect_to_libvirt()
    # Get host capabilities
    caps_str = conn.getCapabilities()
    doc = ElementTree.fromstring(caps_str)
    caps = minidom.parseString(caps_str)
    caps_host = caps.getElementsByTagName('host')[0]
    caps_cells = caps_host.getElementsByTagName('cells')[0]
    total_cpus = caps_cells.getElementsByTagName('cpu').length

    Thread_cnt = {}
    topology = {}
    cells = doc.findall('./host/topology/cells/cell')
    for cell in cells:
        for cpu in cell.findall('./cpus/cpu'):
            # obtain core_id, cpu_id, and socket_id; ignore 'siblings' since
            # that can be inferred by enumeration of thread_id.
            core_id = int(cpu.get('core_id'))
            cpu_id = int(cpu.get('id'))
            socket_id = int(cpu.get('socket_id'))

            # thread_id's are enumerated assuming cpu_id is already sorted
            if socket_id not in Thread_cnt:
                Thread_cnt[socket_id] = {}
            if core_id not in Thread_cnt[socket_id]:
                Thread_cnt[socket_id][core_id] = 0
            else:
                Thread_cnt[socket_id][core_id] += 1
            thread_id = Thread_cnt[socket_id][core_id]

            # save topology[socket_id][core_id][thread_id]
            if socket_id not in topology:
                topology[socket_id] = {}
            if core_id not in topology[socket_id]:
                topology[socket_id][core_id] = {}
            topology[socket_id][core_id][thread_id] = cpu_id
    conn.close()
    return topology


def get_guest_domain_info(dom):
    """Obtain cpulist of pcpus in the order of vcpus.

    This applies to either pinned or floating vcpus,  Note that the cpuinfo
    pcpu value can be stale if we scale down cpus since it reports cpu-last-run.
    For this reason use cpumap = d_vcpus[1][vcpu], instead of cpuinfo
    (i.e., vcpu, state, cpuTime, pcpu = d_vcpus[0][vcpu]).
    """
    uuid = dom.UUIDString()
    d_state, d_maxMem_KiB, d_memory_KiB, \
        d_nrVirtCpu, d_cpuTime = dom.info()
    try:
        with suppress_stdout_stderr():
            d_vcpus = dom.vcpus()
    except Exception as e:
        d_vcpus = tuple([d_nrVirtCpu * [],
                        d_nrVirtCpu * [tuple(total_cpus * [False])]])

    cpulist_p = []
    cpulist_d = {}
    cpuset_total = 0
    up_total = 0
    for vcpu in range(d_nrVirtCpu):
        cpuset_b = d_vcpus[1][vcpu]
        cpuset = 0
        for cpu, up in enumerate(cpuset_b):
            if up:
                cpulist_d[vcpu] = cpu
                aff = 1 << cpu
                cpuset |= aff
                up_total += 1
        cpuset_total |= cpuset
    cpulist_f = _mask_to_cpulist(mask=cpuset_total)
    for key in sorted(cpulist_d.keys()):
        cpulist_p.append(cpulist_d[key])

    # Determine if floating or pinned, display appropriate cpulist
    if up_total > d_nrVirtCpu:
        d_cpulist = cpulist_f
        cpu_pinned = False
    else:
        d_cpulist = cpulist_p
        cpu_pinned = True

    # Determine list of numa nodes (the hard way)
    dom_xml = ElementTree.fromstring(dom.XMLDesc(0))
    nodeset = set([])
    for elem in dom_xml.findall('./numatune/memnode'):
        nodes = range_to_list(elem.get('nodeset'))
        nodeset.update(nodes)
    d_nodelist = list(sorted(nodeset))

    # Get pci info.
    pci_addrs = set()
    for interface in dom_xml.findall('./devices/interface'):
        if interface.find('driver').get('name').startswith('vfio'):
            addr_tag = interface.find('source/address')
            if addr_tag.get('type') == 'pci':
                pci_addr = "%04x:%02x:%02x.%01x" % (
                    addr_tag.get('domain'),
                    addr_tag.get('bus'),
                    addr_tag.get('slot'),
                    addr_tag.get('function'))
                pci_addrs.update([pci_addr])

    # Update dictionary with per-domain information
    domain = {
        'uuid': uuid,
        'state': _translate_virDomainState(d_state),
        'IsCpuPinned': cpu_pinned,
        'nr_vcpus': d_nrVirtCpu,
        'nodelist': d_nodelist,
        'cpulist': d_cpulist,
        'cpu_pinning': cpulist_d,
        'pci_addrs': pci_addrs
    }
    return domain


def get_guest_domain_by_uuid(conn, uuid):
    try:
        dom = conn.lookupByUUIDString(uuid)
    except Exception as e:
        LOG.warning("Failed to get domain for uuid=%s! error=%s" % (uuid, e))
        return None
    domain = get_guest_domain_info(dom)
    return domain
