#!/usr/bin/python
#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import ast
import os
import os.path
import re
import subprocess
import sys


#########
# Utils #
#########

def command(arguments, **kwargs):
    """ Execute e command and capture stdout, stderr & return code """
    process = subprocess.Popen(
        arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs)
    out, err = process.communicate()
    return out, err, process.returncode


def get_input(arg, valid_keys):
    """Convert the input to a dict and perform basic validation"""
    json_string = arg.replace("\\n", "\n")
    try:
        input_dict = ast.literal_eval(json_string)
        if not all(k in input_dict for k in valid_keys):
            return None
    except Exception:
        return None

    return input_dict


def get_partition_uuid(dev):
    output, _, _ = command(['blkid', dev])
    try:
        return re.search('PARTUUID=\"(.+?)\"', output).group(1)
    except AttributeError:
        return None


def device_path_to_device_node(device_path):
    try:
        output, _, _ = command(["udevadm", "settle", "-E", device_path])
        out, err, retcode = command(["readlink", "-f", device_path])
        out = out.rstrip()
    except Exception as e:
        return None

    return out


###########################################
# Manage Journal Disk Partitioning Scheme #
###########################################

DISK_BY_PARTUUID = "/dev/disk/by-partuuid/"
JOURNAL_UUID='45b0969e-9b03-4f30-b4c6-b4b80ceff106'  # Type of a journal partition


def is_partitioning_correct(disk_path, partition_sizes):
    """ Validate the existence and size of journal partitions"""

    # Obtain the device node from the device path.
    disk_node = device_path_to_device_node(disk_path)

    # Check that partition table format is GPT
    output, _, _ = command(["udevadm", "settle", "-E", disk_node])
    output, _, _ = command(["parted", "-s", disk_node, "print"])
    if not re.search('Partition Table: gpt', output):
        print "Format of disk node %s is not GPT, zapping disk" % disk_node
        return False

    # Check each partition size
    partition_index = 1
    for size in partition_sizes:
        # Check that each partition size matches the one in input
        partition_node = disk_node + str(partition_index)
        output, _, _ = command(["udevadm", "settle", "-E", partition_node])
        cmd = ["parted", "-s", partition_node, "unit", "MiB", "print"]
        output, _, _ = command(cmd)

        regex = ("^Disk " + str(partition_node) + ":\\s*" +
                 str(size) + "[\\.0]*MiB")
        if not re.search(regex, output, re.MULTILINE):
            print ("Journal partition %(node)s size is not %(size)s, "
                   "zapping disk" % {"node": partition_node, "size": size})
            return False

        partition_index += 1

    output, _, _ = command(["udevadm", "settle", "-t", "10"])
    return True


def create_partitions(disk_path, partition_sizes):
    """ Recreate partitions """

    # Obtain the device node from the device path.
    disk_node = device_path_to_device_node(disk_path)

    # Issue: After creating a new partition table on a device, Udev does not
    # always remove old symlinks (i.e. to previous partitions on that device).
    # Also, even if links are erased before zapping the disk, some of them will
    # be recreated even though there is no partition to back them!
    # Therefore, we have to remove the links AFTER we erase the partition table
    # Issue: DISK_BY_PARTUUID directory is not present at all if there are no
    # GPT partitions on the storage node so nothing to remove in this case
    links = []
    if os.path.isdir(DISK_BY_PARTUUID):
    	links = [ os.path.join(DISK_BY_PARTUUID,l) for l in os.listdir(DISK_BY_PARTUUID) 
        	        if os.path.islink(os.path.join(DISK_BY_PARTUUID, l)) ]

    # Erase all partitions on current node by creating a new GPT table
    _, err, ret = command(["parted", "-s", disk_node, "mktable", "gpt"])
    if ret:
        print ("Error erasing partition table of %(node)s\n"
               "Return code: %(ret)s reason: %(reason)s" %
               {"node": disk_node, "ret": ret, "reason": err})
        exit(1)

    # Erase old symlinks
    for l in links:
        if disk_node in os.path.realpath(l):
            os.remove(l)

    # Create partitions in order
    used_space_mib = 1  # leave 1 MB at the beginning of the disk
    num = 1
    for size in partition_sizes:
        cmd = ['parted', '-s', disk_node, 'unit', 'mib',
               'mkpart', 'primary',
               str(used_space_mib), str(used_space_mib + size)]
        _, err, ret = command(cmd)
        parms = {"disk_node": disk_node,
                 "start": used_space_mib,
                 "end": used_space_mib + size,
                 "reason": err}
        print ("Created partition from start=%(start)s MiB to end=%(end)s MiB"
               " on %(disk_node)s" % parms)
        if ret:
            print ("Failed to create partition with "
                   "start=%(start)s, end=%(end)s "
                   "on %(disk_node)s reason: %(reason)s" % parms)
            exit(1)
        # Set partition type to ceph journal
        # noncritical operation, it makes 'ceph-disk list' output correct info
        cmd = ['sgdisk',
               '--change-name={num}:ceph journal'.format(num=num),
               '--typecode={num}:{uuid}'.format(
                  num=num,
                  uuid=JOURNAL_UUID,
                  ),
               disk_node]
        _, err, ret = command(cmd)
        if ret:
            print ("WARNINIG: Failed to set partition name and typecode")
        used_space_mib += size
        num += 1

