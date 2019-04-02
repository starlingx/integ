#!/usr/bin/python
#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
#
# Wait for one or a group of OSDs to match one or a group of statuses
# as reported by "ceph osd tree".
#
# Examples:
# - wait for osd 0 to be up:
#     osd-wait-status -o 0 -s up
#
# - wait for osd 0 and osd 1 to be up:
#     osd-wait-status -o 0 1 -s up
#
# The amount of time spent waiting for OSDs to match a status can
# be limited by specifying:
#
# - the maximum retry count; the script will if the status doesn't
#   match the desired one after more than retry count attempts.
#   The interval between attempts is controlled by the "-i" flag.
#   Example:
#     osd-wait-status -o 0 -s up -c 2 -i 3
#   will call "ceph osd tree" once to get the status of osd 0 and if
#   it's not "up" then it will try one more time after 3 seconds.
#
# - a deadline as the maximum interval of time the script is looping
#   waiting for OSDs to match status. The interval between attempts
#   is controlled by the "-i" flag.
#   Example:
#     osd-wait-status -o 0 -s up -d 10 -i 3
#   will call "ceph osd tree" until either osd 0 status is "up" or
#   no more than 10 seconds have passed, that's 3-4 attempts depending
#   on how much time it takes to run "ceph osd tree"
#
# Status match can be reversed by using "-n" flag.
# Example:
#   osd-wait-status -o 0 -n -s up
# waits until osd 0 status is NOT up.
#
# osd-wait-status does not allow matching arbitrary combinations of
# OSDs and statuses. For example: "osd 0 up and osd 1 down" is not
# supported.
#
# Return code is 0 if OSDs match expected status before the
# retry count*interval / deadline limits are reached.

import argparse
import json
import logging
import retrying
import subprocess
import sys
import time

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger('osd-wait-status')

CEPH_BINARY_PATH = '/usr/bin/ceph'
RETRY_INTERVAL_SEC = 1
RETRY_FOREVER = 0
NO_DEADLINE = 0


class OsdException(Exception):
    def __init__(self, message, restartable=False):
        super(OsdException, self).__init__(message)
        self.restartable = restartable


def get_osd_tree():
    command = [CEPH_BINARY_PATH,
               'osd', 'tree', '--format', 'json']
    try:
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        output, error = p.communicate()
        if p.returncode != 0:
            raise OsdException(
                ('Command failed: command="{}", '
                 'returncode={}, output="{}"').format(
                    ' '.join(command),
                    p.returncode,
                    output, error),
                restartable=True)
    except OSError as e:
        raise OsdException(
            ('Command failed: command="{}", '
             'reason="{}"').format(command, str(e)))
    try:
        return json.loads(output)
    except ValueError as e:
        raise OsdException(
            ('JSON decode failed: '
             'data="{}", error="{}"').format(
                output, e))


def osd_match_status(target_osd, target_status,
                     reverse_logic):
    LOG.info(('Match status: '
              'target_osd={}, '
              'target status={}, '
              'reverse_logic={}').format(
        target_osd, target_status, reverse_logic))
    tree = get_osd_tree()
    osd_status = {}
    for node in tree.get('nodes'):
        name = node.get('name')
        if name in target_osd:
            osd_status[name] = node.get('status')
        if len(osd_status) == len(target_osd):
            break
    LOG.info('Current OSD(s) status: {}'.format(osd_status))
    for name in target_osd:
        if name not in osd_status:
            raise OsdException(
                ('Unable to retrieve status '
                 'for "{}"').format(
                    name))
        if reverse_logic:
            if osd_status[name] not in target_status:
                del osd_status[name]
        else:
            if osd_status[name] in target_status:
                del osd_status[name]
    if len(osd_status) == 0:
        LOG.info('OSD(s) status target reached.')
        return True
    else:
        LOG.info('OSD(s) {}matching status {}: {}'.format(
            '' if reverse_logic else 'not ',
            target_status,
            osd_status.keys()))
        return False


def osd_wait_status(target_osd, target_status,
                    reverse_logic,
                    retry_count, retry_interval,
                    deadline):

    def retry_if_false(result):
        return (result is False)

    def retry_if_restartable(exception):
        return (isinstance(exception, OsdException)
                and exception.restartable)

    LOG.info(('Wait options: '
              'target_osd={}, '
              'target_status={}, '
              'reverse_logic={}, '
              'retry_count={}, '
              'retry_interval={}, '
              'deadline={}').format(
        target_osd, target_status, reverse_logic,
        retry_count, retry_interval, deadline))
    kwargs = {
        'retry_on_result': retry_if_false,
        'retry_on_exception': retry_if_restartable}
    if retry_count != RETRY_FOREVER:
        kwargs['stop_max_attempt_number'] = retry_count
    if deadline != NO_DEADLINE:
        kwargs['stop_max_delay'] = deadline * 1000
    if retry_interval != 0:
        kwargs['wait_fixed'] = retry_interval * 1000
    if not len(target_osd):
        return
    retrying.Retrying(**kwargs).call(
        osd_match_status,
        target_osd, target_status,
        reverse_logic)


def non_negative_interger(value):
    value = int(value)
    if value < 0:
        raise argparse.argumenttypeerror(
            '{} is a negative integer value'.format(value))
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Wait for OSD status match')
    parser.add_argument(
        '-o', '--osd',
        nargs='*',
        help='osd id',
        type=non_negative_interger,
        required=True)
    parser.add_argument(
        '-n', '--not',
        dest='reverse_logic',
        help='reverse logic: wait for status NOT to match',
        action='store_true',
        default=False)
    parser.add_argument(
        '-s', '--status',
        nargs='+',
        help='status',
        type=str,
        required=True)
    parser.add_argument(
        '-c', '--retry-count',
        help='retry count',
        type=non_negative_interger,
        default=RETRY_FOREVER)
    parser.add_argument(
        '-i', '--retry-interval',
        help='retry interval (seconds)',
        type=non_negative_interger,
        default=RETRY_INTERVAL_SEC)
    parser.add_argument(
        '-d', '--deadline',
        help='deadline (seconds)',
        type=non_negative_interger,
        default=NO_DEADLINE)
    args = parser.parse_args()
    start = time.time()
    try:
        osd_wait_status(
            ['osd.{}'.format(o) for o in args.osd],
            args.status,
            args.reverse_logic,
            args.retry_count,
            args.retry_interval,
            args.deadline)
        LOG.info('Elapsed time: {:.02f} seconds'.format(
            time.time() - start))
        sys.exit(0)
    except retrying.RetryError as e:
        LOG.warn(
            ('Retry error: {}. '
             'Elapsed time: {:.02f} seconds'.format(
                 e, time.time() - start)))
    except OsdException as e:
        LOG.warn(
            ('OSD wait error: {}. '
             'Elapsed time: {:.02f} seconds').format(
                e, time.time() - start))
    sys.exit(1)
