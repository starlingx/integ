#
# Copyright (c) 2014-2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""
usage: vm-topology [-h]
                   [-s <brief,all,aggregates,computes,flavors,images,
                        libvirt,migrations,server_groups,servers,
                        topology,topology-long>]

Tool to summarize server resource usage and vcpu placement
related attributes for nova and libvirt.

Details:
- shows nova view of server attributes including extended resources:
   - project, compute host, server name, libvirt name, image name, flavor
   - vm status, task state, power state, uptime
   - pinning, numa nodes, cpuset, cpulists, server groups
- shows nova view of compute resource usage, aggregates
- shows libvirt view of servers, running state
- shows migrations in-progress
- shows flavors used
- shows images used
"""

import argparse
import datetime
import copy
import libvirt
import logging
from itertools import groupby
import multiprocessing
import os
import pprint
from prettytable import PrettyTable
import psutil
import re
import sys
import signal
import textwrap
import time

from cinderclient import client as cinder_client
from glanceclient import client as glance_client
from keystoneclient.auth.identity import v3 as keystone_identity
from keystoneclient.v3 import client as keystone_client
from keystoneauth1 import loading as keystone
from keystoneauth1 import session
from novaclient import client as nova_client
from novaclient.v2 import migrations

from oslo_serialization import jsonutils

from sqlalchemy.ext.automap import automap_base
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy.sql import select

from xml.dom import minidom
from xml.etree import ElementTree

NOVACONF = '/etc/nova/nova.conf'
AUTHTOKEN_GROUP = 'keystone_authtoken'
NOVACLIENT_VERSION = '2.25'
CINDERCLIENT_VERSION = '2'

# NOTE: Old glanceclient version 1 gives access to image properties
GLANCECLIENT_VERSION = '1'

from keystonemiddleware.auth_token import _opts as keystone_auth_token_opts
from oslo_config import cfg
from oslo_config import types

CONF = cfg.CONF

"""----------------------------------------------------------------------------
Global definitions
----------------------------------------------------------------------------"""

# logger
logger = logging.getLogger(__name__)
logging.getLogger('multiprocessing').setLevel(logging.CRITICAL)
logging.getLogger('sqlalchemy.engine').setLevel(logging.CRITICAL)

# debug and show options
debug = {}
show = {}

# Constants
Ki = 1024
Mi = Ki*Ki

# Active worker pids
active_pids = multiprocessing.Manager().dict()

# libvirt timeout parameters
LIBVIRT_TIMEOUT_SEC = 5.0
LIBVIRT_REAP_SEC = LIBVIRT_TIMEOUT_SEC + 2.0

###############################################################################
## Subroutines
###############################################################################


# Define a context manager to suppress stdout and stderr.
class suppress_stdout_stderr(object):
    '''
    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).
    '''
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


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    '''
    return [atoi(c) for c in re.split('(\d+)', text)]


def help_text_epilog():
    text = textwrap.dedent('''\
       Tables and Field descriptions:
       ------------------------------

       COMPUTE HOSTS:  Legend: U = Used, A = Avail
        Host          - compute host name
        status        - host operational status
        model         - processor model
        topology      - processor cpu topology (sockets, cores, threads)
        servers       - number of servers
        node          - physical processor node (a.k.a., numa node)
        pcpus         - physical vcpus per numa node (avail to libvirt)
        U:dedicated   - used dedicated vcpus (a.k.a., pinned)
        U:shared      - used shared vcpus (a.k.a., float)
        memory        - host memory (MiB) available for libvirt
        U:memory      - used memory for servers (MiB)
        A:mem_4K      - available 4K host memory for servers (MiB)
        A:mem_2M      - available 2M host memory for servers (MiB)
        A:mem_1G      - available 1G host memory for servers (MiB)
        Aggregate     - list of host aggregate names

        Note:
        - rows similar to 'nova hypervisor-show <hypervisor>'
        - last row similar to 'nova hypervisor-stats'

       LOGICAL CPU TOPOLOGY (compute hosts):
        cpu_id     - logical cpu id
        socket_id  - socket id (a.k.a., processor node, numa node)
        core_id    - physical core id on a given socket_id
        thread_id  - hyperthread (SMT) index of a given core_id
        sibling_id - hyperthread sibling cpu_id(s) (excludes cpu_id)

       SERVERS (nova view):
        tenant        - server tenant name (a.k.a. project)
        ID            - server uuid
        instance_name - server libvirt name
        name          - server name
        host          - server host
        vm_state      - server vm state
        task_state    - server task state
        power_state   - server power state
        image         - server image name (or image volume booted from)
        flavor        - server flavor name
        vcpus         - server number of vcpus (scaling: min, cur, max)
        memory        - server memory (MiB)
        instance_topology - server numa topology
                            (dedicated vs shared, pgsize,
                             mapping of vpus, pcpus, shared_vcpu, sibings)
        in_libvirt    - indicates server also seen in libvirt

       SERVERS (libvirt view):
        uuid          - server uuid
        instance_name - server libvirt name
        host          - server host
        id            - server libvirt id
        state         - server libvirt state
        vcpus         - server number of vcpus
        memory        - server memory (MiB)
        nodelist      - server list of numa nodes
        cpulist       - server list of pcpu[i] for each vcpu i
        in_nova       - indicates server also seen in nova

       MIGRATIONS (in progress):  Legend: S=Source, D=Destination
        ID             - server uuid
        status         - migration status
        S:node         - source node
        D:node         - destination node
        S:compute      - source compute
        D:compute      - destination compute
        S:flavor[PKey] - source flavor primary key id
        D:flavor[PKey] - destination flavor primary key id
        created_at     - timestamp of migration

       FLAVORS (in use):
        id          - flavor_id
        name        - flavor name
        vcpus       - number of vcpus
        ram         - memory (MiB)
        disk        - disk stgorage (GB)
        ephemeral   - ephemeral storage (GB)
        swap        - swap size (MiB)
        rxtx_factor - RX/TX factor (default 1)
        is_public   - make flavor accessible to the public (default true)
        extra_specs - metadata containing key=value pairs

       IMAGES (in use):
        id          - image id
        name        - image name
        minDisk     - minimum size of disk to boot image (GB)
        minRam      - minimum size of ram to boot image (MB)
        size        - image data size (MB)
        status      - image status
        properties  - metadata containing key=value pairs

       SERVER GROUPS (in use):
        tenant      - server tenant name (a.k.a., project)
        id          - server group uuid
        name        - server group name
        policies    - server group policies
        metadata    - metadata containing key=value pairs
       ''')
    return text


class ChoiceOpt(cfg.Opt):
    r"""Option with List(String) type
    Option with ``type`` :class:`oslo_config.types.List`
    :param name: the option's name
    :param choices: Optional sequence of either valid values or tuples of valid
        values with descriptions.
    :param bounds: if True the value should be inside "[" and "]" pair
    :param \*\*kwargs: arbitrary keyword arguments passed to :class:`Opt`
    .. versionchanged:: 2.5
       Added *item_type* and *bounds* parameters.
    """

    def __init__(self, name, choices=None, bounds=None, **kwargs):
        type = types.List(item_type=types.String(choices=choices), bounds=bounds)
        super(ChoiceOpt, self).__init__(name, type=type, **kwargs)


def parse_arguments(debug, show):
    """
    Parse command line arguments.
    """

    # Initialize all debug flags to False
    define_debug_flags(debug)

    # Initialized show option lists
    (L_opts, L_brief, L_details, L_other) = define_options()

    # Select potentially multiple values from the following options
    O = set([])
    O.update(L_brief)
    O.update(L_details)
    O.update(L_other)
    S = sorted(O)
    S[0:0] = L_opts

    # Enable debug option, but its usage/help is hidden.
    D = debug.keys()
    D.sort()
    D.insert(0, 'all')

    # Parse arguments
    cli_opts = [
        ChoiceOpt('show',
                  default=['brief'],
                  choices=sorted(list(set(S))),
                  metavar='<' + ','.join(str(x) for x in S) + '>',
                  help='Show summary of selected tables'),
        ChoiceOpt('dbg',
                  default=[],
                  choices=sorted(list(set(D))),
                  metavar='<' + ','.join(str(x) for x in D) + '>',
                  help='Print debugging information for selected tables'),
    ]

    CONF.register_cli_opts(cli_opts)
    CONF.formatter_class = argparse.RawTextHelpFormatter
    CONF(sys.argv[1:],
         default_config_files=[NOVACONF],
         prog=os.path.basename(sys.argv[0]),
         description=(
            'Tool to summarize server resouce usage and vcpu placement'
            'related attributes for nova and libvirt.'),
         # NOTE: oslo_config implementation of _CachedArgumentParser does not
         # configure argparse formatter_class. The resulting epilog text is
         # automatically text-wrapped which is not desired. Manually adding
         # newlines does not work either. The epilog text is disabled for now.
         #epilog=help_text_epilog(),
        )

    # Configure logging to appropriate level
    level = logging.INFO
    if CONF.dbg:
        level = logging.DEBUG
    configure_logging(logger, level=level)

    if CONF.dbg:
        logger.debug('parse_args: debug=%r, show=%r' % (CONF.dbg, CONF.show))

    # Flatten debug options list
    L = list(set(CONF.dbg))

    # Update debug options based on parsed options
    {debug.update({e: True}) for e in L}

    # Enable all debug flags (except libvirt_xml) if 'all' is specified
    x = debug['libvirt_xml']
    if debug['all']:
        {debug.update({e: True}) for e in debug.keys()}
        debug['libvirt_xml'] = x

    # Flatten show options list
    L = list(set(CONF.show))
    if CONF.dbg:
        L = []

    # Update show options based on parsed options
    define_option_flags(show,
                        options=L,
                        L_opts=L_opts,
                        L_brief=L_brief,
                        L_details=L_details,
                        L_other=L_other)


def configure_logging(logger, level=logging.DEBUG):
    """ Configure logger streams and format. """
    logger.setLevel(level)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s %(process)s %(levelname)s %(module)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def _translate_keys(collection, convert):
    """ For a collection of elements, translate _info field names
    into human-readable names based on a list of conversion tuples.
    """
    for k, item in collection.iteritems():
        keys = item.__dict__.keys()
        for from_key, to_key in convert:
            if from_key in keys and to_key not in keys:
                try:
                    setattr(item, to_key, item._info[from_key])
                except AttributeError:
                    logger.error('_translate_keys: from_key:%r to_key:%r, '
                                 'item._info[from_key]:%r'
                                 % (from_key, to_key, item._info[from_key]))


def _translate_extended_states(collection):
    """ Return human readable power-state string. """
    power_states = [
        'NOSTATE',   # 0x00
        'Running',   # 0x01
        '',          # 0x02
        'Paused',    # 0x03
        'Shutdown',  # 0x04
        '',          # 0x05
        'Crashed',   # 0x06
        'Suspended'  # 0x07
    ]
    for k, item in collection.iteritems():
        try:
            setattr(item, 'power_state',
                    power_states[getattr(item, 'power_state')])
        except AttributeError:
            setattr(item, 'power_state', "N/A")
        try:
            getattr(item, 'task_state')
        except AttributeError:
            setattr(item, 'task_state', "N/A")


def _translate_virDomainState(state):
    """ Return human readable virtual domain state string. """
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


def _translate_virVcpuState(state):
    """ Return human readable virtual vpu state string. """
    states = {}
    states[0] = 'Offline'
    states[1] = 'Running'
    states[2] = 'Blocked'
    states[3] = 'Last'
    return states[state]


def _mask_to_cpulist(mask=0):
    """ Create cpulist from mask, list in socket-core-thread enumerated order.

    :param extended: extended info
    :param mask: cpuset mask
    :returns cpulist: list of cpus in socket-core-thread enumerated order
    """
    cpulist = []
    if mask is None or mask <= 0:
        return cpulist

    # Assume max number of cpus for now...
    max_cpus = 128
    for cpu in range(max_cpus):
        if ((1 << cpu) & mask):
            cpulist.append(cpu)
    return cpulist


def string_to_cpulist(cpus_str=''):
    ''' Convert a string representation to cpulist

    :param cpus_str: string containing list cpus, eg., 1,2,6-7
    :returns cpulist
    '''

    # Create list of excluded cpus by parsing excluded_cpulist_str,
    # example: 1,2,6-7
    cpulist = []
    re_digit = re.compile(r'^(\d+)$')
    re_range = re.compile(r'^(\d+)-(\d+)$')
    s = cpus_str.strip()
    for ele in s.split(','):
        match = re_digit.search(ele)
        if match:
            cpu = int(match.group(1))
            cpulist.append(cpu)

        match = re_range.search(ele)
        if match:
            cpu0 = int(match.group(1))
            cpu1 = int(match.group(2))
            if cpu1 > cpu0:
                cpulist.extend(list(range(cpu0, cpu1 + 1)))
    return cpulist


def list_to_range(L=[]):
    """ Convert a list into a string of comma separate ranges.
        E.g.,  [1,2,3,8,9,15] is converted to '1-3,8-9,15'
    """
    G = (list(x) for _, x in groupby(enumerate(L), lambda (i, x): i - x))
    return ",".join(
        "-".join(map(str, (g[0][1], g[-1][1])[:len(g)])) for g in G)

def range_to_list(csv_range=None):
    """ Convert a string of comma separate ranges into an expanded list of
        integers.  E.g., '1-3,8-9,15' is converted to [1,2,3,8,9,15]
    """
    if not csv_range:
        return []
    ranges = [(lambda L: range(L[0], L[-1] + 1))(map(int, r.split('-')))
               for r in csv_range.split(',')]
    return [y for x in ranges for y in x]


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError('timeout')


def libvirt_domain_info_worker((host)):
    pid = os.getpid()
    active_pids.update({pid: (host, time.time())})
    error = None
    try:
        (domain, topology) = do_libvirt_domain_info((host))
    except Exception as e:
        domain = {}
        topology = {}
        error = 'cannot connect to libvirt: %s; %s' % (host, e)
    del active_pids[pid]
    return (host, domain, topology, time.time(), error)


def do_libvirt_domain_info((host)):
    """
    Connect to libvirt for specified host, and retrieve per-domain information
    including cpu affinity per vcpu.
    """
    domains = {}
    topology = {}
    if not host:
        return (domains, topology)

    # Connect to remote libvirt hypervisor
    transport = 'tcp'
    duri = "qemu+%s://%s/system" % (transport, host)
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
    if conn is None:
        return (domains, topology)

    # Get host capabilities (contains host topology)
    caps_str = conn.getCapabilities()
    doc = ElementTree.fromstring(caps_str)
    caps = minidom.parseString(caps_str)
    caps_host = caps.getElementsByTagName('host')[0]
    caps_cells = caps_host.getElementsByTagName('cells')[0]
    total_cpus = caps_cells.getElementsByTagName('cpu').length

    # Enumerate logical cpu topology using socket_id, core_id, thread_id
    # indices.  This generates the following dictionary:
    # topology[socket_id][core_id][thread_id] = cpu_id
    Thread_cnt = {}
    topology = {}
    cells = doc.findall('./host/topology/cells/cell')
    for cell in cells:
        cell_id = int(cell.get('id'))
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

    # Get domains (i.e., one per VM)
    for dom in conn.listAllDomains(flags=0):
        # Get overall domain info
        d_name = dom.name()
        d_id = dom.ID()
        d_uuid = dom.UUIDString()
        d_ostype = dom.OSType()
        d_state, d_maxMem_KiB, d_memory_KiB, \
            d_nrVirtCpu, d_cpuTime = dom.info()
        try:
            with suppress_stdout_stderr():
                d_vcpus = dom.vcpus()
        except Exception as e:
            d_vcpus = tuple([d_nrVirtCpu*[],
                             d_nrVirtCpu*[tuple(total_cpus * [False])]])

        # Obtain cpulist of pcpus in the order of vcpus. This applies to either
        # pinned or floating vcpus,  Note that the cpuinfo pcpu value can be
        # stale if we scale down cpus since it reports cpu-last-run.
        # For this reason use cpumap = d_vcpus[1][vcpu], instead of cpuinfo
        # (i.e., vcpu, state, cpuTime, pcpu = d_vcpus[0][vcpu]).
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
        for key in sorted(cpulist_d.iterkeys()):
            cpulist_p.append(cpulist_d[key])

        # Determine if floating or pinned, display appropriate cpulist
        d_cpuset = cpuset_total
        if up_total > d_nrVirtCpu:
            d_cpulist = cpulist_f
        else:
            d_cpulist = cpulist_p

        # Determine list of numa nodes (the hard way)
        dom_xml = ElementTree.fromstring(dom.XMLDesc(0))
        nodeset = set([])
        for elem in dom_xml.findall('./numatune/memnode'):
            nodes = range_to_list(elem.get('nodeset'))
            nodeset.update(nodes)
        d_nodelist = list(sorted(nodeset))

        # Update dictionary with per-domain information
        domains[d_uuid] = {
            'name': d_name,
            'id': d_id,
            'uuid': d_uuid,
            'ostype': d_ostype,
            'state': _translate_virDomainState(d_state),
            'maxMem': int(d_maxMem_KiB / 1024.0),
            'memory': int(d_memory_KiB / 1024.0),
            'vcpus': d_nrVirtCpu,
            'cputime': d_cpuTime,
            'cpuset': d_cpuset,
            'nodelist': d_nodelist,
            'cpulist': d_cpulist,
        }

        # Dump XML string
        if debug['libvirt_xml']:
            dom_xml = ElementTree.fromstring(dom.XMLDesc(0))
            xml_str = ElementTree.tostring(dom_xml)
            logger.debug('DOM[%s] : XML =\n%s' % (d_name, xml_str))

    conn.close()
    return (domains, topology)


def print_debug_info(tenants=None, regions=None,
                     endpoints=None, services=None,
                     hypervisors=None, statistics=None,
                     servers=None, server_groups=None,
                     migrations=None, flavors=None, extra_specs=None,
                     images=None, volumes=None,
                     aggregates=None, domains=None,
                     topologies=None, topologies_idx=None, topologies_sib=None,
                     computes_cell=None,
                     debug=None, show=None):
    """
    Print debug information - pretty formatting of various data structures
    """
    pp = pprint.PrettyPrinter(indent=2)

    if True in debug.values():
        print
        logger.debug('OPTIONS:')
        logger.debug('debug=\n%s' % (pp.pformat(debug)))
        logger.debug('show=\n%s' % (pp.pformat(show)))

    if debug['creds']:
        print
        logger.debug('CREDENTIALS:')
        logger.debug('regions:\n%s' % (pp.pformat(regions)))
        logger.debug('tenants:\n%s' % (pp.pformat(tenants)))
        logger.debug('services:\n%s' % (pp.pformat(services)))
        logger.debug('endpoints:\n%s' % (pp.pformat(endpoints)))

    if debug['hypervisors']:
        print
        logger.debug('HYPERVISORS:')
        for H in hypervisors.values():
            logger.debug('hypervisor:\n%s' % (pp.pformat(vars(H))))

        print
        logger.debug('HYPERVISORS: numa cells')
        logger.debug('computes_cell:\n%s' % (pp.pformat(computes_cell)))

    if debug['statistics']:
        print
        logger.debug('STATISTICS:')
        logger.debug('statistic:\n%s' % (pp.pformat(vars(statistics))))

    if debug['images']:
        print
        logger.debug('IMAGES:')
        for I in images.values():
            logger.debug('image: id=%r\n%s' % (I.id, pp.pformat(vars(I))))

    if debug['volumes']:
        print
        logger.debug('VOLUMES:')
        for V in volumes.values():
            logger.debug('volume: id=%r\n%s' % (V['volume_id'], pp.pformat(V)))

    if debug['servers']:
        print
        logger.debug('SERVERS:')
        for S in servers.values():
            logger.debug('server: id=%r\n%s' % (S.id, pp.pformat(vars(S))))

    if debug['server_groups']:
        print
        logger.debug('SERVER GROUPS:')
        for S in server_groups.values():
            logger.debug(
                'server_group: id=%r\n%s' % (S.id, pp.pformat(vars(S))))

    if debug['migrations']:
        print
        logger.debug('MIGRATIONS:')
        for M in migrations.values():
            logger.debug('MIG: id=%r\n%s' % (M.id, pp.pformat(vars(M))))

    if debug['flavors']:
        print
        logger.debug('FLAVORS:')
        for F in flavors.values():
            logger.debug(
                'FLAVOR: id=%r\n%s\nextra_specs=%s'
                % (F.id, pp.pformat(vars(F)), pp.pformat(extra_specs[F.id])))

    if debug['aggregates']:
        print
        logger.debug('AGGREGATES:')
        for A in aggregates.values():
            logger.debug('aggregate: %s' % (pp.pformat(vars(A))))

    if debug['libvirt']:
        print
        logger.debug('LIBVIRT:')
        logger.debug('domain:\n%s' % (pp.pformat(domains)))

    if debug['topology']:
        print
        logger.debug('TOPOLOGY:')
        logger.debug('topologies:\n%s' % (pp.pformat(topologies)))
        logger.debug('topologies_idx:\n%s' % (pp.pformat(topologies_idx)))
        logger.debug('topologies_sib:\n%s' % (pp.pformat(topologies_sib)))

    if debug:
        print


def define_debug_flags(debug):
    """ Define dictionary of debug flags. """
    opts = ['all',
            'creds',
            'hypervisors',
            'statistics',
            'servers',
            'server_groups',
            'migrations',
            'flavors',
            'images',
            'volumes',
            'aggregates',
            'libvirt',
            'libvirt_xml',
            'topology',
            'mismatch',
            ]
    {debug.update({e: False}) for e in opts}


def define_options(L_opts=[], L_brief=[], L_details=[], L_other=[]):
    """ Define several groupings with lists of show options. """
    L_opts = ['brief',
              'all',
              ]
    L_brief = ['computes',
               'servers',
               'server_groups',
               'migrations',
               'flavors',
               'images',
               ]
    L_details = ['computes',
                 'servers',
                 'server_groups',
                 'libvirt',
                 'migrations',
                 'flavors',
                 'images',
                 'volumes',
                 ]
    L_other = ['aggregates', 'topology', 'topology-long']
    return (L_opts, L_brief, L_details, L_other)


def define_option_flags(show, options=[],
                        L_opts=[], L_brief=[], L_details=[], L_other=[]):
    """ Define dictionary of option flags. """

    # Set all options to False
    {show.update({e: False}) for e in L_opts + L_brief + L_details + L_other}

    # Enable specific options
    show.update({'show': options})
    if 'brief' in options:
        {show.update({e: True}) for e in L_brief}
    if 'all' in options:
        {show.update({e: True}) for e in L_brief + L_details}
    for e in options:
        if e in show.keys():
            show.update({e: True})


def print_all_tables(tenants=None,
                     hypervisors=None, statistics=None,
                     servers=None, server_groups=None,
                     migrations=migrations, flavors=None, extra_specs=None,
                     images=None, volumes=None,
                     aggregates=None, domains=None,
                     topologies=None, topologies_idx=None, topologies_sib=None,
                     computes_cell=None,
                     agg_h=None,
                     flavors_in_use=None,
                     images_in_use=None,
                     server_groups_in_use=None,
                     debug=None, show=None):
    """ Print all summary tables using PrettyTable.
    """
    # Print list of aggregates
    if show['aggregates']:
        print
        print("AGGREGATES:")
        pt = PrettyTable(
            ['Name',
             'Avail Zone',
             'Hosts',
             'Metadata',
            ], caching=False)
        pt.align = 'l'
        for name, A in sorted(aggregates.items()):
            pt.add_row(
                [A.name,
                 str(A.availability_zone),
                 ", ".join([str(x) for x in A.hosts]),
                 str(A.metadata)
                ])
        print(pt)

    # Print list of compute host hypervisors, showing per numa details
    if show['computes']:
        print
        print('COMPUTE HOSTS:  '
              'Legend: U = Used, A = Avail')
        pt = PrettyTable(
            ['Host',
             'status',
             'model',
             'topology',
             'servers',
             'node',
             'pcpus',
             'U:dedicated',
             'U:shared',
             'memory',
             'U:memory',
             'A:mem_4K',
             'A:mem_2M',
             'A:mem_1G',
             'Aggregate',
            ])
        pt.align = 'l'
        for C in ['servers', 'pcpus', 'U:dedicated', 'U:shared',
                  'memory', 'U:memory', 'A:mem_4K', 'A:mem_2M', 'A:mem_1G']:
            pt.align[C] = 'r'
        for host_name, H in sorted(hypervisors.iteritems(),
                                   key=lambda (k, v): (natural_keys(k))):
            A = agg_h[host_name].keys()

            try:
                topology_idx = topologies_idx[host_name]
                cpu_ids = sorted(topology_idx.keys())
            except Exception:
                topology_idx = {}
                cpu_ids = []
            if len(cpu_ids) > 0:
                # determine number of sockets, cores/socket, threads/core
                topology = topologies[host_name]
                cpu_id = 0
                socket_id = topology_idx[cpu_id]['s']
                core_id = topology_idx[cpu_id]['c']
                n_sockets = len(topology.keys())
                n_cores = len(topology[socket_id].keys())
                n_threads = len(topology[socket_id][core_id].keys())
            else:
                if 'topology' in H.cpu_info:
                    topology = H.cpu_info['topology']
                    n_sockets = topology['sockets']
                    n_cores = topology['cores']
                    n_threads = topology['threads']
                else:                    
                    n_sockets = 0
                    n_cores = 0
                    n_threads = 0
                if 'model' not in H.cpu_info:
                    H.cpu_info['model'] = None

            first = True
            for cell in computes_cell[host_name]:
                if first:
                    pt.add_row(
                        [host_name,
                         H.status,
                         H.cpu_info['model'],
                         "%ss,%sc,%st" % (n_sockets,
                                          n_cores,
                                          n_threads),
                         H.running_vms,
                         cell['id'],
                         cell['pcpus'],
                         cell['pinned_used'],
                         cell['shared_used'],
                         cell['memory'],
                         cell['memory_usage'],
                         cell['memory_avail_4K'],
                         cell['memory_avail_2M'],
                         cell['memory_avail_1G'],
                         textwrap.fill(", ".join([str(x) for x in A]),
                                       width=75),
                        ])
                else:
                    pt.add_row(
                        ['',  # host
                         '',  # H.status,
                         '',  # model
                         '',  # topology
                         '',  # H.running_vms,
                         cell['id'],
                         cell['pcpus'],
                         cell['pinned_used'],
                         cell['shared_used'],
                         cell['memory'],
                         cell['memory_usage'],
                         cell['memory_avail_4K'],
                         cell['memory_avail_2M'],
                         cell['memory_avail_1G'],
                         '',  # agg
                        ])

                first = False
            if len(computes_cell[host_name]) < 1:
                pt.add_row(
                    [host_name,
                     H.status,
                     H.cpu_info['model'],
                     "%ss,%sc,%st" % (n_sockets,
                                      n_cores,
                                      n_threads),
                     H.running_vms,
                     '-',  # cell.id
                     '-',  # pcpus
                     '-',  # U:dedicated
                     '-',  # U:shared
                     '-',  # memory
                     '-',  # memory_usage
                     '-',  # memory_avail_4K
                     '-',  # memory_avail_2M
                     '-',  # memory_avail_1G
                     ", ".join([str(x) for x in A]),
                    ])

        # Add row with statistics
        Y = statistics
        pt.add_row(
            ['count: %s' % (Y.count),
             '-',  # status
             '-',  # model
             '-',  # topology
             Y.running_vms,
             '-',  # node
             Y.vcpus,  # pcpus
             '-',  # U:dedicated
             '-',  # U:shared
             Y.memory_mb,  # memory
             Y.memory_mb_used,  # memory_usage
             '-',  # memory_avail_4K
             '-',  # memory_avail_2M
             '-',  # memory_avail_1G
             '-',  # agg
            ])
        print pt

    # Print list of compute hosts topology
    if show['topology']:
        print
        print('LOGICAL CPU TOPOLOGY (compute hosts):')
        for host_name, topology in sorted(topologies.iteritems(),
                                          key=lambda (k, v): (natural_keys(k))):
            H = hypervisors[host_name]
            try:
                topology_idx = topologies_idx[host_name]
                cpu_ids = sorted(topology_idx.keys())
                siblings = topologies_sib[host_name]
            except Exception:
                topology_idx = {}
                siblings = {}
                cpu_ids = []
            if len(cpu_ids) < 1:
                logger.info('%s libvirt info not available\n' % (host_name))
                continue

            # determine number of sockets, cores/socket, threads/core
            cpu_id = 0
            socket_id = topology_idx[cpu_id]['s']
            core_id = topology_idx[cpu_id]['c']
            n_sockets = len(topology.keys())
            n_cores = len(topology[socket_id].keys())
            n_threads = len(topology[socket_id][core_id].keys())

            print('%s:  Model:%s, Arch:%s, Vendor:%s, '
                  'Sockets=%d, Cores/Socket=%d, Threads/Core=%d, Logical=%d'
                  % (host_name,
                     H.cpu_info['model'],
                     H.cpu_info['arch'],
                     H.cpu_info['vendor'],
                     n_sockets, n_cores, n_threads, len(cpu_ids)))

            # cpu_id row
            L = ['cpu_id']
            {L.append(i) for i in cpu_ids}
            pt = PrettyTable(L)
            pt.align = 'r'

            # socket_id row
            L = ['socket_id']
            {L.append(topology_idx[i]['s']) for i in cpu_ids}
            pt.add_row(L)

            # core_id row
            L = ['core_id']
            {L.append(topology_idx[i]['c']) for i in cpu_ids}
            pt.add_row(L)

            # thread_id row
            L = ['thread_id']
            {L.append(topology_idx[i]['t']) for i in cpu_ids}
            pt.add_row(L)

            # sibling_id row
            L = ['sibling_id']
            {L.append(','.join(
                str(s) for s in siblings[i]) or '-') for i in cpu_ids}
            pt.add_row(L)
            print(pt)
            print

    # Print list of compute hosts topology
    if show['topology-long']:
        print
        print('LOGICAL CPU TOPOLOGY (compute hosts):')
        for host_name, topology in sorted(topologies.iteritems(),
                                          key=lambda (k, v): (natural_keys(k))):
            H = hypervisors[host_name]
            try:
                topology_idx = topologies_idx[host_name]
                cpu_ids = sorted(topology_idx.keys())
                siblings = topologies_sib[host_name]
            except Exception:
                topology_idx = {}
                siblings = {}
                cpu_ids = []
            if len(cpu_ids) < 1:
                logger.info('%s libvirt info not available\n' % (host_name))
                continue

            # determine number of sockets, cores/socket, threads/core
            cpu_id = 0
            socket_id = topology_idx[cpu_id]['s']
            core_id = topology_idx[cpu_id]['c']
            n_sockets = len(topology.keys())
            n_cores = len(topology[socket_id].keys())
            n_threads = len(topology[socket_id][core_id].keys())

            print('%s:  Model:%s, Arch:%s, Vendor:%s, '
                  'Sockets=%d, Cores/Socket=%d, Threads/Core=%d, Logical=%d'
                  % (host_name,
                     H.cpu_info['model'],
                     H.cpu_info['arch'],
                     H.cpu_info['vendor'],
                     n_sockets, n_cores, n_threads, len(cpu_ids)))
            pt = PrettyTable(
                ['cpu_id',
                 'socket_id',
                 'core_id',
                 'thread_id',
                 'sibling_id',
                 'affinity'
                ])
            pt.align = 'r'
            pt.align['affinity'] = 'l'
            for i in cpu_ids:
                pt.add_row(
                    [i,
                     topology_idx[i]['s'],
                     topology_idx[i]['c'],
                     topology_idx[i]['t'],
                     list_to_range(siblings[i]) or '-',
                     '0x%x' % (1 << i)
                    ])
            print(pt)
            print

    # Print list of servers
    if show['servers']:
        re_server_group = re.compile(r'^(\S+)\s+\((\S+)\)$')
        print
        print('SERVERS (nova view):')
        pt = PrettyTable(
            ['tenant',
             'ID',
             'instance_name',
             'name',
             'host',
             'state (vm, task, power)',
             'server_group',
             'image',
             'flavor',
             'vcpus',
             'memory',
             'instance_topology',
             'in_libvirt',
            ])
        pt.align = 'l'
        for C in ['vcpus', 'memory']:
            pt.align[C] = 'r'
        for C in ['in_libvirt']:
            pt.align[C] = 'c'
        for _, S in sorted(servers.iteritems(),
                           key=lambda (k, v): (natural_keys(v.host),
                                               v.server_group,
                                               v.instance_name)
                           if (v.host is not None) else 'None'
        ):
            if S.server_group is not None and S.server_group:
                match = re_server_group.search(S.server_group)
                if match:
                    server_group = match.group(1)
                    sgid = match.group(2)
                else:
                    server_group = '-'
                    sgid = None
            else:
                server_group = '-'
                sgid = None

            # Determine image name based on glance image id if it exists,
            # or deduce from attached volume metadata.
            try:
                image_id = S.image['id']
            except Exception:
                try:
                    image_id = volumes[S.id]['image_id']
                except Exception:
                    image_id = None
            try:
                image_name = images[image_id].name
            except Exception:
                image_name = '-'

            # Determine flavor name
            flavor_id = S.flavor['id']
            try:
                flavor_name = flavors[flavor_id].name
            except Exception:
                flavor_name = 'DELETED (%s)' % (flavor_id)
            try:
                flavor_vcpus = flavors[flavor_id].vcpus
                flavor_ram = flavors[flavor_id].ram
            except Exception:
                flavor_vcpus = '-'
                flavor_ram = '-'

            try:
                vcpus_scale = ','.join(str(x) for x in S.vcpus_scale)
            except Exception:
                vcpus_scale = flavor_vcpus

            in_libvirt = False
            for h, D in domains.iteritems():
                if S.id in D:
                    in_libvirt = True
                    break
            tenant = tenants[S.tenant_id].name

            pt.add_row(
                [tenant,
                 S.id,
                 S.instance_name,
                 S.name,
                 S.host,
                 '%7s, %s, %s' % (S.vm_state, S.task_state, S.power_state),
                 server_group,
                 image_name,
                 flavor_name,
                 vcpus_scale,
                 flavor_ram,
                 S.topology,
                 'yes' if in_libvirt else 'NO',
                ])
        print pt

    # Print each libvirt domain info
    if show['libvirt']:
        print
        print('SERVERS (libvirt view):  '
              'Legend: cpulist = [pcpu[i], ...]')
        pt = PrettyTable(
            ['uuid',
             'instance_name',
             'host',
             'id',
             'state',
             'vcpus',
             'memory',
             'nodelist',
             'cpulist',
             'in_nova',
            ])
        pt.align = 'l'
        for C in ['id', 'vcpus', 'memory', 'nodelist']:
            pt.align[C] = 'r'
        for C in ['in_nova']:
            pt.align[C] = 'c'
        for host, D in sorted(domains.iteritems(),
                              key=lambda (k, v): (natural_keys(k))):
            for _, S in sorted(D.iteritems(),
                               key=lambda (k, v): (v['name'])):
                in_nova = True if S['uuid'] in servers else False
                pt.add_row(
                    [S['uuid'],
                     S['name'],
                     host,
                     S['id'],
                     S['state'],
                     S['vcpus'],
                     S['memory'],
                     list_to_range(S['nodelist']) or '-',
                     list_to_range(S['cpulist']) or '-',
                     'yes' if in_nova else 'NO',
                    ])
        print pt

    # Print list of in-progress migrations
    if show['migrations']:
        print
        print("MIGRATIONS (in progress):  Legend: S=Source, D=Destination")
        pt = PrettyTable(
            ['ID',
             'status',
             'S:node',
             'D:node',
             'S:compute',
             'D:compute',
             'S:flavor[PKey]',
             'D:flavor[PKey]',
             'created_at',
            ])
        pt.align = 'l'
        for _, M in sorted(migrations.iteritems(),
                           key=lambda (k, v): (k)):
            pt.add_row(
                [M.instance_uuid,
                 M.status,
                 M.source_node,
                 M.dest_node,
                 M.source_compute,
                 M.dest_compute,
                 M.new_instance_type_id,
                 M.old_instance_type_id,
                 M.created_at,
                ])
        print pt

    # Print flavors for instances currently in use
    pp = pprint.PrettyPrinter(indent=1, width=40)
    if show['flavors']:
        print
        print("FLAVORS (in use):")
        pt = PrettyTable(
            ['id',
             'name',
             'vcpus',
             'ram',
             'disk',
             'ephemeral',
             'swap',
             'rxtx_factor',
             'is_public',
             'extra_specs',
            ])
        pt.align = 'l'
        for C in ['id', 'vcpus', 'ram', 'disk', 'ephemeral', 'swap',
                  'rxtx_factor']:
            pt.align[C] = 'r'
        for _, F in sorted(flavors.iteritems(),
                           key=lambda (k, v): (k)):
            if F.id in flavors_in_use:
                pt.add_row(
                    [F.id,
                     F.name,
                     F.vcpus,
                     F.ram,
                     F.disk,
                     F.ephemeral or '-',
                     F.swap or '-',
                     F.rxtx_factor,
                     F.is_public,
                     pp.pformat(extra_specs[F.id]),
                    ])
        print(pt)

    # Print images for instances currently in use
    pp = pprint.PrettyPrinter(indent=1, width=40)
    if show['images']:
        print
        print("IMAGES (in use):")
        pt = PrettyTable(
            ['id',
             'name',
             'min_disk',
             'min_ram',
             'size(MB)',
             'status',
             'properties',
            ])
        pt.align = 'l'
        for C in ['id', 'min_disk', 'min_ram', 'status']:
            pt.align[C] = 'r'
        for _, I in sorted(images.iteritems(),
                           key=lambda (k, v): (k)):
            if I.id in images_in_use:
                pt.add_row(
                    [I.id,
                     I.name,
                     I.min_disk,
                     I.min_ram,
                     '%.2f' % (I.size/1024.0/1024.0),
                     I.status,
                     I.properties,
                    ])
        print(pt)

    # Print server groups for instances currently in use (exclude members data)
    if show['server_groups']:
        print
        print("SERVER GROUPS (in use):")
        pt = PrettyTable(
            ['Tenant',
             'Id',
             'Name',
             'Policies',
             'Metadata',
            ])
        pt.align = 'l'
        for _, S in sorted(server_groups.iteritems(),
                           key=lambda (k, v): (k)):
            if S.id in server_groups_in_use:
                tenant = tenants[S.project_id].name
                pt.add_row(
                    [tenant,
                     S.id,
                     S.name,
                     str(S.policies),
                     str(S.metadata),
                    ])
        print(pt)


def _get_host_id(tenant_id=None, host_name=None):
    """ Routine defined in nova/api/openstack/compute/views/servers.py .
    """
    sha_hash = hashlib.sha224(tenant_id + host_name)
    return sha_hash.hexdigest()


def start_process():
    logger.debug('Starting: %s, %d'
        % (multiprocessing.current_process().name, os.getpid()))


def get_info_and_display(show=None):
    """ Get information from various sources (keystone, nova, libvirt).

        Display the following information in table format.
        - nova view of hypervisors and servers
        - libvirt view of servers
        - nova view of in-progress migrations
        - nova view of flavors in-use
        - nova view of volumes and images in-use
        - nova view of server-groups in-use
    """
    t0 = time.time()

    # Keep track of mismatches found when validating data sources
    warnings = []

    # Define list of server field conversions
    convert = [
        ('OS-EXT-SRV-ATTR:host', 'host'),
        ('OS-EXT-SRV-ATTR:hypervisor_hostname', 'nodename'),
        ('OS-EXT-STS:task_state', 'task_state'),
        ('OS-EXT-STS:vm_state', 'vm_state'),
        ('OS-EXT-SRV-ATTR:instance_name', 'instance_name'),
        ('OS-EXT-STS:power_state', 'power_state'),
        ('OS-SRV-USG:launched_at', 'launched_at'),
        ('OS-FLV-DISABLED:disabled', 'disabled'),
        ('OS-FLV-EXT-DATA:ephemeral', '_ephemeral'),
        ('os-flavor-access:is_public', '_is_public'),
        ('os-extended-volumes:volumes_attached', 'volumes_attached'),
        ('wrs-res:vcpus', 'vcpus_scale'),
        ('OS-EXT-IMG-SIZE:size', 'size'),
        ('wrs-res:topology', 'topology'),
        ('wrs-sg:server_group', 'server_group'),
        ('wrs-sg:project_id', 'project_id'),
    ]

    # Define list of migration status that imply completed migration
    migration_completed_list = [
        # live migration
        'live-post', 'live-rollback',
        # cold migration
        'confirmed', 'reverted', 'finished',
        # drop_resize_claim
        'drop-claim',
        # error
        'error'
    ]


    # Get keystone credentials from nova.conf
    auth = keystone.load_auth_from_conf_options(CONF, AUTHTOKEN_GROUP)
    keystone_session = session.Session(auth=auth)

    # Define primary region_name (should be the same as keystone)
    regions = {}
    primary = 'primary'
    regions[primary] = CONF.keystone_authtoken.region_name

    # Query sysinv database for region_name data. This is done directly from
    # sysinv database, as that information is not exported via sysinv APIs.
    # We have sufficient postgres credentials since we are on the same
    # localhost as the DB and may use a local socket. We also execute as root.
    engine = create_engine(
        '{driver}://{user}:{passwd}@{host}:{port}/{dbname}'.
        format(
            driver='postgresql',
            user='admin',
            passwd='admin',
            host='controller',
            dbname='sysinv',
            port='5432',
        ), client_encoding='utf8')
    conn = engine.connect()

    # Get sysinv i_system
    metadata = MetaData()
    metadata.reflect(engine, only=['i_system'])
    Base = automap_base(metadata=metadata)
    Base.prepare(engine)
    S = Base.classes.i_system
    q = select([S.name,
                S.region_name,
                S.deleted_at]
              ).where(S.deleted_at == None)
    result = conn.execute(q)
    for row in result:
        field = 'region_name'
        if row[field] is None:
            continue
        regions[primary] = str(row[field])

    # Get sysinv services
    metadata = MetaData()
    metadata.reflect(engine, only=['services'])
    Base = automap_base(metadata=metadata)
    Base.prepare(engine)
    S = Base.classes.services
    q = select([S.name,
                S.region_name,
                S.deleted_at]
              ).where(S.deleted_at == None)
    result = conn.execute(q)
    for row in result:
        name = str(row['name'])
        field = 'region_name'
        if row[field] is None:
            region = regions[primary]
        else:
            region = str(row[field])
        regions[name] = region

    # Connect keystone client
    region_keystone = CONF.keystone_authtoken.region_name
    try:
        kc = keystone_client.Client(session=keystone_session,
                                    endpoint_type='internalURL',
                                    region_name=region_keystone)
    except Exception as e:
        logger.error('cannot connect keystone client, %s', e)
        sys.exit(1)

    # Connect nova client as admin
    region_nova = regions.get('nova', CONF.keystone_authtoken.region_name)
    try:
        nc_admin = nova_client.Client(NOVACLIENT_VERSION,
                                      session=keystone_session,
                                      endpoint_type='internalURL',
                                      region_name=region_nova)
    except Exception as e:
        logger.error('cannot connect nova client, %s', e)
        sys.exit(1)

    # Get list of services, then transform into dictionary with 'name' as key
    try:
        services_ = kc.services.list()
    except Exception as e:
        logger.error('cannot list services', exc_info=1)
        sys.exit(1)
    services = dict((e.name, e) for e in services_)
    del services_

    # Get list of endpoints, then transform into dictionary with 'id' as key
    try:
        endpoints_ = kc.endpoints.list()
    except Exception as e:
        logger.error('cannot list endpoints', exc_info=1)
        sys.exit(1)
    endpoints = dict((e.id, e) for e in endpoints_)
    del endpoints_

    # Get list of tenants, then transform into dictionary with 'id' as key
    try:
        tenants_ = kc.projects.list()
    except Exception as e:
        logger.error('cannot list tenants', exc_info=1)
        sys.exit(1)
    tenants = dict((e.id, e) for e in tenants_)
    del tenants_

    # Connect cinder client as admin to access block storage volumes
    region_cinder = regions.get('cinder', CONF.keystone_authtoken.region_name)
    try:
        cv_admin = cinder_client.Client(CINDERCLIENT_VERSION,
                                        session=keystone_session,
                                        endpoint_type='internalURL',
                                        region_name=region_cinder)
    except Exception as e:
        logger.error('cannot connect cinder client, %s', e)
        sys.exit(1)

    # Connect glanceclient as admin to access images
    region_glance = regions.get('glance', CONF.keystone_authtoken.region_name)
    try:
        gc_admin = glance_client.Client(GLANCECLIENT_VERSION,
                                        session=keystone_session,
                                        interface='internalURL',
                                        region_name=region_glance)
    except Exception as e:
        logger.error('cannot connect glance client, %s', e)
        sys.exit(1)

    # Get list of images
    try:
        images_ = gc_admin.images.list(detailed=True)
    except Exception as e:
        if True in debug.values():
            logger.error('cannot list images', exc_info=1)
        else:
            logger.error('cannot list images, %s' % (e))
        images_ = []
    try:
        images = dict((e.id, e) for e in images_)
    except Exception as e:
        if True in debug.values():
            logger.error('cannot list images', exc_info=1)
        else:
            logger.error('cannot list images, %s' % (e))
        images = {}

    # translate fields into human-readable names
    _translate_keys(images, convert)

    for I_id, I in images.iteritems():
        meta = copy.deepcopy(I.properties)
        I.properties = {}
        for k, v in meta.items():
            I.properties[str(k)] = str(v)

    # Get list of servers for all tenants
    try:
        servers_ = nc_admin.servers.list(detailed=True,
                                         search_opts={'all_tenants': True})
    except Exception as e:
        logger.error('cannot list servers', exc_info=1)
        sys.exit(1)

    servers = dict((e.id, e) for e in servers_)
    del servers_
    # translate fields into human-readable names
    _translate_keys(servers, convert)
    _translate_extended_states(servers)
    for S in servers.values():
        if S.host != S.nodename:
            warnings.append(
                'Server ID=%s, instance_name=%s, name=%s, host=%s '
                'does not match nodename=%s.'
                % (S.id, S.instance_name, S.name, S.host, S.nodename))

    # Get list of volumes attached to servers for all tenants
    if show['volumes']:
        try:
            volumes_ = cv_admin.volumes.list(detailed=True,
                                             search_opts={'all_tenants': True})
        except Exception as e:
            if True in debug.values():
                logger.error('cannot list volumes', exc_info=1)
            else:
                logger.error('cannot list volumes, %s' % (e))
            volumes_ = []
    else:
        volumes_ = []
    volumes = {}
    # keep all fields for debug even though we do not display details.
    for V in volumes_:
        # image metadata (not always available)
        try:
            image_id = V.volume_image_metadata['image_id']
            image_name = V.volume_image_metadata['image_name']
        except Exception:
            image_id = None
            image_name = None
        for A in V.attachments:
            server_id = A['server_id']
            volume_id = A['volume_id']
            volumes[server_id] = {'volume_id': volume_id,
                                  'image_id': image_id,
                                  'image_name': image_name,
                                  'vars': vars(V),
                                 }
    del volumes_

    # Get list of migrations, sort-by id which puts them in time order.
    # Transform into dictionary with 'instance_uuid' as key. Keep only the
    # most current, and only in-progress migrations.
    try:
        migrations_ = nc_admin.migrations.list()
    except Exception as e:
        logger.error('cannot list migrations', exc_info=1)
        migrations_ = {}
    migrations = {}
    if migrations_:
        migrations_.sort(key=lambda x: (x.id))
    for M in migrations_:
        if M.instance_uuid in servers:
            migrations.update({M.instance_uuid: M})
    for _, M in migrations.items():
        S = servers[M.instance_uuid]
        if S.task_state is None or M.status in migration_completed_list:
            del migrations[M.instance_uuid]
    del migrations_

    # Get list of flavors, then transform into dictionary with 'id' as key
    try:
        flavors_ = nc_admin.flavors.list(detailed=True)
    except Exception as e:
        logger.error('cannot list flavors', exc_info=1)
        sys.exit(1)
    flavors = dict((e.id, e) for e in flavors_)
    del flavors_

    # translate fields into human-readable names
    _translate_keys(flavors, convert)

    # Get extra_specs
    extra_specs = {}
    for f_id, F in flavors.iteritems():
        try:
            specs = F.get_keys()
        except Exception as e:
            specs = {}
            logger.error('cannot get extra_specs for flavor:%s, error=%s'
                         % (f_id, e))
        extra_specs[f_id] = {}
        for k, v in specs.items():
            extra_specs[f_id][str(k)] = str(v)

    # Get list of server groups, then transform into dictionary with 'id'
    # as key
    try:
        server_groups_ = nc_admin.server_groups.list()
    except Exception as e:
        logger.error('cannot list server_groups', exc_info=1)
        sys.exit(1)
    server_groups = dict((e.id, e) for e in server_groups_)
    del server_groups_

    # translate fields into human-readable names
    _translate_keys(server_groups, convert)

    # Generate server_groups_in_use, flavors in-use, images in-use
    re_server_group = re.compile(r'^(\S+)\s+\((\S+)\)$')
    server_groups_in_use = {}
    flavors_in_use = {}
    images_in_use = {}
    for S in servers.values():
        if S.server_group is not None and S.server_group:
            match = re_server_group.search(S.server_group)
            if match:
                server_group = match.group(1)
                server_group_id = match.group(2)
                server_groups_in_use[server_group_id] = True

        # Save flavors in use
        flavor_id = S.flavor['id']
        flavors_in_use[flavor_id] = True

        # Save images in use. Look for glance image id. If glance image not
        # available, then check for attached volume and store image name from
        # volume metadata.
        try:
            image_id = S.image['id']
        except Exception:
            try:
                image_id = volumes[S.id]['image_id']
                images_in_use[image_id] = True
            except Exception:
                image_id = None
        if image_id is not None:
            images_in_use[image_id] = True

    # Get list of hypervisors, then transform into dictionary with
    # 'hypervisor_hostname' as key
    try:
        hypervisors_ = nc_admin.hypervisors.list(detailed=True)
    except Exception as e:
        logger.error('cannot list hypervisors', exc_info=1)
        sys.exit(1)
    hypervisors = dict((e.hypervisor_hostname, e) for e in hypervisors_)
    del hypervisors_
    for H in hypervisors.values():
        H.cpu_info = jsonutils.loads(H.cpu_info) if H.cpu_info else {}
        del H._info, H._loaded, H.manager

    # Get hypervisor statisics (over all computes)
    try:
        statistics = nc_admin.hypervisors.statistics()
    except Exception as e:
        logger.error('cannot get overall hypervisors statistics', exc_info=1)
        sys.exit(1)

    # Get list of aggregates, then transform into dictionary with 'id' as key
    try:
        aggregates_ = nc_admin.aggregates.list()
    except Exception as e:
        logger.error('cannot list aggregates', exc_info=1)
        sys.exit(1)
    aggregates = dict((e.id, e) for e in aggregates_)
    del aggregates_

    # Build up aggregate list per compute host
    agg_h = {}
    for H in hypervisors.keys():
        agg_h[H] = {}
    for A in aggregates.values():
        for H in A.hosts:
            agg_h[H] = {}
    for A in aggregates.values():
        for H in A.hosts:
            agg_h[H][str(A.name)] = A.metadata

    # Calculate number of workers we can handle
    process = psutil.Process(os.getpid())
    avail_MiB = psutil.virtual_memory().available / float(Mi)
    try:
        process_MiB = process.get_memory_info().rss / float(Mi)
    except Exception as e1:
        try:
            process_MiB = process.memory_info().rss / float(Mi)
        except Exception as e2:
            logger.error('WORKERS: psutil.memory_info(), error=%s' % (e2))
            process_MiB = 50.0
    pool_size = \
        max(1,
            min(len(hypervisors),
                max(1,
                    min(multiprocessing.cpu_count(),
                        int(0.6 * (avail_MiB - 100.0) / process_MiB)
                    )
                )
            )
        )
    logger.debug('WORKERS: avail=%.2f MiB, process=%.2f MiB, pool_size=%d'
        % (avail_MiB, process_MiB, pool_size))

    # Create pool of workers that connect to libvirt hypervisor.
    try:
        pool = multiprocessing.Pool(processes=pool_size,
                                    initializer=start_process,
                                    maxtasksperchild=2)
    except Exception as e:
        logger.error('Cannot create worker pool, %s' % (e))
        sys.exit(1)

    hosts = []
    for h in hypervisors.keys():
        hosts.append(h)

    # Launch tasks
    results = [pool.apply_async(libvirt_domain_info_worker,
                                args=(x,)) for x in hosts]
    pool.close()

    # Wait for active workers to complete
    time.sleep(0.15)
    while len(active_pids) > 0:
        # Reap aged workers that exceed hang timeout
        now = time.time()
        reap = []
        for pid in active_pids.keys():
            if pid == 0:
                continue
            try:
                host, age = active_pids[pid]
            except:
                continue
            dt = now - age
            if dt > LIBVIRT_REAP_SEC:
                reap.append(pid)
                logger.error('REAP: pid=%d, host=%s, age=%.2f s'
                             % (pid, host, dt))
        for pid in reap:
            os.kill(pid, signal.SIGKILL)
            del active_pids[pid]
        time.sleep(0.25)

    # Collect outputs
    # Since we have already waited, set timeout small.
    outputs = []
    for p in results:
        try:
            outputs.append(p.get(timeout=0.005))
        except:
            pass

    # Cleanup workers
    pool.terminate()
    pool.join()

    # Summarize per-domain and cpu topology per host.
    domains = {}
    topologies = {}
    topologies_idx = {}
    topologies_sib = {}
    topologies_lib = {}
    for (h, domain_lib, topology_lib, tm1, error) in outputs:
        if error is None:
            domains[h] = domain_lib
            topologies_lib[h] = topology_lib
        else:
            domains[h] = {}
            topologies_lib[h] = {}
            logger.error('%s' % error)
        topology = copy.deepcopy(topologies_lib[h])
        topologies[h] = copy.deepcopy(topology)

        # Define topology indices for each logical cpu
        topology_idx = {}
        for socket_id in topology:
            for core_id in topology[socket_id]:
                for thread_id in topology[socket_id][core_id]:
                    cpu_id = topology[socket_id][core_id][thread_id]
                    topology_idx[cpu_id] = {'s': socket_id,
                                            'c': core_id,
                                            't': thread_id}
        topologies_idx[h] = copy.deepcopy(topology_idx)

        # Define siblings for each logical cpu
        siblings = {}
        for socket_id in topology:
            for core_id in topology[socket_id]:
                for thread_id in topology[socket_id][core_id]:
                    cpu_id = topology[socket_id][core_id][thread_id]
                    siblings[cpu_id] = []
                    for sibling_id in topology[socket_id][core_id]:
                        if thread_id != sibling_id:
                            sibling_cpu_id = topology[socket_id][core_id][sibling_id]
                            siblings[cpu_id].append(sibling_cpu_id)
        topologies_sib[h] = copy.deepcopy(siblings)
    del outputs

    # Query nova database for compute_nodes table, which contains per NUMA cell
    # data (i.e., numa_topology). This is done directly from nova database,
    # as that information is not exported via nova APIs.
    # We have sufficient postgres credentials since we are on the same
    # localhost as the DB and may use a local socket. We also execute as root.
    computes_cell = {}
    engine = create_engine(
        '{driver}://{user}:{passwd}@{host}:{port}/{dbname}'.
        format(
            driver='postgresql',
            user='admin',
            passwd='admin',
            host='controller',
            dbname='nova',
            port='5432',
        ), client_encoding='utf8')
    conn = engine.connect()
    metadata = MetaData()
    metadata.reflect(engine, only=['compute_nodes'])
    Base = automap_base(metadata=metadata)
    Base.prepare(engine)
    CN = Base.classes.compute_nodes
    q = select([CN.hypervisor_hostname,
                CN.numa_topology,
                CN.deleted]
              ).where(CN.deleted == 0)
    result = conn.execute(q)
    for row in result:
        host = row['hypervisor_hostname']
        computes_cell[host] = []

        # We need libvirt topology information to make sense of cpusets.
        have_topology = True
        try:
            if len(topologies_idx[host].keys()) < 1:
                have_topology = False
        except:
            have_topology = False

        field = 'numa_topology'
        if field not in row or row[field] is None:
            continue
        try:
            T = jsonutils.loads(row[field])
        except Exception as e:
            T = {}
            logger.warning('cannot json.loads(%s), error=%s' % (field, e))
            continue
        try:
            cells = T['nova_object.data']['cells']
            for C in cells:
                cell = C['nova_object.data']
                cell_id = cell['id']
                cpu_usage = cell['cpu_usage']
                cpuset = cell['cpuset']
                pinned_cpus = cell['pinned_cpus']
                shared_pcpu = cell['shared_pcpu']
                siblings = cell['siblings']
                memory = cell['memory']
                memory_usage = cell['memory_usage']
                MP = cell['mempages']
                mempages = []
                for M in MP:
                    MS = M['nova_object.data']
                    mempages.append(MS)

                pcpuset = []
                if have_topology:
                    for cpu in cpuset:
                        if topologies_idx[host][cpu]['s'] == cell_id:
                            pcpuset.append(cpu)

                # Store data for compute node numa cell
                Cell = {}
                Cell['id'] = cell_id
                Cell['memory'] = memory
                Cell['memory_usage'] = memory_usage
                Cell['mempages'] = mempages
                Cell['pinned_cpus'] = pinned_cpus
                Cell['pcpuset'] = pcpuset
                if have_topology:
                    Cell['pcpus'] = len(pcpuset)
                else:
                    Cell['pcpus'] = '-'
                Cell['shared_pcpu'] = shared_pcpu
                Cell['siblings'] = siblings
                Cell['pinned_used'] = len(pinned_cpus)
                if have_topology:
                    Cell['pinned_avail'] = len(pcpuset) - len(pinned_cpus)
                else:
                    Cell['pinned_avail'] = '-'
                Cell['shared_used'] = cpu_usage - len(pinned_cpus)
                for suf in ['4K', '2M', '1G']:
                    Cell['memory_total_' + suf] = 0
                    Cell['memory_used_' + suf] = 0
                    Cell['memory_avail_' + suf] = 0
                for pages in mempages:
                    suf = ''
                    if pages['size_kb'] == 4:
                        suf = '4K'
                    if pages['size_kb'] == 2048:
                        suf = '2M'
                    if pages['size_kb'] == 1048576:
                        suf = '1G'
                    Cell['memory_total_' + suf] = pages['size_kb'] * pages['total'] / Ki
                    Cell['memory_used_' + suf] = pages['size_kb'] * pages['used'] / Ki
                    Cell['memory_avail_' + suf] = pages['size_kb'] * (pages['total'] - pages['used']) / Ki

                computes_cell[host].append(Cell)

        except Exception as e:
            logger.warning('cannot print numa_topology.cells, error=%s' % (e))

    conn.close()

    # Detect mismatch where server is in nova but not in libvirt
    server_mismatch = False
    for S in servers.values():
        in_libvirt = False
        for h, D in domains.iteritems():
            if S.id in D and S.host == h:
                in_libvirt = True
                break
        if not in_libvirt:
            server_mismatch = True
            warnings.append('Server ID=%s, instance_name=%s, name=%s, '
                            'host=%s is in nova but not libvirt.'
                            % (S.id, S.instance_name, S.name, S.host))

    # Detect mismatch where server is in libvirt but not in nova
    for host, D in domains.iteritems():
        for k, S in D.iteritems():
            in_nova = False
            uuid = S['uuid']
            if uuid in servers and servers[uuid].host == host:
                in_nova = True
            if not in_nova:
                server_mismatch = True
                warnings.append('Server ID=%s, instance_name=%s, host=%s '
                                'is in libvirt but not nova.'
                                % (S['uuid'], S['name'], host))

    # Print out more details if we detect a mismatch, but only if we meant
    # to display servers.
    if server_mismatch and (show['servers'] or show['libvirt']):
        show['servers'] = True
        show['libvirt'] = True

    # Print debug information
    if True in debug.values():
        print_debug_info(tenants=tenants, regions=regions,
                         endpoints=endpoints, services=services,
                         hypervisors=hypervisors, statistics=statistics,
                         servers=servers, server_groups=server_groups,
                         migrations=migrations, flavors=flavors,
                         extra_specs=extra_specs,
                         images=images, volumes=volumes,
                         aggregates=aggregates, domains=domains,
                         topologies=topologies,
                         topologies_idx=topologies_idx,
                         topologies_sib=topologies_sib,
                         computes_cell=computes_cell,
                         debug=debug, show=show)

    # Print all summary tables
    print_all_tables(tenants=tenants,
                     hypervisors=hypervisors, statistics=statistics,
                     servers=servers, server_groups=server_groups,
                     migrations=migrations, flavors=flavors,
                     extra_specs=extra_specs,
                     images=images, volumes=volumes,
                     aggregates=aggregates, domains=domains,
                     topologies=topologies,
                     topologies_idx=topologies_idx,
                     topologies_sib=topologies_sib,
                     computes_cell=computes_cell,
                     agg_h=agg_h,
                     flavors_in_use=flavors_in_use,
                     images_in_use=images_in_use,
                     server_groups_in_use=server_groups_in_use,
                     debug=debug, show=show)

    # Print out warnings if we detect mismatches between nova and libvirt
    if warnings:
        print
        print("WARNINGS (mismatch):")
        pt = PrettyTable(['Message'])
        pt.align = 'l'
        for W in warnings:
            pt.add_row([W])
        print(pt)

    if True in debug.values():
        logger.debug('done.')

    # Cleanup
    del nc_admin, kc


def main():
    try:
        # Enforce 'root' access since we need to read nova.conf .
        if os.geteuid() != 0:
            print('Require sudo/root.')
            os.execvp('sudo', ['sudo'] + sys.argv)

        # Process command line options and arguments, configure logging,
        # configure debug and show options
        parse_arguments(debug, show)

        # Print selected options, and timestamp
        prog = os.path.basename(sys.argv[0])
        ts = datetime.datetime.now()
        print("%s: %s  options: show:%s" % (prog, ts.isoformat(), show['show']))
        if show['volumes']:
            logger.info('volumes selected: displaying will take some time')

        if debug['creds']:
            CONF.log_opt_values(logger, logging.INFO)

        # Get all info and display in table format
        get_info_and_display(show)
        sys.exit(0)

    except KeyboardInterrupt as e:
        logger.info('caught: %r, shutting down', e)
        sys.exit(0)

    except IOError as e:
        sys.exit(0)

    except Exception as e:
        logger.error('exception: %r', e, exc_info=1)
        sys.exit(-4)