###########################
# Manage Journal Location #
###########################

OSD_PATH = "/var/lib/ceph/osd/"


def mount_data_partition(data_path, osdid):
    """ Mount an OSD data partition and return the mounted path """

    # Obtain the device node from the device path.
    data_node = device_path_to_device_node(data_path)

    mount_path = OSD_PATH + "ceph-" + str(osdid)
    output, _, _ = command(['mount'])
    regex = "^" + data_node + ".*" + mount_path
    if not re.search(regex, output, re.MULTILINE):
        cmd = ['mount', '-t', 'xfs', data_node, mount_path]
        _, _, ret = command(cmd)
        params = {"node": data_node, "path": mount_path}
        if ret:
            print "Failed to mount %(node)s to %(path), aborting" % params
            exit(1)
        else:
            print "Mounted %(node)s to %(path)s" % params
    return mount_path


def is_location_correct(path, journal_path, osdid):
    """ Check if location points to the correct device """

    # Obtain the device node from the device path.
    journal_node = device_path_to_device_node(journal_path)

    cur_node = os.path.realpath(path + "/journal")
    if cur_node == journal_node:
        return True
    else:
        return False


def fix_location(mount_point, journal_path, osdid):
    """ Move the journal to the new partition """

    # Obtain the device node from the device path.
    journal_node = device_path_to_device_node(journal_path)

    # Fix symlink
    path = mount_point + "/journal"  # 'journal' symlink path used by ceph-osd
    journal_uuid = get_partition_uuid(journal_node)
    new_target = DISK_BY_PARTUUID + journal_uuid
    params = {"path": path, "target": new_target}
    try:
        if os.path.lexists(path):
            os.unlink(path)  # delete the old symlink
        os.symlink(new_target, path)
        print "Symlink created: %(path)s -> %(target)s" % params
    except:
        print "Failed to create symlink: %(path)s -> %(target)s" % params
        exit(1)
    # Fix journal_uuid
    path = mount_point + "/journal_uuid"
    try:
        with open(path, 'w') as f:
            f.write(journal_uuid)
    except Exception as ex:
        # The operation is noncritical, it only makes 'ceph-disk list'
        # display complete output. We log and continue.
        params = {"path": path, "uuid": journal_uuid}
        print "WARNING: Failed to set uuid of %(path)s to %(uuid)s" % params

    # Clean the journal partition
    # even if erasing the partition table, if another journal was present here
    # it's going to be reused. Journals are always bigger than 100MB.
    command(['dd', 'if=/dev/zero', 'of=%s' % journal_node,
             'bs=1M', 'count=100'])

    # Format the journal
    cmd = ['/usr/bin/ceph-osd', '-i', str(osdid),
           '--pid-file', '/var/run/ceph/osd.%s.pid' % osdid,
           '-c', '/etc/ceph/ceph.conf',
           '--cluster', 'ceph',
           '--mkjournal']
    out, err, ret = command(cmd)
    params = {"journal_node": journal_node,
              "osdid": osdid,
              "ret": ret,
              "reason": err}
    if not ret:
        print ("Prepared new journal partition: %(journal_node)s "
               "for osd id: %(osdid)s") % params
    else:
        print ("Error initializing journal node: "
               "%(journal_node)s for osd id: %(osdid)s "
               "ceph-osd return code: %(ret)s reason: %(reason)s" % params)


########
# Main #
########

def main(argv):
    # parse and validate arguments
    err = False
    partitions = None
    location = None
    if len(argv) != 2:
        err = True
    elif argv[0] == "partitions":
        valid_keys = ['disk_path', 'journals']
        partitions = get_input(argv[1], valid_keys)
        if not partitions:
            err = True
        elif not isinstance(partitions['journals'], list):
            err = True
    elif argv[0] == "location":
        valid_keys = ['data_path', 'journal_path', 'osdid']
        location = get_input(argv[1], valid_keys)
        if not location:
            err = True
        elif not isinstance(location['osdid'], int):
            err = True
    else:
        err = True
    if err:
        print "Command intended for internal use only"
        exit(-1)

    if partitions:
        # Recreate partitions only if the existing ones don't match input
        if not is_partitioning_correct(partitions['disk_path'],
                                       partitions['journals']):
            create_partitions(partitions['disk_path'], partitions['journals'])
        else:
            print ("Partition table for %s is correct, "
                   "no need to repartition" %
                   device_path_to_device_node(partitions['disk_path']))
    elif location:
        # we need to have the data partition mounted & we can let it mounted
        mount_point = mount_data_partition(location['data_path'],
                                           location['osdid'])
        # Update journal location only if link point to another partition
        if not is_location_correct(mount_point,
                                   location['journal_path'],
                                   location['osdid']):
            print ("Fixing journal location for "
                   "OSD id: %(id)s" % {"node": location['data_path'],
                                       "id": location['osdid']})
            fix_location(mount_point,
                         location['journal_path'],
                         location['osdid'])
        else:
            print ("Journal location for %s is correct,"
                   "no need to change it" % location['data_path'])

main(sys.argv[1:])
