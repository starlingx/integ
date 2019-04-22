#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""

Usage: storage-topology  [options]
    options:
     -d,  --diskview  view  disk data of all server nodes.
     -v,  --vgview    view  VG data  in all nodes.
     -a,  --all       view both disk and vg view. ( selected by default if any
                       of the view options is NOT selected)
     -e,  --extended  include additional parameters like uuids in selected
                      view(s)
     -h,  --help   display this usage

Tool to show a consolidated view of system physical disks and logical volume
groups data.
"""

import os
import sys
import argparse
import datetime
import logging
import textwrap
import keyring
import subprocess
import math
from prettytable import PrettyTable
from cgtsclient.common import utils
from cgtsclient import client as cgts_client
from cgtsclient import exc

"""----------------------------------------------------------------------------
Global definitions
----------------------------------------------------------------------------"""

# logger
logger = logging.getLogger(__name__)

#  show options
show = {}


def configure_debuggubg(debug):
    if debug:
        logging.basicConfig(
            format="%(levelname)s (%(module)s:%(lineno)d) %(message)s",
            level=logging.DEBUG)
    else:
        logging.basicConfig(
            format="%(levelname)s %(message)s",
            level=logging.WARNING)


def parse_arguments(show):
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
            Tool to summarize server storage resouce usage.
            '''),
        epilog=textwrap.dedent('''\
            Tables and Field descriptions:
            ------------------------------
            SERVER Physical DISK view:
             Host          - server host name
             Device Node   - device node name
             Device Type   - device node type ( extended view only)
             UUID          - device node uuid ( extended view only)
             Size in GB    - disk size in giga bytes
             PV Name       - name of physical volume
             PV State      - the physical volume state
             PV UUID       - the physical volume uuid
             VG (name:state:uuid)
                    name   - VG name
                    state  - VG state
                    uuid   - VG uuid (extended view only)


            SERVER VOLUME GROUP view:
             Host          - server host name
             Name          - volume group name
             UUID          - volume group  uuid
             State         - VG state
             Size          - VG size in GB
             Current LVs   - current Number of logical volumes (lv)
             Current PVs   - current Number of physical volumes (pv)
             PV List (name:state:uuid) - Comma separated list of PVs
                    name   - physical volume name
                    state  - physical volume state
                    uuid   - physical volume uuid (extended view only)
             Parameters    - list of VG parameters

            '''),
    )

    # Global arguments

    parser.add_argument('-d', '--diskview',
                        default=False, action='store_true',
                        help="view all physical disks  across all nodes"
                             " including mapped physical volumes and"
                             "logical volume groups")

    parser.add_argument('-v', '--vgview',
                        default=False, action='store_true',
                        help="view information pertaining to VGs in all nodes")

    parser.add_argument('-a', '--all',
                        default=False, action='store_true',
                        help="view both disk and vg views")

    parser.add_argument('--debug',
                        default=bool(utils.env('SYSTEMCLIENT_DEBUG')),
                        action='store_true',
                        help=argparse.SUPPRESS)

    parser.add_argument('-e', '--extended',
                        default=False, action="store_true",
                        help="Print  additional disk or vg information")

    # Parse arguments
    args = parser.parse_args()

    show['diskview'] = args.diskview
    show['vgview'] = args.vgview
    show['all'] = args.all
    show['extended'] = args.extended
    show['debug'] = args.debug

    # Configure logging to appropriate level

    configure_debuggubg(show['debug'])


def get_system_creds():
    """Return keystone credentials by sourcing /etc/platform/openrc"""
    d = {}

    proc = subprocess.Popen(['bash', '-c',
                             'source /etc/platform/openrc && env'],
                            stdout=subprocess.PIPE)

    for line in proc.stdout:
        key, _, value = line.partition("=")
        if key == 'OS_USERNAME':
            d['os_username'] = value.strip()
        elif key == 'OS_PASSWORD':
            d['os_password'] = value.strip()
        elif key == 'OS_TENANT_NAME':
            d['os_tenant_name'] = value.strip()
        elif key == 'OS_AUTH_URL':
            d['os_auth_url'] = value.strip()
        elif key == 'OS_REGION_NAME':
            d['os_region_name'] = value.strip()

    proc.communicate()
    return d


def convert_to_readable_size(size, orig_unit='B'):
    """Converts size to human readable unit"""
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

    # convert original size to bytes
    try:
        i = units.index(orig_unit)
    except:
        raise RuntimeError('Invalid size unit passed: %s' % (orig_unit))
    size = size * pow(1024, i)

    unitIndex = int(math.floor(math.log(size, 1024)))
    # set size unit to PB max if size is greater than 1024 PB
    if unitIndex > 5:
        unitIndex = 5
    sizer = math.pow(1024, unitIndex)
    newsize = round(size / sizer, 2)
    return "%s %s" % (newsize, units[unitIndex])


def print_disk_view(rows=None, extended=False):
    """Print all summary Disk views using PrettyTable"""

    disk_lables_extended = \
        ['Host', 'Device Node', 'Device Type', 'UUID', 'Size',
         'PV Name', 'PV State', 'PV UUID', 'VG (name:state:uuid)', ]
    disk_lables_brief = \
        ['Host', 'Device Node', 'Size', 'PV Name', 'PV State',
         'VG (name:state)']

    if len(rows) > 0:
        print()
        print("DISKs: (Physical disk view)")

        pt = PrettyTable(disk_lables_extended) if extended else  \
            PrettyTable(disk_lables_brief)
        pt.align = 'l'
        pt.align['Size'] = 'r'
        for r in rows:
            if len(r) == len(pt.field_names):
                pt.add_row(r)
            else:
                print("Disk row has incorrect number of values: %s" % r)

        print(pt)


def print_vg_view(rows=None, extended=False):
    """Print all summary VG views using PrettyTable"""
    vg_labels_extended = \
        ['Host', 'VG Name', 'UUID', 'VG State', 'VG Size', 'Current LVs',
         'Current PVs', 'PV List (name:state:uuid)', 'VG Parameters']

    vg_labels_brief = \
        ['Host', 'VG Name', 'VG State', 'VG Size', 'Current LVs',
         'Current PVs', 'PV List (name:state)', 'VG Parameters']

    if len(rows) > 0:
        print()
        print("VOLUME GROUPS:  (VG view)")

        pt = PrettyTable(vg_labels_extended) if extended else  \
            PrettyTable(vg_labels_brief)
        pt.align = 'l'
        for C in ['VG Size', 'Current LVs', 'Current PVs']:
            pt.align[C] = 'r'

        for r in rows:
            if len(r) == len(pt.field_names):
                pt.add_row(r)
            else:
                print("VG row has incorrect number of values: %s" % r)

        print(pt)


def get_info_and_display(cc, show=None):
    """Get storage information from server nodes

    Display the following information in table format:
    - disk data of all server nodes
    - VG data of all servers nodes
    """
    # get list of server hosts and for each host retrieve
    # the disk, lvg. pv list objects.

    host_storage_attr = {}
    hosts = cc.ihost.list()
    hostnames = []
    for h in hosts:
        hostname = getattr(h, 'hostname', '')
        hostnames.append(hostname)
        host_disks = cc.idisk.list(h.uuid)
        host_pvs = cc.ipv.list(h.uuid)
        host_lvgs = cc.ilvg.list(h.uuid)
        host_storage_attr[hostname] = {'host_disks': host_disks,
                                       'host_pvs': host_pvs,
                                       'host_lvgs': host_lvgs}

    disk_view = []
    vg_view = []

    pv_fields_ext = ['lvm_pv_name', 'pv_state', 'lvm_pv_uuid']
    pv_fields = ['lvm_pv_name', 'pv_state']
    disk_fields_ext = ['device_node', 'device_type', 'uuid', 'size_mib']
    disk_fields = ['device_node', 'size_mib']
    lvg_fields_ext = ['lvm_vg_name', 'uuid', 'vg_state', 'lvm_vg_size',
                      'lvm_cur_lv', 'lvm_cur_pv']
    lvg_fields = ['lvm_vg_name', 'vg_state', 'lvm_vg_size', 'lvm_cur_lv',
                  'lvm_cur_pv']

    # padding empty values in case not pv in disk.
    disk_pd_num_ext = 5
    disk_pd_num = 3
    pv_pd_num_ext = 4
    pv_pd_num = 3

    for k, v in host_storage_attr.items():
        if show['diskview'] or show['all']:
            for disk_o in v['host_disks']:
                device_node = getattr(disk_o, 'device_node', '')
                drow = [k]
                if show['extended']:
                    drow.extend([(getattr(disk_o, f, ''))
                                 for f in disk_fields_ext])
                    drow[4] = convert_to_readable_size(
                        getattr(disk_o, 'size_mib', ''), 'MB')
                else:
                    drow.extend([(getattr(disk_o, f, ''))
                                 for f in disk_fields])
                    drow[2] = convert_to_readable_size(
                        getattr(disk_o, 'size_mib', ''), 'MB')

                if v['host_pvs']:
                    first = True
                    for pv_o in v['host_pvs']:
                        pv_node = getattr(pv_o, 'idisk_device_node', '')
                        if pv_node == device_node:
                            if first:
                                if show['extended']:
                                    drow.extend([(getattr(pv_o, f, ''))
                                                 for f in pv_fields_ext])
                                else:
                                    drow.extend([(getattr(pv_o, f, ''))
                                                 for f in pv_fields])
                                first = False
                            else:
                                disk_view.append(drow)
                                # new row for next pv
                                # padd for host, device_node, size
                                if show['extended']:
                                    drow = [''] * disk_pd_num_ext
                                    drow.extend([(getattr(pv_o, f, ''))
                                                 for f in pv_fields_ext])
                                else:
                                    drow = [''] * disk_pd_num
                                    drow.extend([(getattr(pv_o, f, ''))
                                                 for f in pv_fields])

                            for vg_o in v['host_lvgs']:
                                vg_str = ""
                                if getattr(pv_o, 'lvm_vg_name', '') == \
                                        getattr(vg_o, 'lvm_vg_name', ''):
                                    if show['extended']:
                                        vg_str += ":".join(
                                            [str(getattr(pv_o, 'lvm_vg_name',
                                                         '')),
                                             str(getattr(vg_o, 'vg_state')),
                                             str(getattr(vg_o, 'uuid'))])
                                    else:
                                        vg_str += ":".join(
                                            [str(getattr(pv_o, 'lvm_vg_name',
                                                         '')),
                                             str(getattr(vg_o, 'vg_state'))])

                                    drow.append(vg_str)
                else:
                    if show['extended']:
                        drow.extend([''] * pv_pd_num_ext)
                    else:
                        drow.extend([''] * pv_pd_num)

                disk_view.append(drow)  # add to disk row disk view rows

        if show['vgview'] or show['all']:
            for vg_o in v['host_lvgs']:
                vgrow = [k]
                if show['extended']:
                    vgrow.extend([(getattr(vg_o, f, ''))
                                  for f in lvg_fields_ext])
                    vgrow[4] = convert_to_readable_size(
                        getattr(vg_o, 'lvm_vg_size', ''))
                else:
                    vgrow.extend([(getattr(vg_o, f, '')) for f in lvg_fields])
                    vgrow[3] = convert_to_readable_size(
                        getattr(vg_o, 'lvm_vg_size', ''))

                # list of current pvs for each VG
                count = 0
                for pv_o in v['host_pvs']:
                    pv_str = ""
                    if getattr(vg_o, 'lvm_vg_name', '') == getattr(
                            pv_o, 'lvm_vg_name', ''):
                        count += 1
                        if count > 1:
                            pv_str += ', '

                        if show['extended']:
                            pv_str += ":".join(
                                [str(getattr(pv_o, f, ''))
                                 for f in pv_fields_ext])
                        else:
                            pv_str += ":".join(
                                [str(getattr(pv_o, f, '')) for f in pv_fields])
                        vgrow.append(pv_str)

                vgrow.append(getattr(vg_o, 'capabilities', ''))

                vg_view.append(vgrow)

    print_disk_view(rows=disk_view, extended=show['extended'])
    print_vg_view(rows=vg_view, extended=show['extended'])


def main():
    try:
        # Process command line options and arguments, configure logging,
        # configure debug and show options
        parse_arguments(show)

        if not show['diskview'] and not show['vgview']:
            # both disk and vg views are printed
            show['all'] = True

        api_version = utils.env('SYSTEM_API_VERSION', default='1')

        # Print selected options, and timestamp
        prog = os.path.basename(sys.argv[0])
        ts = datetime.datetime.now()
        if show['debug']:
            print("%s: %s  options: view:%s System api version: %s"
                  % (prog, ts.isoformat(), show, api_version))

        cgts_client_creds = get_system_creds()
        if not cgts_client_creds['os_username']:
            raise exc.CommandError("You must provide a username via "
                                   "env[OS_USERNAME]")
        if not cgts_client_creds['os_password']:
            # priviledge check (only allow Keyring retrieval if we are root)
            if os.geteuid() == 0:
                cgts_client_creds['os_password'] = keyring.get_password(
                    'CGCS', cgts_client_creds['os_username'])
            else:
                raise exc.CommandError("You must provide a password via "
                                       "env[OS_PASSWORD]")

        if not cgts_client_creds['os_tenant_name']:
            raise exc.CommandError("You must provide a tenant_id via "
                                   "env[OS_TENANT_NAME]")

        if not cgts_client_creds['os_auth_url']:
            raise exc.CommandError("You must provide a auth url via "
                                   "env[OS_AUTH_URL]")

        if not cgts_client_creds['os_region_name']:
            raise exc.CommandError("You must provide a region_name via "
                                   "env[OS_REGION_NAME]")

        cc = cgts_client.get_client(api_version, **cgts_client_creds)

        # Get all info and display in table format
        get_info_and_display(cc, show)
        sys.exit(0)

    except KeyboardInterrupt as e:
        logger.warning('caught: %r, shutting down', e)
        sys.exit(0)

    except IOError as e:
        logger.warning('caught: %r, shutting down', e)
        sys.exit(0)

    except Exception as e:
        logger.error('exception: %r', e, exc_info=1)
        sys.exit(-4)
