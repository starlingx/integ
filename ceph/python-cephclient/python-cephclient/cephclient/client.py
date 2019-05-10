#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import ipaddress
import json
import logging
import re
import requests
import six
import subprocess
import time

from cephclient.exception import CephMonRestfulListKeysError
from cephclient.exception import CephMonRestfulJsonError
from cephclient.exception import CephMonRestfulMissingUserCredentials
from cephclient.exception import CephMgrDumpError
from cephclient.exception import CephMgrJsonError
from cephclient.exception import CephMgrMissingRestfulService
from cephclient.exception import CephClientFormatNotSupported
from cephclient.exception import CephClientResponseFormatNotImplemented
from cephclient.exception import CephClientInvalidChoice
from cephclient.exception import CephClientTypeError
from cephclient.exception import CephClientValueOutOfBounds
from cephclient.exception import CephClientInvalidPgid
from cephclient.exception import CephClientInvalidIPAddr
from cephclient.exception import CephClientInvalidOsdIdValue
from cephclient.exception import CephClientNoSuchUser
from cephclient.exception import CephClientIncorrectPassword


CEPH_MON_RESTFUL_USER = 'admin'
CEPH_MON_RESTFUL_SERVICE = 'restful'
CEPH_CLIENT_RETRY_COUNT = 2
CEPH_CLIENT_RETRY_TIMEOUT_SEC = 5
CEPH_CLI_TIMEOUT_SEC = 5
API_SUPPORTED_RESPONSE_FORMATS = [
    'text', 'json', 'xml', 'binary'
]

LOG = logging.getLogger('ceph_client')
LOG.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'))
LOG.addHandler(ch)


class CephClient(object):

    def __init__(self,
                 username=CEPH_MON_RESTFUL_USER,
                 password=None,
                 retry_count=CEPH_CLIENT_RETRY_COUNT,
                 retry_timeout=CEPH_CLIENT_RETRY_TIMEOUT_SEC):
        self.username = username
        self.password = password
        self.check_certificate = True
        self.service_url = None
        # TODO: fix certificates
        self._disable_certificate_checks()
        self.session = None
        self.retry_count = retry_count
        self.retry_timeout = retry_timeout

    def _refresh_session(self):
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)

    def _disable_certificate_checks(self):
        self.check_certificate = False
        requests.packages.urllib3.disable_warnings()
        LOG.warning('skip checking server certificate')

    def _get_password(self):
        try:
            output = subprocess.check_output(
                ('ceph restful list-keys '
                 '--connect-timeout {}').format(
                    CEPH_CLI_TIMEOUT_SEC),
                shell=True)
        except subprocess.CalledProcessError as e:
            raise CephMonRestfulListKeysError(str(e))
        try:
            keys = json.loads(output)
        except (KeyError, ValueError):
            raise CephMonRestfulJsonError(output)
        try:
            self.password = keys[self.username]
        except KeyError:
            raise CephMonRestfulMissingUserCredentials(self.username)

    def _get_service_url(self):
        try:
            output = subprocess.check_output(
                ('ceph mgr dump '
                 '--connect-timeout {}').format(
                    CEPH_CLI_TIMEOUT_SEC),
                shell=True)
        except subprocess.CalledProcessError as e:
            raise CephMgrDumpError(str(e))
        try:
            status = json.loads(output)
        except (KeyError, ValueError):
            raise CephMgrJsonError(output)
        try:
            self.service_url = status["services"][CEPH_MON_RESTFUL_SERVICE]
        except (KeyError, TypeError):
            raise CephMgrMissingRestfulService(
                status.get('services', ''))

    def _make_text_result(self, prefix, result):
        if result.get('has_failed'):
            assert(len(result['failed']) == 1)
            response = requests.Response()
            response.status_code = requests.codes.internal_server_error
            response.reason = result['failed'][0]['outs'].rstrip()
            return response, response.reason
        else:
            assert(len(result['finished']) == 1)
            response = requests.Response()
            response.status_code = requests.codes.ok
            response.reason = "OK"
            return response, result['finished'][0]['outb'].rstrip()

    def _apply_json_result_workarounds(self, prefix, outb):
        if prefix == 'osd crush tree':
            # ceph mgr strangely adds a pair of square brackets at the end
            while outb.endswith('][]'):
                LOG.info("Trim 'osd crush tree' json response")
                outb = outb[:-2]
        return outb

    def _make_json_result(self, prefix, result):
        if result.get('has_failed'):
            assert(len(result['failed']) == 1)
            response = requests.Response()
            response.status_code = requests.codes.internal_server_error
            response.reason = result['failed'][0]['outs']
            return response, dict(
                status=result['failed'][0]['outs'],
                output=result['failed'][0]['outb'])
        else:
            assert(len(result['finished']) == 1)
            outb = result['finished'][0]['outb']
            outb = self._apply_json_result_workarounds(prefix, outb)
            response = requests.Response()
            response.status_code = requests.codes.ok
            response.reason = "OK"
            try:
                return response, dict(
                    status=result['finished'][0]['outs'],
                    output=json.loads(outb or 'null'))
            except (ValueError, TypeError):
                raise CephMgrJsonError(outb)

    def _request(self, prefix, *args, **kwargs):
        if not self.password:
            self._get_password()
        if not self.service_url:
            self._get_service_url()
        if not self.session:
            self._refresh_session()
        format = kwargs.get('body', 'json').lower()
        if format not in API_SUPPORTED_RESPONSE_FORMATS:
            raise CephClientFormatNotSupported(
                prefix=prefix, format=format)
        del kwargs['body']
        req_json = dict(kwargs)
        req_json['format'] = format
        assert('prefix' not in kwargs)
        req_json['prefix'] = prefix
        if 'timeout' in req_json:
            timeout = req_json['timeout']
            del req_json['timeout']
        else:
            timeout = None
        LOG.info('Request params: url={}, json={}'.format(
            self.service_url + 'request?wait=1', req_json))
        credit = self.retry_count + 1
        while credit > 0:
            credit -= 1
            try:
                result = self.session.post(
                    self.service_url + 'request?wait=1',
                    json=req_json,
                    verify=self.check_certificate,
                    timeout=timeout).json()
                LOG.info('Result: {}'.format(result))
                if 'is_finished' in result:
                    self.session.delete(
                        self.service_url + 'request?id=' + result['id'])
                else:
                    assert('message' in result)
                    if 'auth: No such user' in result['message']:
                        raise CephClientNoSuchUser(user=self.username)
                    elif 'auth: Incorrect password' in result['message']:
                        raise CephClientIncorrectPassword(
                            user=self.username)
                break
            except CephClientIncorrectPassword:
                if not credit:
                    raise
                LOG.warning('Incorrect password for user \'{}\'. '
                            'Fetch user password via list-keys '
                            'and retry.'.format(self.username))
                if self.retry_timeout > 0:
                    time.sleep(self.retry_timeout)
                self._get_password()
                self._refresh_session()
            except (requests.ConnectionError,
                    requests.Timeout,
                    requests.HTTPError) as e:
                if not credit:
                    raise IOError(str(e))
                LOG.warning(
                    'Request error: {}. '
                    'Refresh restful service URL and retry'.format(e))
                if self.retry_timeout > 0:
                    time.sleep(self.retry_timeout)
                self._get_service_url()
                self._refresh_session()
        if format == 'json':
            return self._make_json_result(prefix, result)
        elif format == 'text':
            return self._make_text_result(prefix, result)
        else:
            raise CephClientResponseFormatNotImplemented(
                format=format, reason=result["finished"][0]["outb"])

    def pg_stat(self, body='json', timeout=None):
        """show placement group status."""
        return self._request('pg stat', body=body, timeout=timeout)

    def pg_getmap(self, body='json', timeout=None):
        """get binary pg map to -o/stdout"""
        return self._request('pg getmap', body=body, timeout=timeout)

    PG_DUMP_DUMPCONTENTS_VALUES = \
        ['all', 'summary', 'sum', 'delta', 'pools',
         'osds', 'pgs', 'pgs_brief']

    def pg_dump(self, dumpcontents=None, body='json', timeout=None):
        """show human-readable versions of pg map (only 'all' valid with plain)"""
        kwargs = dict(body=body, timeout=timeout)
        if dumpcontents is not None:
            if not isinstance(dumpcontents, six.string_types):
                raise CephClientTypeError(
                    name='dumpcontents',
                    actual=type(dumpcontents),
                    expected=six.string_types)
            supported = CephClient.PG_DUMP_DUMPCONTENTS_VALUES
            if dumpcontents not in supported:
                raise CephClientInvalidChoice(
                    function='pg_dump',
                    option='dumpcontents',
                    value=dumpcontents,
                    supported=', '.join(supported))
            if not isinstance(dumpcontents, list):
                dumpcontents = [dumpcontents]
            kwargs['dumpcontents'] = dumpcontents
        return self._request('pg dump', **kwargs)

    PG_DUMP_JSON_DUMPCONTENTS_VALUES = [
        'all', 'summary', 'sum', 'pools', 'osds', 'pgs']

    def pg_dump_json(self, dumpcontents=None, body='json', timeout=None):
        """show human-readable version of pg map in json only"""
        kwargs = dict(body=body, timeout=timeout)
        if dumpcontents is not None:
            if not isinstance(dumpcontents, six.string_types):
                raise CephClientTypeError(
                    name='dumpcontents',
                    actual=type(dumpcontents),
                    expected=six.string_types)
            supported = CephClient.PG_DUMP_JSON_DUMPCONTENTS_VALUES
            if dumpcontents not in supported:
                raise CephClientInvalidChoice(
                    function='pg_dump_json',
                    option='dumpcontents',
                    value=dumpcontents,
                    supported=', '.join(supported))
            if not isinstance(dumpcontents, list):
                dumpcontents = [dumpcontents]
            kwargs['dumpcontents'] = dumpcontents
        return self._request('pg dump_json', **kwargs)

    def pg_dump_pools_json(self, body='json', timeout=None):
        """show pg pools info in json only"""
        return self._request('pg dump_pools_json',
                             body=body, timeout=timeout)

    def pg_ls_by_pool(self, poolstr, states=None,
                      body='json', timeout=None):
        """list pg with pool = [poolname]"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(poolstr, six.string_types):
            raise CephClientTypeError(
                name='poolstr',
                actual=type(poolstr),
                expected=six.string_types)

        kwargs['poolstr'] = poolstr
        if states is not None:
            if isinstance(states, list):
                for item in states:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='states',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(states, six.string_types):
                    raise CephClientTypeError(
                        name='states',
                        actual=type(states),
                        expected=six.string_types)
            if not isinstance(states, list):
                states = [states]
            kwargs['states'] = states
        return self._request('pg ls-by-pool', **kwargs)

    def pg_ls_by_primary(self, osd, pool=None,
                         states=None, body='json', timeout=None):
        """list pg with primary = [osd]"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(osd, six.integer_types):
            pass
        elif isinstance(osd, six.string_types):
            osd = osd.lower()
            prefix = 'osd.'
            if not osd.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=osd)
            osd = int(osd[len(prefix):])
        else:
            raise CephClientTypeError(
                name='osd',
                actual=type(osd),
                expected='int or string')

        kwargs['osd'] = osd
        if pool is not None:
            if not isinstance(pool, six.integer_types):
                raise CephClientTypeError(
                    name='pool',
                    actual=type(pool),
                    expected=int)
            kwargs['pool'] = pool
        if states is not None:
            if isinstance(states, list):
                for item in states:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='states',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(states, six.string_types):
                    raise CephClientTypeError(
                        name='states',
                        actual=type(states),
                        expected=six.string_types)
            if not isinstance(states, list):
                states = [states]
            kwargs['states'] = states
        return self._request('pg ls-by-primary', **kwargs)

    def pg_ls_by_osd(self, osd, pool=None, states=None,
                     body='json', timeout=None):
        """list pg on osd [osd]"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(osd, six.integer_types):
            pass
        elif isinstance(osd, six.string_types):
            osd = osd.lower()
            prefix = 'osd.'
            if not osd.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=osd)
            osd = int(osd[len(prefix):])
        else:
            raise CephClientTypeError(
                name='osd',
                actual=type(osd),
                expected='int or string')

        kwargs['osd'] = osd
        if pool is not None:
            if not isinstance(pool, six.integer_types):
                raise CephClientTypeError(
                    name='pool',
                    actual=type(pool),
                    expected=int)
            kwargs['pool'] = pool
        if states is not None:
            if isinstance(states, list):
                for item in states:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='states',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(states, six.string_types):
                    raise CephClientTypeError(
                        name='states',
                        actual=type(states),
                        expected=six.string_types)
            if not isinstance(states, list):
                states = [states]
            kwargs['states'] = states
        return self._request('pg ls-by-osd', **kwargs)

    def pg_ls(self, pool=None, states=None, body='json', timeout=None):
        """list pg with specific pool, osd, state"""
        kwargs = dict(body=body, timeout=timeout)
        if pool is not None:
            if not isinstance(pool, six.integer_types):
                raise CephClientTypeError(
                    name='pool',
                    actual=type(pool),
                    expected=int)
            kwargs['pool'] = pool
        if states is not None:
            if isinstance(states, list):
                for item in states:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='states',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(states, six.string_types):
                    raise CephClientTypeError(
                        name='states',
                        actual=type(states),
                        expected=six.string_types)
            if not isinstance(states, list):
                states = [states]
            kwargs['states'] = states
        return self._request('pg ls', **kwargs)

    PG_DUMP_STUCK_STUCKOPS_VALUES = \
        ['inactive', 'unclean', 'stale', 'undersized',
         'degraded']

    def pg_dump_stuck(self, stuckops=None, threshold=None,
                      body='json', timeout=None):
        """show information about stuck pgs"""
        kwargs = dict(body=body, timeout=timeout)
        if stuckops is not None:
            if not isinstance(stuckops, six.string_types):
                raise CephClientTypeError(
                    name='stuckops',
                    actual=type(stuckops),
                    expected=six.string_types)
            supported = CephClient.PG_DUMP_STUCK_STUCKOPS_VALUES
            if stuckops not in supported:
                raise CephClientInvalidChoice(
                    function='pg_dump_stuck',
                    option='stuckops',
                    value=stuckops,
                    supported=', '.join(supported))
            if not isinstance(stuckops, list):
                stuckops = [stuckops]
            kwargs['stuckops'] = stuckops
        if threshold is not None:
            if not isinstance(threshold, six.integer_types):
                raise CephClientTypeError(
                    name='threshold',
                    actual=type(threshold),
                    expected=int)
            kwargs['threshold'] = threshold
        return self._request('pg dump_stuck', **kwargs)

    PG_DEBUG_DEBUGOP_VALUES = \
        ['unfound_objects_exist', 'degraded_pgs_exist']

    def pg_debug(self, debugop, body='json', timeout=None):
        """show debug info about pgs"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(debugop, six.string_types):
            raise CephClientTypeError(
                name='debugop',
                actual=type(debugop),
                expected=six.string_types)
        supported = CephClient.PG_DEBUG_DEBUGOP_VALUES
        if debugop not in supported:
            raise CephClientInvalidChoice(
                function='pg_debug',
                option='debugop',
                value=debugop,
                supported=', '.join(supported))

        kwargs['debugop'] = debugop
        return self._request('pg debug', **kwargs)

    def pg_scrub(self, pgid, body='json', timeout=None):
        """start scrub on <pgid>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        return self._request('pg scrub', **kwargs)

    def pg_deep_scrub(self, pgid, body='json', timeout=None):
        """start deep-scrub on <pgid>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        return self._request('pg deep-scrub', **kwargs)

    def pg_repair(self, pgid, body='json', timeout=None):
        """start repair on <pgid>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        return self._request('pg repair', **kwargs)

    def pg_force_recovery(self, pgid, body='json', timeout=None):
        """force recovery of <pgid> first"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        if not isinstance(pgid, list):
            pgid = [pgid]
        kwargs['pgid'] = pgid
        return self._request('pg force-recovery', **kwargs)

    def pg_force_backfill(self, pgid, body='json', timeout=None):
        """force backfill of <pgid> first"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        if not isinstance(pgid, list):
            pgid = [pgid]
        kwargs['pgid'] = pgid
        return self._request('pg force-backfill', **kwargs)

    def pg_cancel_force_recovery(self, pgid, body='json', timeout=None):
        """restore normal recovery priority of <pgid>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        if not isinstance(pgid, list):
            pgid = [pgid]
        kwargs['pgid'] = pgid
        return self._request('pg cancel-force-recovery', **kwargs)

    def pg_cancel_force_backfill(self, pgid, body='json', timeout=None):
        """restore normal backfill priority of <pgid>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        if not isinstance(pgid, list):
            pgid = [pgid]
        kwargs['pgid'] = pgid
        return self._request('pg cancel-force-backfill', **kwargs)

    def osd_perf(self, body='json', timeout=None):
        """print dump of OSD perf summary stats"""
        return self._request('osd perf', body=body, timeout=timeout)

    OSD_DF_OUTPUT_METHOD_VALUES = ['plain', 'tree']

    def osd_df(self, output_method=None, body='json', timeout=None):
        """show OSD utilization"""
        kwargs = dict(body=body, timeout=timeout)
        if output_method is not None:
            if not isinstance(output_method, six.string_types):
                raise CephClientTypeError(
                    name='output_method',
                    actual=type(output_method),
                    expected=six.string_types)
            supported = CephClient.OSD_DF_OUTPUT_METHOD_VALUES
            if output_method not in supported:
                raise CephClientInvalidChoice(
                    function='osd_df',
                    option='output_method',
                    value=output_method,
                    supported=', '.join(supported))
            kwargs['output_method'] = output_method
        return self._request('osd df', **kwargs)

    def osd_blocked_by(self, body='json', timeout=None):
        """print histogram of which OSDs are blocking their peers"""
        return self._request('osd blocked-by', body=body, timeout=timeout)

    def osd_pool_stats(self, pool_name=None, body='json', timeout=None):
        """obtain stats from all pools, or from specified pool"""
        kwargs = dict(body=body, timeout=timeout)
        if pool_name is not None:
            if not isinstance(pool_name, six.string_types):
                raise CephClientTypeError(
                    name='pool_name',
                    actual=type(pool_name),
                    expected=six.string_types)
            kwargs['pool_name'] = pool_name
        return self._request('osd pool stats', **kwargs)

    OSD_REWEIGHT_BY_UTILIZATION_NO_INCREASING_VALUES = ['--no-increasing']

    def osd_reweight_by_utilization(
            self, oload=None, max_change=None, max_osds=None,
            no_increasing=None, body='json', timeout=None):
        """reweight OSDs by utilization [overload-percentage-for-consideration,default 120] """
        kwargs = dict(body=body, timeout=timeout)
        if oload is not None:
            if not isinstance(oload, six.integer_types):
                raise CephClientTypeError(
                    name='oload',
                    actual=type(oload),
                    expected=int)
            kwargs['oload'] = oload
        if max_change is not None:
            if not isinstance(max_change, (six.integer_types, float)):
                raise CephClientTypeError(
                    name='max_change',
                    actual=type(max_change),
                    expected=int)
            kwargs['max_change'] = max_change
        if max_osds is not None:
            if not isinstance(max_osds, six.integer_types):
                raise CephClientTypeError(
                    name='max_osds',
                    actual=type(max_osds),
                    expected=int)
            kwargs['max_osds'] = max_osds
        if no_increasing is not None:
            if not isinstance(no_increasing, six.string_types):
                raise CephClientTypeError(
                    name='no_increasing',
                    actual=type(no_increasing),
                    expected=six.string_types)
            supported = CephClient.OSD_REWEIGHT_BY_UTILIZATION_NO_INCREASING_VALUES  # noqa E501
            if no_increasing not in supported:
                raise CephClientInvalidChoice(
                    function='osd_reweight_by_utilization',
                    option='no_increasing',
                    value=no_increasing,
                    supported=', '.join(supported))
            kwargs['no_increasing'] = no_increasing
        return self._request('osd reweight-by-utilization', **kwargs)

    OSD_TEST_REWEIGHT_BY_UTILIZATION_NO_INCREASING_VALUES = [
        '--no-increasing']

    def osd_test_reweight_by_utilization(
            self, oload=None, max_change=None, max_osds=None,
            no_increasing=None, body='json', timeout=None):
        """dry run of reweight OSDs by utilization [overload-percentage-for-consideration, default 120] """
        kwargs = dict(body=body, timeout=timeout)
        if oload is not None:
            if not isinstance(oload, six.integer_types):
                raise CephClientTypeError(
                    name='oload',
                    actual=type(oload),
                    expected=int)
            kwargs['oload'] = oload
        if max_change is not None:
            if not isinstance(max_change, (six.integer_types, float)):
                raise CephClientTypeError(
                    name='max_change',
                    actual=type(max_change),
                    expected=int)
            kwargs['max_change'] = max_change
        if max_osds is not None:
            if not isinstance(max_osds, six.integer_types):
                raise CephClientTypeError(
                    name='max_osds',
                    actual=type(max_osds),
                    expected=int)
            kwargs['max_osds'] = max_osds
        if no_increasing is not None:
            if not isinstance(no_increasing, six.string_types):
                raise CephClientTypeError(
                    name='no_increasing',
                    actual=type(no_increasing),
                    expected=six.string_types)
            supported = CephClient.OSD_TEST_REWEIGHT_BY_UTILIZATION_NO_INCREASING_VALUES  # noqa E501
            if no_increasing not in supported:
                raise CephClientInvalidChoice(
                    function='osd_test_reweight_by_utilization',
                    option='no_increasing',
                    value=no_increasing,
                    supported=', '.join(supported))
            kwargs['no_increasing'] = no_increasing
        return self._request('osd test-reweight-by-utilization', **kwargs)

    def osd_reweight_by_pg(
            self, oload=None, max_change=None, max_osds=None, pools=None,
            body='json', timeout=None):
        """reweight OSDs by PG distribution [overload-percentage-for-consideration, default 120] """
        kwargs = dict(body=body, timeout=timeout)
        if oload is not None:
            if not isinstance(oload, six.integer_types):
                raise CephClientTypeError(
                    name='oload',
                    actual=type(oload),
                    expected=int)
            kwargs['oload'] = oload
        if max_change is not None:
            if not isinstance(max_change, (six.integer_types, float)):
                raise CephClientTypeError(
                    name='max_change',
                    actual=type(max_change),
                    expected=int)
            kwargs['max_change'] = max_change
        if max_osds is not None:
            if not isinstance(max_osds, six.integer_types):
                raise CephClientTypeError(
                    name='max_osds',
                    actual=type(max_osds),
                    expected=int)
            kwargs['max_osds'] = max_osds
        if pools is not None:
            if isinstance(pools, list):
                for item in pools:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='pools',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(pools, six.string_types):
                    raise CephClientTypeError(
                        name='pools',
                        actual=type(pools),
                        expected=six.string_types)
            if not isinstance(pools, list):
                pools = [pools]
            kwargs['pools'] = pools
        return self._request('osd reweight-by-pg', **kwargs)

    def osd_test_reweight_by_pg(
            self, oload=None, max_change=None, max_osds=None, pools=None,
            body='json', timeout=None):
        """dry run of reweight OSDs by PG distribution [overload-percentage-for-consideration, default 120] """
        kwargs = dict(body=body, timeout=timeout)
        if oload is not None:
            if not isinstance(oload, six.integer_types):
                raise CephClientTypeError(
                    name='oload',
                    actual=type(oload),
                    expected=int)
            kwargs['oload'] = oload
        if max_change is not None:
            if not isinstance(max_change, (six.integer_types, float)):
                raise CephClientTypeError(
                    name='max_change',
                    actual=type(max_change),
                    expected=int)
            kwargs['max_change'] = max_change
        if max_osds is not None:
            if not isinstance(max_osds, six.integer_types):
                raise CephClientTypeError(
                    name='max_osds',
                    actual=type(max_osds),
                    expected=int)
            kwargs['max_osds'] = max_osds
        if pools is not None:
            if isinstance(pools, list):
                for item in pools:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='pools',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(pools, six.string_types):
                    raise CephClientTypeError(
                        name='pools',
                        actual=type(pools),
                        expected=six.string_types)
            if not isinstance(pools, list):
                pools = [pools]
            kwargs['pools'] = pools
        return self._request('osd test-reweight-by-pg', **kwargs)

    def osd_safe_to_destroy(self, ids, body='json', timeout=None):
        """check whether osd(s) can be safely destroyed without reducing datadurability """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd safe-to-destroy', **kwargs)

    def osd_ok_to_stop(self, ids, body='json', timeout=None):
        """check whether osd(s) can be safely stopped without reducing immediatedata availability """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd ok-to-stop', **kwargs)

    def osd_scrub(self, who, body='json', timeout=None):
        """initiate scrub on osd <who>, or use <all|any> to scrub all"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        return self._request('osd scrub', **kwargs)

    def osd_deep_scrub(self, who, body='json', timeout=None):
        """initiate deep scrub on osd <who>, or use <all|any> to deep scrub all"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        return self._request('osd deep-scrub', **kwargs)

    def osd_repair(self, who, body='json', timeout=None):
        """initiate repair on osd <who>, or use <all|any> to repair all"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        return self._request('osd repair', **kwargs)

    def service_dump(self, body='json', timeout=None):
        """dump service map"""
        return self._request('service dump', body=body, timeout=timeout)

    def service_status(self, body='json', timeout=None):
        """dump service state"""
        return self._request('service status', body=body, timeout=timeout)

    def config_show(self, who, key, body='json', timeout=None):
        """Show running configuration"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        return self._request('config show', **kwargs)

    def config_show_with_defaults(self, who, body='json', timeout=None):
        """Show running configuration (including compiled-in defaults)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        return self._request('config show-with-defaults', **kwargs)

    def pg_map(self, pgid, body='json', timeout=None):
        """show mapping of pg to osds"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        return self._request('pg map', **kwargs)

    def osd_last_stat_seq(self, _id, body='json', timeout=None):
        """get the last pg stats sequence number reported for this osd"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        return self._request('osd last-stat-seq', **kwargs)

    def auth_export(self, entity=None, body='json', timeout=None):
        """write keyring for requested entity, or master keyring if none given"""
        kwargs = dict(body=body, timeout=timeout)
        if entity is not None:
            if not isinstance(entity, six.string_types):
                raise CephClientTypeError(
                    name='entity',
                    actual=type(entity),
                    expected=six.string_types)
            kwargs['entity'] = entity
        return self._request('auth export', **kwargs)

    def auth_get(self, entity, body='json', timeout=None):
        """write keyring file with requested key"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        return self._request('auth get', **kwargs)

    def auth_get_key(self, entity, body='json', timeout=None):
        """display requested key"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        return self._request('auth get-key', **kwargs)

    def auth_print_key(self, entity, body='json', timeout=None):
        """display requested key"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        return self._request('auth print-key', **kwargs)

    def auth_list(self, body='json', timeout=None):
        """list authentication state"""
        return self._request('auth list', body=body, timeout=timeout)

    def auth_ls(self, body='json', timeout=None):
        """list authentication state"""
        return self._request('auth ls', body=body, timeout=timeout)

    def auth_import(self, body='json', timeout=None):
        """auth import: read keyring file from -i <file>"""
        return self._request('auth import', body=body, timeout=timeout)

    def auth_add(self, entity, caps=None, body='json', timeout=None):
        """add auth info for <entity> from input file, or random key if no inputis given, and/or any caps specified in the command """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        if caps is not None:
            if isinstance(caps, list):
                for item in caps:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='caps',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(caps, six.string_types):
                    raise CephClientTypeError(
                        name='caps',
                        actual=type(caps),
                        expected=six.string_types)
            if not isinstance(caps, list):
                caps = [caps]
            kwargs['caps'] = caps
        return self._request('auth add', **kwargs)

    def auth_get_or_create_key(
            self, entity, caps=None, body='json', timeout=None):
        """get, or add, key for <name> from system/caps pairs specified in thecommand.  If key already exists, any given caps must match the existing caps for that key.  """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        if caps is not None:
            if isinstance(caps, list):
                for item in caps:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='caps',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(caps, six.string_types):
                    raise CephClientTypeError(
                        name='caps',
                        actual=type(caps),
                        expected=six.string_types)
            if not isinstance(caps, list):
                caps = [caps]
            kwargs['caps'] = caps
        return self._request('auth get-or-create-key', **kwargs)

    def auth_get_or_create(self, entity, caps=None,
                           body='json', timeout=None):
        """add auth info for <entity> from input file, or random key if no inputgiven, and/or any caps specified in the command """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        if caps is not None:
            if isinstance(caps, list):
                for item in caps:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='caps',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(caps, six.string_types):
                    raise CephClientTypeError(
                        name='caps',
                        actual=type(caps),
                        expected=six.string_types)
            if not isinstance(caps, list):
                caps = [caps]
            kwargs['caps'] = caps
        return self._request('auth get-or-create', **kwargs)

    def fs_authorize(self, filesystem, entity, caps,
                     body='json', timeout=None):
        """add auth for <entity> to access file system <filesystem> based onfollowing directory and permissions pairs """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(filesystem, six.string_types):
            raise CephClientTypeError(
                name='filesystem',
                actual=type(filesystem),
                expected=six.string_types)

        kwargs['filesystem'] = filesystem
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        if isinstance(caps, list):
            for item in caps:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='caps',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(caps, six.string_types):
                raise CephClientTypeError(
                    name='caps',
                    actual=type(caps),
                    expected=six.string_types)

        if not isinstance(caps, list):
            caps = [caps]
        kwargs['caps'] = caps
        return self._request('fs authorize', **kwargs)

    def auth_caps(self, entity, caps, body='json', timeout=None):
        """update caps for <name> from caps specified in the command"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        if isinstance(caps, list):
            for item in caps:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='caps',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(caps, six.string_types):
                raise CephClientTypeError(
                    name='caps',
                    actual=type(caps),
                    expected=six.string_types)

        if not isinstance(caps, list):
            caps = [caps]
        kwargs['caps'] = caps
        return self._request('auth caps', **kwargs)

    def auth_del(self, entity, body='json', timeout=None):
        """delete all caps for <name>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        return self._request('auth del', **kwargs)

    def auth_rm(self, entity, body='json', timeout=None):
        """remove all caps for <name>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(entity, six.string_types):
            raise CephClientTypeError(
                name='entity',
                actual=type(entity),
                expected=six.string_types)

        kwargs['entity'] = entity
        return self._request('auth rm', **kwargs)

    def compact(self, body='json', timeout=None):
        """cause compaction of monitor's leveldb/rocksdb storage"""
        return self._request('compact', body=body, timeout=timeout)

    def scrub(self, body='json', timeout=None):
        """scrub the monitor stores"""
        return self._request('scrub', body=body, timeout=timeout)

    def fsid(self, body='json', timeout=None):
        """show cluster FSID/UUID"""
        return self._request('fsid', body=body, timeout=timeout)

    def log(self, logtext, body='json', timeout=None):
        """log supplied text to the monitor log"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(logtext, list):
            for item in logtext:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='logtext',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(logtext, six.string_types):
                raise CephClientTypeError(
                    name='logtext',
                    actual=type(logtext),
                    expected=six.string_types)

        if not isinstance(logtext, list):
            logtext = [logtext]
        kwargs['logtext'] = logtext
        return self._request('log', **kwargs)

    LOG_LAST_LEVEL_VALUES = ['debug', 'info', 'sec', 'warn', 'error']

    LOG_LAST_CHANNEL_VALUES = ['*', 'cluster', 'audit']

    def log_last(
            self, num=None, level=None, channel=None, body='json',
            timeout=None):
        """print last few lines of the cluster log"""
        kwargs = dict(body=body, timeout=timeout)
        if num is not None:
            if not isinstance(num, six.integer_types):
                raise CephClientTypeError(
                    name='num',
                    actual=type(num),
                    expected=int)
            if num < 1:
                raise CephClientValueOutOfBounds(
                    name='num',
                    actual=num,
                    min=1,
                    max='unlimited')
            kwargs['num'] = num
        if level is not None:
            if not isinstance(level, six.string_types):
                raise CephClientTypeError(
                    name='level',
                    actual=type(level),
                    expected=six.string_types)
            supported = CephClient.LOG_LAST_LEVEL_VALUES
            if level not in supported:
                raise CephClientInvalidChoice(
                    function='log_last',
                    option='level',
                    value=level,
                    supported=', '.join(supported))
            kwargs['level'] = level
        if channel is not None:
            if not isinstance(channel, six.string_types):
                raise CephClientTypeError(
                    name='channel',
                    actual=type(channel),
                    expected=six.string_types)
            supported = CephClient.LOG_LAST_CHANNEL_VALUES
            if channel not in supported:
                raise CephClientInvalidChoice(
                    function='log_last',
                    option='channel',
                    value=channel,
                    supported=', '.join(supported))
            kwargs['channel'] = channel
        return self._request('log last', **kwargs)

    def injectargs(self, injected_args, body='json', timeout=None):
        """inject config arguments into monitor"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(injected_args, list):
            for item in injected_args:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='injected_args',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(injected_args, six.string_types):
                raise CephClientTypeError(
                    name='injected_args',
                    actual=type(injected_args),
                    expected=six.string_types)

        if not isinstance(injected_args, list):
            injected_args = [injected_args]
        kwargs['injected_args'] = injected_args
        return self._request('injectargs', **kwargs)

    def status(self, body='json', timeout=None):
        """show cluster status"""
        return self._request('status', body=body, timeout=timeout)

    HEALTH_DETAIL_VALUES = ['detail']

    def health(self, detail=None, body='json', timeout=None):
        """show cluster health"""
        kwargs = dict(body=body, timeout=timeout)
        if detail is not None:
            if not isinstance(detail, six.string_types):
                raise CephClientTypeError(
                    name='detail',
                    actual=type(detail),
                    expected=six.string_types)
            supported = CephClient.HEALTH_DETAIL_VALUES
            if detail not in supported:
                raise CephClientInvalidChoice(
                    function='health',
                    option='detail',
                    value=detail,
                    supported=', '.join(supported))
            kwargs['detail'] = detail
        return self._request('health', **kwargs)

    def time_sync_status(self, body='json', timeout=None):
        """show time sync status"""
        return self._request('time-sync-status',
                             body=body, timeout=timeout)

    DF_DETAIL_VALUES = ['detail']

    def df(self, detail=None, body='json', timeout=None):
        """show cluster free space stats"""
        kwargs = dict(body=body, timeout=timeout)
        if detail is not None:
            if not isinstance(detail, six.string_types):
                raise CephClientTypeError(
                    name='detail',
                    actual=type(detail),
                    expected=six.string_types)
            supported = CephClient.DF_DETAIL_VALUES
            if detail not in supported:
                raise CephClientInvalidChoice(
                    function='df',
                    option='detail',
                    value=detail,
                    supported=', '.join(supported))
            kwargs['detail'] = detail
        return self._request('df', **kwargs)

    def report(self, tags=None, body='json', timeout=None):
        """report full status of cluster, optional title tag strings"""
        kwargs = dict(body=body, timeout=timeout)
        if tags is not None:
            if isinstance(tags, list):
                for item in tags:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='tags',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(tags, six.string_types):
                    raise CephClientTypeError(
                        name='tags',
                        actual=type(tags),
                        expected=six.string_types)
            if not isinstance(tags, list):
                tags = [tags]
            kwargs['tags'] = tags
        return self._request('report', **kwargs)

    def features(self, body='json', timeout=None):
        """report of connected features"""
        return self._request('features', body=body, timeout=timeout)

    def quorum_status(self, body='json', timeout=None):
        """report status of monitor quorum"""
        return self._request('quorum_status', body=body, timeout=timeout)

    def mon_status(self, body='json', timeout=None):
        """report status of monitors"""
        return self._request('mon_status', body=body, timeout=timeout)

    SYNC_FORCE_VALIDATE1_VALUES = ['--yes-i-really-mean-it']

    SYNC_FORCE_VALIDATE2_VALUES = ['--i-know-what-i-am-doing']

    def sync_force(
            self, validate1=None, validate2=None, body='json',
            timeout=None):
        """force sync of and clear monitor store"""
        kwargs = dict(body=body, timeout=timeout)
        if validate1 is not None:
            if not isinstance(validate1, six.string_types):
                raise CephClientTypeError(
                    name='validate1',
                    actual=type(validate1),
                    expected=six.string_types)
            supported = CephClient.SYNC_FORCE_VALIDATE1_VALUES
            if validate1 not in supported:
                raise CephClientInvalidChoice(
                    function='sync_force',
                    option='validate1',
                    value=validate1,
                    supported=', '.join(supported))
            kwargs['validate1'] = validate1
        if validate2 is not None:
            if not isinstance(validate2, six.string_types):
                raise CephClientTypeError(
                    name='validate2',
                    actual=type(validate2),
                    expected=six.string_types)
            supported = CephClient.SYNC_FORCE_VALIDATE2_VALUES
            if validate2 not in supported:
                raise CephClientInvalidChoice(
                    function='sync_force',
                    option='validate2',
                    value=validate2,
                    supported=', '.join(supported))
            kwargs['validate2'] = validate2
        return self._request('sync force', **kwargs)

    HEAP_HEAPCMD_VALUES = \
        ['dump', 'start_profiler', 'stop_profiler',
         'release', 'stats']

    def heap(self, heapcmd, body='json', timeout=None):
        """show heap usage info (available only if compiled with tcmalloc)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(heapcmd, six.string_types):
            raise CephClientTypeError(
                name='heapcmd',
                actual=type(heapcmd),
                expected=six.string_types)
        supported = CephClient.HEAP_HEAPCMD_VALUES
        if heapcmd not in supported:
            raise CephClientInvalidChoice(
                function='heap',
                option='heapcmd',
                value=heapcmd,
                supported=', '.join(supported))

        kwargs['heapcmd'] = heapcmd
        return self._request('heap', **kwargs)

    QUORUM_QUORUMCMD_VALUES = ['enter', 'exit']

    def quorum(self, quorumcmd, body='json', timeout=None):
        """enter or exit quorum"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(quorumcmd, six.string_types):
            raise CephClientTypeError(
                name='quorumcmd',
                actual=type(quorumcmd),
                expected=six.string_types)
        supported = CephClient.QUORUM_QUORUMCMD_VALUES
        if quorumcmd not in supported:
            raise CephClientInvalidChoice(
                function='quorum',
                option='quorumcmd',
                value=quorumcmd,
                supported=', '.join(supported))

        kwargs['quorumcmd'] = quorumcmd
        return self._request('quorum', **kwargs)

    def tell(self, target, args, body='json', timeout=None):
        """send a command to a specific daemon"""
        kwargs = dict(body=body, timeout=timeout)

        kwargs['target'] = target
        if isinstance(args, list):
            for item in args:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='args',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(args, six.string_types):
                raise CephClientTypeError(
                    name='args',
                    actual=type(args),
                    expected=six.string_types)

        if not isinstance(args, list):
            args = [args]
        kwargs['args'] = args
        return self._request('tell', **kwargs)

    def version(self, body='json', timeout=None):
        """show mon daemon version"""
        return self._request('version', body=body, timeout=timeout)

    NODE_LS__TYPE_VALUES = ['all', 'osd', 'mon', 'mds', 'mgr']

    def node_ls(self, _type=None, body='json', timeout=None):
        """list all nodes in cluster [type]"""
        kwargs = dict(body=body, timeout=timeout)
        if _type is not None:
            if not isinstance(_type, six.string_types):
                raise CephClientTypeError(
                    name='_type',
                    actual=type(_type),
                    expected=six.string_types)
            supported = CephClient.NODE_LS__TYPE_VALUES
            if _type not in supported:
                raise CephClientInvalidChoice(
                    function='node_ls',
                    option='_type',
                    value=_type,
                    supported=', '.join(supported))
            kwargs['type'] = _type
        return self._request('node ls', **kwargs)

    def mon_compact(self, body='json', timeout=None):
        """cause compaction of monitor's leveldb/rocksdb storage"""
        return self._request('mon compact', body=body, timeout=timeout)

    def mon_scrub(self, body='json', timeout=None):
        """scrub the monitor stores"""
        return self._request('mon scrub', body=body, timeout=timeout)

    MON_SYNC_FORCE_VALIDATE1_VALUES = ['--yes-i-really-mean-it']

    MON_SYNC_FORCE_VALIDATE2_VALUES = ['--i-know-what-i-am-doing']

    def mon_sync_force(
            self, validate1=None, validate2=None, body='json',
            timeout=None):
        """force sync of and clear monitor store"""
        kwargs = dict(body=body, timeout=timeout)
        if validate1 is not None:
            if not isinstance(validate1, six.string_types):
                raise CephClientTypeError(
                    name='validate1',
                    actual=type(validate1),
                    expected=six.string_types)
            supported = CephClient.MON_SYNC_FORCE_VALIDATE1_VALUES
            if validate1 not in supported:
                raise CephClientInvalidChoice(
                    function='mon_sync_force',
                    option='validate1',
                    value=validate1,
                    supported=', '.join(supported))
            kwargs['validate1'] = validate1
        if validate2 is not None:
            if not isinstance(validate2, six.string_types):
                raise CephClientTypeError(
                    name='validate2',
                    actual=type(validate2),
                    expected=six.string_types)
            supported = CephClient.MON_SYNC_FORCE_VALIDATE2_VALUES
            if validate2 not in supported:
                raise CephClientInvalidChoice(
                    function='mon_sync_force',
                    option='validate2',
                    value=validate2,
                    supported=', '.join(supported))
            kwargs['validate2'] = validate2
        return self._request('mon sync force', **kwargs)

    def mon_metadata(self, _id=None, body='json', timeout=None):
        """fetch metadata for mon <id>"""
        kwargs = dict(body=body, timeout=timeout)
        if _id is not None:
            if not isinstance(_id, six.string_types):
                raise CephClientTypeError(
                    name='_id',
                    actual=type(_id),
                    expected=six.string_types)
            kwargs['id'] = _id
        return self._request('mon metadata', **kwargs)

    def mon_count_metadata(self, _property, body='json', timeout=None):
        """count mons by metadata field property"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(_property, six.string_types):
            raise CephClientTypeError(
                name='_property',
                actual=type(_property),
                expected=six.string_types)

        kwargs['property'] = _property
        return self._request('mon count-metadata', **kwargs)

    def mon_versions(self, body='json', timeout=None):
        """check running versions of monitors"""
        return self._request('mon versions', body=body, timeout=timeout)

    def versions(self, body='json', timeout=None):
        """check running versions of ceph daemons"""
        return self._request('versions', body=body, timeout=timeout)

    def mds_stat(self, body='json', timeout=None):
        """show MDS status"""
        return self._request('mds stat', body=body, timeout=timeout)

    def mds_dump(self, epoch=None, body='json', timeout=None):
        """dump legacy MDS cluster info, optionally from epoch"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('mds dump', **kwargs)

    def fs_dump(self, epoch=None, body='json', timeout=None):
        """dump all CephFS status, optionally from epoch"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('fs dump', **kwargs)

    def mds_getmap(self, epoch=None, body='json', timeout=None):
        """get MDS map, optionally from epoch"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('mds getmap', **kwargs)

    def mds_metadata(self, who=None, body='json', timeout=None):
        """fetch metadata for mds <role>"""
        kwargs = dict(body=body, timeout=timeout)
        if who is not None:
            if not isinstance(who, six.string_types):
                raise CephClientTypeError(
                    name='who',
                    actual=type(who),
                    expected=six.string_types)
            kwargs['who'] = who
        return self._request('mds metadata', **kwargs)

    def mds_count_metadata(self, _property, body='json', timeout=None):
        """count MDSs by metadata field property"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(_property, six.string_types):
            raise CephClientTypeError(
                name='_property',
                actual=type(_property),
                expected=six.string_types)

        kwargs['property'] = _property
        return self._request('mds count-metadata', **kwargs)

    def mds_versions(self, body='json', timeout=None):
        """check running versions of MDSs"""
        return self._request('mds versions', body=body, timeout=timeout)

    def mds_tell(self, who, args, body='json', timeout=None):
        """send command to particular mds"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        if isinstance(args, list):
            for item in args:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='args',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(args, six.string_types):
                raise CephClientTypeError(
                    name='args',
                    actual=type(args),
                    expected=six.string_types)

        if not isinstance(args, list):
            args = [args]
        kwargs['args'] = args
        return self._request('mds tell', **kwargs)

    def mds_compat_show(self, body='json', timeout=None):
        """show mds compatibility settings"""
        return self._request('mds compat show', body=body, timeout=timeout)

    def mds_stop(self, role, body='json', timeout=None):
        """stop mds"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(role, six.string_types):
            raise CephClientTypeError(
                name='role',
                actual=type(role),
                expected=six.string_types)

        kwargs['role'] = role
        return self._request('mds stop', **kwargs)

    def mds_deactivate(self, role, body='json', timeout=None):
        """clean up specified MDS rank (use with `set max_mds` to shrink cluster)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(role, six.string_types):
            raise CephClientTypeError(
                name='role',
                actual=type(role),
                expected=six.string_types)

        kwargs['role'] = role
        return self._request('mds deactivate', **kwargs)

    def mds_set_max_mds(self, maxmds, body='json', timeout=None):
        """set max MDS index"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(maxmds, six.integer_types):
            raise CephClientTypeError(
                name='maxmds',
                actual=type(maxmds),
                expected=int)
        if maxmds < 0:
            raise CephClientValueOutOfBounds(
                name='maxmds',
                actual=maxmds,
                min=0,
                max='unlimited')

        kwargs['maxmds'] = maxmds
        return self._request('mds set_max_mds', **kwargs)

    MDS_SET_VAR_VALUES = \
        ['max_mds', 'max_file_size', 'inline_data',
         'allow_new_snaps', 'allow_multimds',
         'allow_multimds_snaps', 'allow_dirfrags']

    def mds_set(self, var, val, confirm=None, body='json', timeout=None):
        """set mds parameter <var> to <val>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(var, six.string_types):
            raise CephClientTypeError(
                name='var',
                actual=type(var),
                expected=six.string_types)
        supported = CephClient.MDS_SET_VAR_VALUES
        if var not in supported:
            raise CephClientInvalidChoice(
                function='mds_set',
                option='var',
                value=var,
                supported=', '.join(supported))

        kwargs['var'] = var
        if not isinstance(val, six.string_types):
            raise CephClientTypeError(
                name='val',
                actual=type(val),
                expected=six.string_types)

        kwargs['val'] = val
        if confirm is not None:
            if not isinstance(confirm, six.string_types):
                raise CephClientTypeError(
                    name='confirm',
                    actual=type(confirm),
                    expected=six.string_types)
            kwargs['confirm'] = confirm
        return self._request('mds set', **kwargs)

    def mds_set_state(self, gid, state, body='json', timeout=None):
        """set mds state of <gid> to <numeric-state>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(gid, six.integer_types):
            raise CephClientTypeError(
                name='gid',
                actual=type(gid),
                expected=int)
        if gid < 0:
            raise CephClientValueOutOfBounds(
                name='gid',
                actual=gid,
                min=0,
                max='unlimited')

        kwargs['gid'] = gid
        if not isinstance(state, six.integer_types):
            raise CephClientTypeError(
                name='state',
                actual=type(state),
                expected=int)
        if state < 0 or state > 20:
            raise CephClientValueOutOfBounds(
                name='state',
                actual=state,
                min=0,
                max=20)

        kwargs['state'] = state
        return self._request('mds set_state', **kwargs)

    def mds_fail(self, role_or_gid, body='json', timeout=None):
        """Mark MDS failed: trigger a failover if a standby is available"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(role_or_gid, six.string_types):
            raise CephClientTypeError(
                name='role_or_gid',
                actual=type(role_or_gid),
                expected=six.string_types)

        kwargs['role_or_gid'] = role_or_gid
        return self._request('mds fail', **kwargs)

    def mds_repaired(self, role, body='json', timeout=None):
        """mark a damaged MDS rank as no longer damaged"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(role, six.string_types):
            raise CephClientTypeError(
                name='role',
                actual=type(role),
                expected=six.string_types)

        kwargs['role'] = role
        return self._request('mds repaired', **kwargs)

    def mds_rm(self, gid, body='json', timeout=None):
        """remove nonactive mds"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(gid, six.integer_types):
            raise CephClientTypeError(
                name='gid',
                actual=type(gid),
                expected=int)
        if gid < 0:
            raise CephClientValueOutOfBounds(
                name='gid',
                actual=gid,
                min=0,
                max='unlimited')

        kwargs['gid'] = gid
        return self._request('mds rm', **kwargs)

    def mds_rmfailed(self, role, confirm=None, body='json', timeout=None):
        """remove failed mds"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(role, six.string_types):
            raise CephClientTypeError(
                name='role',
                actual=type(role),
                expected=six.string_types)

        kwargs['role'] = role
        if confirm is not None:
            if not isinstance(confirm, six.string_types):
                raise CephClientTypeError(
                    name='confirm',
                    actual=type(confirm),
                    expected=six.string_types)
            kwargs['confirm'] = confirm
        return self._request('mds rmfailed', **kwargs)

    def mds_cluster_down(self, body='json', timeout=None):
        """take MDS cluster down"""
        return self._request('mds cluster_down',
                             body=body, timeout=timeout)

    def mds_cluster_up(self, body='json', timeout=None):
        """bring MDS cluster up"""
        return self._request('mds cluster_up', body=body, timeout=timeout)

    def mds_compat_rm_compat(self, feature, body='json', timeout=None):
        """remove compatible feature"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(feature, six.integer_types):
            raise CephClientTypeError(
                name='feature',
                actual=type(feature),
                expected=int)
        if feature < 0:
            raise CephClientValueOutOfBounds(
                name='feature',
                actual=feature,
                min=0,
                max='unlimited')

        kwargs['feature'] = feature
        return self._request('mds compat rm_compat', **kwargs)

    def mds_compat_rm_incompat(self, feature, body='json', timeout=None):
        """remove incompatible feature"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(feature, six.integer_types):
            raise CephClientTypeError(
                name='feature',
                actual=type(feature),
                expected=int)
        if feature < 0:
            raise CephClientValueOutOfBounds(
                name='feature',
                actual=feature,
                min=0,
                max='unlimited')

        kwargs['feature'] = feature
        return self._request('mds compat rm_incompat', **kwargs)

    def mds_add_data_pool(self, pool, body='json', timeout=None):
        """add data pool <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('mds add_data_pool', **kwargs)

    def mds_rm_data_pool(self, pool, body='json', timeout=None):
        """remove data pool <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('mds rm_data_pool', **kwargs)

    def mds_remove_data_pool(self, pool, body='json', timeout=None):
        """remove data pool <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('mds remove_data_pool', **kwargs)

    MDS_NEWFS_SURE_VALUES = ['--yes-i-really-mean-it']

    def mds_newfs(self, metadata, data, sure=None,
                  body='json', timeout=None):
        """make new filesystem using pools <metadata> and <data>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(metadata, six.integer_types):
            raise CephClientTypeError(
                name='metadata',
                actual=type(metadata),
                expected=int)
        if metadata < 0:
            raise CephClientValueOutOfBounds(
                name='metadata',
                actual=metadata,
                min=0,
                max='unlimited')

        kwargs['metadata'] = metadata
        if not isinstance(data, six.integer_types):
            raise CephClientTypeError(
                name='data',
                actual=type(data),
                expected=int)
        if data < 0:
            raise CephClientValueOutOfBounds(
                name='data',
                actual=data,
                min=0,
                max='unlimited')

        kwargs['data'] = data
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.MDS_NEWFS_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='mds_newfs',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('mds newfs', **kwargs)

    FS_NEW_FORCE_VALUES = ['--force']

    FS_NEW_SURE_VALUES = ['--allow-dangerous-metadata-overlay']

    def fs_new(self, fs_name, metadata, data, force=None,
               sure=None, body='json', timeout=None):
        """make new filesystem using named pools <metadata> and <data>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(fs_name, six.string_types):
            raise CephClientTypeError(
                name='fs_name',
                actual=type(fs_name),
                expected=six.string_types)

        kwargs['fs_name'] = fs_name
        if not isinstance(metadata, six.string_types):
            raise CephClientTypeError(
                name='metadata',
                actual=type(metadata),
                expected=six.string_types)

        kwargs['metadata'] = metadata
        if not isinstance(data, six.string_types):
            raise CephClientTypeError(
                name='data',
                actual=type(data),
                expected=six.string_types)

        kwargs['data'] = data
        if force is not None:
            if not isinstance(force, six.string_types):
                raise CephClientTypeError(
                    name='force',
                    actual=type(force),
                    expected=six.string_types)
            supported = CephClient.FS_NEW_FORCE_VALUES
            if force not in supported:
                raise CephClientInvalidChoice(
                    function='fs_new',
                    option='force',
                    value=force,
                    supported=', '.join(supported))
            kwargs['force'] = force
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.FS_NEW_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='fs_new',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('fs new', **kwargs)

    FS_RM_SURE_VALUES = ['--yes-i-really-mean-it']

    def fs_rm(self, fs_name, sure=None, body='json', timeout=None):
        """disable the named filesystem"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(fs_name, six.string_types):
            raise CephClientTypeError(
                name='fs_name',
                actual=type(fs_name),
                expected=six.string_types)

        kwargs['fs_name'] = fs_name
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.FS_RM_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='fs_rm',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('fs rm', **kwargs)

    FS_RESET_SURE_VALUES = ['--yes-i-really-mean-it']

    def fs_reset(self, fs_name, sure=None, body='json', timeout=None):
        """disaster recovery only: reset to a single-MDS map"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(fs_name, six.string_types):
            raise CephClientTypeError(
                name='fs_name',
                actual=type(fs_name),
                expected=six.string_types)

        kwargs['fs_name'] = fs_name
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.FS_RESET_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='fs_reset',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('fs reset', **kwargs)

    def fs_ls(self, body='json', timeout=None):
        """list filesystems"""
        return self._request('fs ls', body=body, timeout=timeout)

    def fs_get(self, fs_name, body='json', timeout=None):
        """get info about one filesystem"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(fs_name, six.string_types):
            raise CephClientTypeError(
                name='fs_name',
                actual=type(fs_name),
                expected=six.string_types)

        kwargs['fs_name'] = fs_name
        return self._request('fs get', **kwargs)

    FS_SET_VAR_VALUES = \
        ['max_mds', 'max_file_size', 'allow_new_snaps',
         'inline_data', 'cluster_down',
         'allow_dirfrags', 'balancer',
         'standby_count_wanted', 'session_timeout',
         'session_autoclose', 'down', 'joinable',
         'min_compat_client']

    def fs_set(self, fs_name, var, val, confirm=None,
               body='json', timeout=None):
        """set fs parameter <var> to <val>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(fs_name, six.string_types):
            raise CephClientTypeError(
                name='fs_name',
                actual=type(fs_name),
                expected=six.string_types)

        kwargs['fs_name'] = fs_name
        if not isinstance(var, six.string_types):
            raise CephClientTypeError(
                name='var',
                actual=type(var),
                expected=six.string_types)
        supported = CephClient.FS_SET_VAR_VALUES
        if var not in supported:
            raise CephClientInvalidChoice(
                function='fs_set',
                option='var',
                value=var,
                supported=', '.join(supported))

        kwargs['var'] = var
        if not isinstance(val, six.string_types):
            raise CephClientTypeError(
                name='val',
                actual=type(val),
                expected=six.string_types)

        kwargs['val'] = val
        if confirm is not None:
            if not isinstance(confirm, six.string_types):
                raise CephClientTypeError(
                    name='confirm',
                    actual=type(confirm),
                    expected=six.string_types)
            kwargs['confirm'] = confirm
        return self._request('fs set', **kwargs)

    FS_FLAG_SET_FLAG_NAME_VALUES = ['enable_multiple']

    FS_FLAG_SET_CONFIRM_VALUES = ['--yes-i-really-mean-it']

    def fs_flag_set(self, flag_name, val, confirm=None,
                    body='json', timeout=None):
        """Set a global CephFS flag"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(flag_name, six.string_types):
            raise CephClientTypeError(
                name='flag_name',
                actual=type(flag_name),
                expected=six.string_types)
        supported = CephClient.FS_FLAG_SET_FLAG_NAME_VALUES
        if flag_name not in supported:
            raise CephClientInvalidChoice(
                function='fs_flag_set',
                option='flag_name',
                value=flag_name,
                supported=', '.join(supported))

        kwargs['flag_name'] = flag_name
        if not isinstance(val, six.string_types):
            raise CephClientTypeError(
                name='val',
                actual=type(val),
                expected=six.string_types)

        kwargs['val'] = val
        if confirm is not None:
            if not isinstance(confirm, six.string_types):
                raise CephClientTypeError(
                    name='confirm',
                    actual=type(confirm),
                    expected=six.string_types)
            supported = CephClient.FS_FLAG_SET_CONFIRM_VALUES
            if confirm not in supported:
                raise CephClientInvalidChoice(
                    function='fs_flag_set',
                    option='confirm',
                    value=confirm,
                    supported=', '.join(supported))
            kwargs['confirm'] = confirm
        return self._request('fs flag set', **kwargs)

    def fs_add_data_pool(self, fs_name, pool, body='json', timeout=None):
        """add data pool <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(fs_name, six.string_types):
            raise CephClientTypeError(
                name='fs_name',
                actual=type(fs_name),
                expected=six.string_types)

        kwargs['fs_name'] = fs_name
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('fs add_data_pool', **kwargs)

    def fs_rm_data_pool(self, fs_name, pool, body='json', timeout=None):
        """remove data pool <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(fs_name, six.string_types):
            raise CephClientTypeError(
                name='fs_name',
                actual=type(fs_name),
                expected=six.string_types)

        kwargs['fs_name'] = fs_name
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('fs rm_data_pool', **kwargs)

    def fs_set_default(self, fs_name, body='json', timeout=None):
        """set the default to the named filesystem"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(fs_name, six.string_types):
            raise CephClientTypeError(
                name='fs_name',
                actual=type(fs_name),
                expected=six.string_types)

        kwargs['fs_name'] = fs_name
        return self._request('fs set_default', **kwargs)

    def mon_dump(self, epoch=None, body='json', timeout=None):
        """dump formatted monmap (optionally from epoch)"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('mon dump', **kwargs)

    def mon_stat(self, body='json', timeout=None):
        """summarize monitor status"""
        return self._request('mon stat', body=body, timeout=timeout)

    def mon_getmap(self, epoch=None, body='json', timeout=None):
        """get monmap"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('mon getmap', **kwargs)

    def mon_add(self, name, addr, body='json', timeout=None):
        """add new monitor named <name> at <addr>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        try:
            ipaddress.ip_address(addr)
        except ValueError:
            raise CephClientInvalidIPAddr(
                name='addr',
                actual=addr)

        kwargs['addr'] = addr
        return self._request('mon add', **kwargs)

    def mon_rm(self, name, body='json', timeout=None):
        """remove monitor named <name>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        return self._request('mon rm', **kwargs)

    def mon_remove(self, name, body='json', timeout=None):
        """remove monitor named <name>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        return self._request('mon remove', **kwargs)

    MON_FEATURE_LS_WITH_VALUE_VALUES = ['--with-value']

    def mon_feature_ls(self, with_value=None, body='json', timeout=None):
        """list available mon map features to be set/unset"""
        kwargs = dict(body=body, timeout=timeout)
        if with_value is not None:
            if not isinstance(with_value, six.string_types):
                raise CephClientTypeError(
                    name='with_value',
                    actual=type(with_value),
                    expected=six.string_types)
            supported = CephClient.MON_FEATURE_LS_WITH_VALUE_VALUES
            if with_value not in supported:
                raise CephClientInvalidChoice(
                    function='mon_feature_ls',
                    option='with_value',
                    value=with_value,
                    supported=', '.join(supported))
            kwargs['with_value'] = with_value
        return self._request('mon feature ls', **kwargs)

    MON_FEATURE_SET_SURE_VALUES = ['--yes-i-really-mean-it']

    def mon_feature_set(self, feature_name, sure=None,
                        body='json', timeout=None):
        """set provided feature on mon map"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(feature_name, six.string_types):
            raise CephClientTypeError(
                name='feature_name',
                actual=type(feature_name),
                expected=six.string_types)

        kwargs['feature_name'] = feature_name
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.MON_FEATURE_SET_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='mon_feature_set',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('mon feature set', **kwargs)

    def osd_stat(self, body='json', timeout=None):
        """print summary of OSD map"""
        return self._request('osd stat', body=body, timeout=timeout)

    def osd_dump(self, epoch=None, body='json', timeout=None):
        """print summary of OSD map"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('osd dump', **kwargs)

    OSD_TREE_STATES_VALUES = ['up', 'down', 'in', 'out', 'destroyed']

    def osd_tree(self, epoch=None, states=None, body='json', timeout=None):
        """print OSD tree"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        if states is not None:
            if not isinstance(states, six.string_types):
                raise CephClientTypeError(
                    name='states',
                    actual=type(states),
                    expected=six.string_types)
            supported = CephClient.OSD_TREE_STATES_VALUES
            if states not in supported:
                raise CephClientInvalidChoice(
                    function='osd_tree',
                    option='states',
                    value=states,
                    supported=', '.join(supported))
            if not isinstance(states, list):
                states = [states]
            kwargs['states'] = states
        return self._request('osd tree', **kwargs)

    OSD_TREE_FROM_STATES_VALUES = [
        'up', 'down', 'in', 'out', 'destroyed']

    def osd_tree_from(
            self, bucket, epoch=None, states=None, body='json',
            timeout=None):
        """print OSD tree in bucket"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(bucket, six.string_types):
            raise CephClientTypeError(
                name='bucket',
                actual=type(bucket),
                expected=six.string_types)

        kwargs['bucket'] = bucket
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        if states is not None:
            if not isinstance(states, six.string_types):
                raise CephClientTypeError(
                    name='states',
                    actual=type(states),
                    expected=six.string_types)
            supported = CephClient.OSD_TREE_FROM_STATES_VALUES
            if states not in supported:
                raise CephClientInvalidChoice(
                    function='osd_tree_from',
                    option='states',
                    value=states,
                    supported=', '.join(supported))
            if not isinstance(states, list):
                states = [states]
            kwargs['states'] = states
        return self._request('osd tree-from', **kwargs)

    def osd_ls(self, epoch=None, body='json', timeout=None):
        """show all OSD ids"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('osd ls', **kwargs)

    def osd_getmap(self, epoch=None, body='json', timeout=None):
        """get OSD map"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('osd getmap', **kwargs)

    def osd_getcrushmap(self, epoch=None, body='json', timeout=None):
        """get CRUSH map"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('osd getcrushmap', **kwargs)

    def osd_getmaxosd(self, body='json', timeout=None):
        """show largest OSD id"""
        return self._request('osd getmaxosd', body=body, timeout=timeout)

    def osd_ls_tree(self, name, epoch=None, body='json', timeout=None):
        """show OSD ids under bucket <name> in the CRUSH map"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('osd ls-tree', **kwargs)

    def osd_find(self, _id, body='json', timeout=None):
        """find osd <id> in the CRUSH map and show its location"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        return self._request('osd find', **kwargs)

    def osd_metadata(self, _id=None, body='json', timeout=None):
        """fetch metadata for osd {id} (default all)"""
        kwargs = dict(body=body, timeout=timeout)
        if _id is not None:
            if isinstance(_id, six.integer_types):
                pass
            elif isinstance(_id, six.string_types):
                _id = _id.lower()
                prefix = 'osd.'
                if not _id.startswith(prefix):
                    raise CephClientInvalidOsdIdValue(osdid=_id)
                _id = int(_id[len(prefix):])
            else:
                raise CephClientTypeError(
                    name='_id',
                    actual=type(_id),
                    expected='int or string')
            kwargs['id'] = _id
        return self._request('osd metadata', **kwargs)

    def osd_count_metadata(self, _property, body='json', timeout=None):
        """count OSDs by metadata field property"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(_property, six.string_types):
            raise CephClientTypeError(
                name='_property',
                actual=type(_property),
                expected=six.string_types)

        kwargs['property'] = _property
        return self._request('osd count-metadata', **kwargs)

    def osd_versions(self, body='json', timeout=None):
        """check running versions of OSDs"""
        return self._request('osd versions', body=body, timeout=timeout)

    def osd_map(self, pool, _object, nspace=None,
                body='json', timeout=None):
        """find pg for <object> in <pool> with [namespace]"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool

        kwargs['object'] = _object
        if nspace is not None:
            if not isinstance(nspace, six.string_types):
                raise CephClientTypeError(
                    name='nspace',
                    actual=type(nspace),
                    expected=six.string_types)
            kwargs['nspace'] = nspace
        return self._request('osd map', **kwargs)

    def osd_lspools(self, auid=None, body='json', timeout=None):
        """list pools"""
        kwargs = dict(body=body, timeout=timeout)
        if auid is not None:
            if not isinstance(auid, six.integer_types):
                raise CephClientTypeError(
                    name='auid',
                    actual=type(auid),
                    expected=int)
            kwargs['auid'] = auid
        return self._request('osd lspools', **kwargs)

    def osd_crush_rule_list(self, body='json', timeout=None):
        """list crush rules"""
        return self._request('osd crush rule list',
                             body=body, timeout=timeout)

    def osd_crush_rule_ls(self, body='json', timeout=None):
        """list crush rules"""
        return self._request('osd crush rule ls',
                             body=body, timeout=timeout)

    def osd_crush_rule_ls_by_class(
            self, _class, body='json', timeout=None):
        """list all crush rules that reference the same <class>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(_class, six.string_types):
            raise CephClientTypeError(
                name='_class',
                actual=type(_class),
                expected=six.string_types)

        kwargs['class'] = _class
        return self._request('osd crush rule ls-by-class', **kwargs)

    def osd_crush_rule_dump(self, name=None, body='json', timeout=None):
        """dump crush rule <name> (default all)"""
        kwargs = dict(body=body, timeout=timeout)
        if name is not None:
            if not isinstance(name, six.string_types):
                raise CephClientTypeError(
                    name='name',
                    actual=type(name),
                    expected=six.string_types)
            kwargs['name'] = name
        return self._request('osd crush rule dump', **kwargs)

    def osd_crush_dump(self, body='json', timeout=None):
        """dump crush map"""
        return self._request('osd crush dump', body=body, timeout=timeout)

    def osd_crush_add_bucket(
            self, name, _type, args=None, body='json', timeout=None):
        """add no-parent (probably root) crush bucket <name> of type <type> tolocation <args> """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if not isinstance(_type, six.string_types):
            raise CephClientTypeError(
                name='_type',
                actual=type(_type),
                expected=six.string_types)

        kwargs['type'] = _type
        if args is not None:
            if isinstance(args, list):
                for item in args:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='args',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(args, six.string_types):
                    raise CephClientTypeError(
                        name='args',
                        actual=type(args),
                        expected=six.string_types)
            if not isinstance(args, list):
                args = [args]
            kwargs['args'] = args
        return self._request('osd crush add-bucket', **kwargs)

    def osd_crush_rename_bucket(
            self, srcname, dstname, body='json', timeout=None):
        """rename bucket <srcname> to <dstname>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(srcname, six.string_types):
            raise CephClientTypeError(
                name='srcname',
                actual=type(srcname),
                expected=six.string_types)

        kwargs['srcname'] = srcname
        if not isinstance(dstname, six.string_types):
            raise CephClientTypeError(
                name='dstname',
                actual=type(dstname),
                expected=six.string_types)

        kwargs['dstname'] = dstname
        return self._request('osd crush rename-bucket', **kwargs)

    def osd_crush_set(self, _id, weight, args, body='json', timeout=None):
        """update crushmap position and weight for <name> to <weight> withlocation <args> """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max='unlimited')

        kwargs['weight'] = weight
        if isinstance(args, list):
            for item in args:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='args',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(args, six.string_types):
                raise CephClientTypeError(
                    name='args',
                    actual=type(args),
                    expected=six.string_types)

        if not isinstance(args, list):
            args = [args]
        kwargs['args'] = args
        return self._request('osd crush set', **kwargs)

    def osd_crush_add(self, _id, weight, args, body='json', timeout=None):
        """add or update crushmap position and weight for <name> with <weight>and location <args> """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max='unlimited')

        kwargs['weight'] = weight
        if isinstance(args, list):
            for item in args:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='args',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(args, six.string_types):
                raise CephClientTypeError(
                    name='args',
                    actual=type(args),
                    expected=six.string_types)

        if not isinstance(args, list):
            args = [args]
        kwargs['args'] = args
        return self._request('osd crush add', **kwargs)

    def osd_crush_set_all_straw_buckets_to_straw2(
            self, body='json', timeout=None):
        """convert all CRUSH current straw buckets to use the straw2 algorithm"""
        return self._request(
            'osd crush set-all-straw-buckets-to-straw2', body=body,
            timeout=timeout)

    def osd_crush_set_device_class(
            self, _class, ids, body='json', timeout=None):
        """set the <class> of the osd(s) <id> [<id>...],or use <all|any> to setall.  """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(_class, six.string_types):
            raise CephClientTypeError(
                name='_class',
                actual=type(_class),
                expected=six.string_types)

        kwargs['class'] = _class
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd crush set-device-class', **kwargs)

    def osd_crush_rm_device_class(self, ids, body='json', timeout=None):
        """remove class of the osd(s) <id> [<id>...],or use <all|any> to removeall.  """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd crush rm-device-class', **kwargs)

    def osd_crush_class_rename(
            self, srcname, dstname, body='json', timeout=None):
        """rename crush device class <srcname> to <dstname>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(srcname, six.string_types):
            raise CephClientTypeError(
                name='srcname',
                actual=type(srcname),
                expected=six.string_types)

        kwargs['srcname'] = srcname
        if not isinstance(dstname, six.string_types):
            raise CephClientTypeError(
                name='dstname',
                actual=type(dstname),
                expected=six.string_types)

        kwargs['dstname'] = dstname
        return self._request('osd crush class rename', **kwargs)

    def osd_crush_create_or_move(
            self, _id, weight, args, body='json', timeout=None):
        """create entry or move existing entry for <name> <weight> at/to location<args> """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max='unlimited')

        kwargs['weight'] = weight
        if isinstance(args, list):
            for item in args:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='args',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(args, six.string_types):
                raise CephClientTypeError(
                    name='args',
                    actual=type(args),
                    expected=six.string_types)

        if not isinstance(args, list):
            args = [args]
        kwargs['args'] = args
        return self._request('osd crush create-or-move', **kwargs)

    def osd_crush_move(self, name, args, body='json', timeout=None):
        """move existing entry for <name> to location <args>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if isinstance(args, list):
            for item in args:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='args',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(args, six.string_types):
                raise CephClientTypeError(
                    name='args',
                    actual=type(args),
                    expected=six.string_types)

        if not isinstance(args, list):
            args = [args]
        kwargs['args'] = args
        return self._request('osd crush move', **kwargs)

    OSD_CRUSH_SWAP_BUCKET_FORCE_VALUES = ['--yes-i-really-mean-it']

    def osd_crush_swap_bucket(
            self, source, dest, force=None, body='json', timeout=None):
        """swap existing bucket contents from (orphan) bucket <source> and<target> """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(source, six.string_types):
            raise CephClientTypeError(
                name='source',
                actual=type(source),
                expected=six.string_types)

        kwargs['source'] = source
        if not isinstance(dest, six.string_types):
            raise CephClientTypeError(
                name='dest',
                actual=type(dest),
                expected=six.string_types)

        kwargs['dest'] = dest
        if force is not None:
            if not isinstance(force, six.string_types):
                raise CephClientTypeError(
                    name='force',
                    actual=type(force),
                    expected=six.string_types)
            supported = CephClient.OSD_CRUSH_SWAP_BUCKET_FORCE_VALUES
            if force not in supported:
                raise CephClientInvalidChoice(
                    function='osd_crush_swap_bucket',
                    option='force',
                    value=force,
                    supported=', '.join(supported))
            kwargs['force'] = force
        return self._request('osd crush swap-bucket', **kwargs)

    def osd_crush_link(self, name, args, body='json', timeout=None):
        """link existing entry for <name> under location <args>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if isinstance(args, list):
            for item in args:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='args',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(args, six.string_types):
                raise CephClientTypeError(
                    name='args',
                    actual=type(args),
                    expected=six.string_types)

        if not isinstance(args, list):
            args = [args]
        kwargs['args'] = args
        return self._request('osd crush link', **kwargs)

    def osd_crush_rm(self, name, ancestor=None, body='json', timeout=None):
        """remove <name> from crush map (everywhere, or just at <ancestor>)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if ancestor is not None:
            if not isinstance(ancestor, six.string_types):
                raise CephClientTypeError(
                    name='ancestor',
                    actual=type(ancestor),
                    expected=six.string_types)
            kwargs['ancestor'] = ancestor
        return self._request('osd crush rm', **kwargs)

    def osd_crush_remove(self, name, ancestor=None,
                         body='json', timeout=None):
        """remove <name> from crush map (everywhere, or just at <ancestor>)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if ancestor is not None:
            if not isinstance(ancestor, six.string_types):
                raise CephClientTypeError(
                    name='ancestor',
                    actual=type(ancestor),
                    expected=six.string_types)
            kwargs['ancestor'] = ancestor
        return self._request('osd crush remove', **kwargs)

    def osd_crush_unlink(self, name, ancestor=None,
                         body='json', timeout=None):
        """unlink <name> from crush map (everywhere, or just at <ancestor>)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if ancestor is not None:
            if not isinstance(ancestor, six.string_types):
                raise CephClientTypeError(
                    name='ancestor',
                    actual=type(ancestor),
                    expected=six.string_types)
            kwargs['ancestor'] = ancestor
        return self._request('osd crush unlink', **kwargs)

    def osd_crush_reweight_all(self, body='json', timeout=None):
        """recalculate the weights for the tree to ensure they sum correctly"""
        return self._request('osd crush reweight-all',
                             body=body, timeout=timeout)

    def osd_crush_reweight(self, name, weight, body='json', timeout=None):
        """change <name>'s weight to <weight> in crush map"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max='unlimited')

        kwargs['weight'] = weight
        return self._request('osd crush reweight', **kwargs)

    def osd_crush_reweight_subtree(
            self, name, weight, body='json', timeout=None):
        """change all leaf items beneath <name> to <weight> in crush map"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max='unlimited')

        kwargs['weight'] = weight
        return self._request('osd crush reweight-subtree', **kwargs)

    OSD_CRUSH_TUNABLES_PROFILE_VALUES = \
        ['legacy', 'argonaut', 'bobtail', 'firefly',
         'hammer', 'jewel', 'optimal', 'default']

    def osd_crush_tunables(self, profile, body='json', timeout=None):
        """set crush tunables values to <profile>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(profile, six.string_types):
            raise CephClientTypeError(
                name='profile',
                actual=type(profile),
                expected=six.string_types)
        supported = CephClient.OSD_CRUSH_TUNABLES_PROFILE_VALUES
        if profile not in supported:
            raise CephClientInvalidChoice(
                function='osd_crush_tunables',
                option='profile',
                value=profile,
                supported=', '.join(supported))

        kwargs['profile'] = profile
        return self._request('osd crush tunables', **kwargs)

    OSD_CRUSH_SET_TUNABLE_TUNABLE_VALUES = ['straw_calc_version']

    def osd_crush_set_tunable(
            self, tunable, value, body='json', timeout=None):
        """set crush tunable <tunable> to <value>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(tunable, six.string_types):
            raise CephClientTypeError(
                name='tunable',
                actual=type(tunable),
                expected=six.string_types)
        supported = CephClient.OSD_CRUSH_SET_TUNABLE_TUNABLE_VALUES
        if tunable not in supported:
            raise CephClientInvalidChoice(
                function='osd_crush_set_tunable',
                option='tunable',
                value=tunable,
                supported=', '.join(supported))

        kwargs['tunable'] = tunable
        if not isinstance(value, six.integer_types):
            raise CephClientTypeError(
                name='value',
                actual=type(value),
                expected=int)

        kwargs['value'] = value
        return self._request('osd crush set-tunable', **kwargs)

    OSD_CRUSH_GET_TUNABLE_TUNABLE_VALUES = ['straw_calc_version']

    def osd_crush_get_tunable(self, tunable, body='json', timeout=None):
        """get crush tunable <tunable>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(tunable, six.string_types):
            raise CephClientTypeError(
                name='tunable',
                actual=type(tunable),
                expected=six.string_types)
        supported = CephClient.OSD_CRUSH_GET_TUNABLE_TUNABLE_VALUES
        if tunable not in supported:
            raise CephClientInvalidChoice(
                function='osd_crush_get_tunable',
                option='tunable',
                value=tunable,
                supported=', '.join(supported))

        kwargs['tunable'] = tunable
        return self._request('osd crush get-tunable', **kwargs)

    def osd_crush_show_tunables(self, body='json', timeout=None):
        """show current crush tunables"""
        return self._request('osd crush show-tunables',
                             body=body, timeout=timeout)

    OSD_CRUSH_RULE_CREATE_SIMPLE_MODE_VALUES = ['firstn', 'indep']

    def osd_crush_rule_create_simple(
            self, name, root, _type, mode=None, body='json', timeout=None):
        """create crush rule <name> to start from <root>, replicate acrossbuckets of type <type>, using a choose mode of <firstn|indep> (default firstn; indep best for erasure pools) """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if not isinstance(root, six.string_types):
            raise CephClientTypeError(
                name='root',
                actual=type(root),
                expected=six.string_types)

        kwargs['root'] = root
        if not isinstance(_type, six.string_types):
            raise CephClientTypeError(
                name='_type',
                actual=type(_type),
                expected=six.string_types)

        kwargs['type'] = _type
        if mode is not None:
            if not isinstance(mode, six.string_types):
                raise CephClientTypeError(
                    name='mode',
                    actual=type(mode),
                    expected=six.string_types)
            supported = CephClient.OSD_CRUSH_RULE_CREATE_SIMPLE_MODE_VALUES
            if mode not in supported:
                raise CephClientInvalidChoice(
                    function='osd_crush_rule_create_simple',
                    option='mode',
                    value=mode,
                    supported=', '.join(supported))
            kwargs['mode'] = mode
        return self._request('osd crush rule create-simple', **kwargs)

    def osd_crush_rule_create_replicated(
            self, name, root, _type, _class=None, body='json',
            timeout=None):
        """create crush rule <name> for replicated pool to start from <root>,replicate across buckets of type <type>, using a choose mode of <firstn|indep> (default firstn; indep best for erasure pools) """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if not isinstance(root, six.string_types):
            raise CephClientTypeError(
                name='root',
                actual=type(root),
                expected=six.string_types)

        kwargs['root'] = root
        if not isinstance(_type, six.string_types):
            raise CephClientTypeError(
                name='_type',
                actual=type(_type),
                expected=six.string_types)

        kwargs['type'] = _type
        if _class is not None:
            if not isinstance(_class, six.string_types):
                raise CephClientTypeError(
                    name='_class',
                    actual=type(_class),
                    expected=six.string_types)
            kwargs['class'] = _class
        return self._request('osd crush rule create-replicated', **kwargs)

    def osd_crush_rule_create_erasure(
            self, name, profile=None, body='json', timeout=None):
        """create crush rule <name> for erasure coded pool created with <profile>(default default) """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if profile is not None:
            if not isinstance(profile, six.string_types):
                raise CephClientTypeError(
                    name='profile',
                    actual=type(profile),
                    expected=six.string_types)
            kwargs['profile'] = profile
        return self._request('osd crush rule create-erasure', **kwargs)

    def osd_crush_rule_rm(self, name, body='json', timeout=None):
        """remove crush rule <name>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        return self._request('osd crush rule rm', **kwargs)

    def osd_crush_rule_rename(
            self, srcname, dstname, body='json', timeout=None):
        """rename crush rule <srcname> to <dstname>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(srcname, six.string_types):
            raise CephClientTypeError(
                name='srcname',
                actual=type(srcname),
                expected=six.string_types)

        kwargs['srcname'] = srcname
        if not isinstance(dstname, six.string_types):
            raise CephClientTypeError(
                name='dstname',
                actual=type(dstname),
                expected=six.string_types)

        kwargs['dstname'] = dstname
        return self._request('osd crush rule rename', **kwargs)

    OSD_CRUSH_TREE_SHADOW_VALUES = ['--show-shadow']

    def osd_crush_tree(self, shadow=None, body='json', timeout=None):
        """dump crush buckets and items in a tree view"""
        kwargs = dict(body=body, timeout=timeout)
        if shadow is not None:
            if not isinstance(shadow, six.string_types):
                raise CephClientTypeError(
                    name='shadow',
                    actual=type(shadow),
                    expected=six.string_types)
            supported = CephClient.OSD_CRUSH_TREE_SHADOW_VALUES
            if shadow not in supported:
                raise CephClientInvalidChoice(
                    function='osd_crush_tree',
                    option='shadow',
                    value=shadow,
                    supported=', '.join(supported))
            kwargs['shadow'] = shadow
        return self._request('osd crush tree', **kwargs)

    def osd_crush_ls(self, node, body='json', timeout=None):
        """list items beneath a node in the CRUSH tree"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(node, six.string_types):
            raise CephClientTypeError(
                name='node',
                actual=type(node),
                expected=six.string_types)

        kwargs['node'] = node
        return self._request('osd crush ls', **kwargs)

    def osd_crush_class_ls(self, body='json', timeout=None):
        """list all crush device classes"""
        return self._request('osd crush class ls',
                             body=body, timeout=timeout)

    def osd_crush_class_ls_osd(self, _class, body='json', timeout=None):
        """list all osds belonging to the specific <class>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(_class, six.string_types):
            raise CephClientTypeError(
                name='_class',
                actual=type(_class),
                expected=six.string_types)

        kwargs['class'] = _class
        return self._request('osd crush class ls-osd', **kwargs)

    def osd_crush_weight_set_ls(self, body='json', timeout=None):
        """list crush weight sets"""
        return self._request('osd crush weight-set ls',
                             body=body, timeout=timeout)

    def osd_crush_weight_set_dump(self, body='json', timeout=None):
        """dump crush weight sets"""
        return self._request('osd crush weight-set dump',
                             body=body, timeout=timeout)

    def osd_crush_weight_set_create_compat(
            self, body='json', timeout=None):
        """create a default backward-compatible weight-set"""
        return self._request(
            'osd crush weight-set create-compat', body=body,
            timeout=timeout)

    OSD_CRUSH_WEIGHT_SET_CREATE_MODE_VALUES = ['flat', 'positional']

    def osd_crush_weight_set_create(
            self, pool, mode, body='json', timeout=None):
        """create a weight-set for a given pool"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(mode, six.string_types):
            raise CephClientTypeError(
                name='mode',
                actual=type(mode),
                expected=six.string_types)
        supported = CephClient.OSD_CRUSH_WEIGHT_SET_CREATE_MODE_VALUES
        if mode not in supported:
            raise CephClientInvalidChoice(
                function='osd_crush_weight_set_create',
                option='mode',
                value=mode,
                supported=', '.join(supported))

        kwargs['mode'] = mode
        return self._request('osd crush weight-set create', **kwargs)

    def osd_crush_weight_set_rm(self, pool, body='json', timeout=None):
        """remove the weight-set for a given pool"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('osd crush weight-set rm', **kwargs)

    def osd_crush_weight_set_rm_compat(self, body='json', timeout=None):
        """remove the backward-compatible weight-set"""
        return self._request(
            'osd crush weight-set rm-compat', body=body, timeout=timeout)

    def osd_crush_weight_set_reweight(
            self, pool, item, weight, body='json', timeout=None):
        """set weight for an item (bucket or osd) in a pool's weight-set"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(item, six.string_types):
            raise CephClientTypeError(
                name='item',
                actual=type(item),
                expected=six.string_types)

        kwargs['item'] = item
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max='unlimited')

        if not isinstance(weight, list):
            weight = [weight]
        kwargs['weight'] = weight
        return self._request('osd crush weight-set reweight', **kwargs)

    def osd_crush_weight_set_reweight_compat(
            self, item, weight, body='json', timeout=None):
        """set weight for an item (bucket or osd) in the backward-compatibleweight-set """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(item, six.string_types):
            raise CephClientTypeError(
                name='item',
                actual=type(item),
                expected=six.string_types)

        kwargs['item'] = item
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max='unlimited')

        if not isinstance(weight, list):
            weight = [weight]
        kwargs['weight'] = weight
        return self._request(
            'osd crush weight-set reweight-compat', **kwargs)

    def osd_setmaxosd(self, newmax, body='json', timeout=None):
        """set new maximum osd value"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(newmax, six.integer_types):
            raise CephClientTypeError(
                name='newmax',
                actual=type(newmax),
                expected=int)
        if newmax < 0:
            raise CephClientValueOutOfBounds(
                name='newmax',
                actual=newmax,
                min=0,
                max='unlimited')

        kwargs['newmax'] = newmax
        return self._request('osd setmaxosd', **kwargs)

    def osd_set_full_ratio(self, ratio, body='json', timeout=None):
        """set usage ratio at which OSDs are marked full"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(ratio, (six.integer_types, float)):
            raise CephClientTypeError(
                name='ratio',
                actual=type(ratio),
                expected=int)
        if ratio < 0.0 or ratio > 1.0:
            raise CephClientValueOutOfBounds(
                name='ratio',
                actual=ratio,
                min=0.0,
                max=1.0)

        kwargs['ratio'] = ratio
        return self._request('osd set-full-ratio', **kwargs)

    def osd_set_backfillfull_ratio(self, ratio, body='json', timeout=None):
        """set usage ratio at which OSDs are marked too full to backfill"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(ratio, (six.integer_types, float)):
            raise CephClientTypeError(
                name='ratio',
                actual=type(ratio),
                expected=int)
        if ratio < 0.0 or ratio > 1.0:
            raise CephClientValueOutOfBounds(
                name='ratio',
                actual=ratio,
                min=0.0,
                max=1.0)

        kwargs['ratio'] = ratio
        return self._request('osd set-backfillfull-ratio', **kwargs)

    def osd_set_nearfull_ratio(self, ratio, body='json', timeout=None):
        """set usage ratio at which OSDs are marked near-full"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(ratio, (six.integer_types, float)):
            raise CephClientTypeError(
                name='ratio',
                actual=type(ratio),
                expected=int)
        if ratio < 0.0 or ratio > 1.0:
            raise CephClientValueOutOfBounds(
                name='ratio',
                actual=ratio,
                min=0.0,
                max=1.0)

        kwargs['ratio'] = ratio
        return self._request('osd set-nearfull-ratio', **kwargs)

    def osd_get_require_min_compat_client(self, body='json', timeout=None):
        """get the minimum client version we will maintain compatibility with"""
        return self._request(
            'osd get-require-min-compat-client', body=body,
            timeout=timeout)

    OSD_SET_REQUIRE_MIN_COMPAT_CLIENT_SURE_VALUES = [
        '--yes-i-really-mean-it']

    def osd_set_require_min_compat_client(
            self, version, sure=None, body='json', timeout=None):
        """set the minimum client version we will maintain compatibility with"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(version, six.string_types):
            raise CephClientTypeError(
                name='version',
                actual=type(version),
                expected=six.string_types)

        kwargs['version'] = version
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_SET_REQUIRE_MIN_COMPAT_CLIENT_SURE_VALUES  # noqa E501
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_set_require_min_compat_client',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd set-require-min-compat-client', **kwargs)

    def osd_pause(self, body='json', timeout=None):
        """pause osd"""
        return self._request('osd pause', body=body, timeout=timeout)

    def osd_unpause(self, body='json', timeout=None):
        """unpause osd"""
        return self._request('osd unpause', body=body, timeout=timeout)

    def osd_erasure_code_profile_set(
            self, name, profile=None, body='json', timeout=None):
        """create erasure code profile <name> with [<key[=value]> ...] pairs. Adda --force at the end to override an existing profile (VERY DANGEROUS) """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if profile is not None:
            if isinstance(profile, list):
                for item in profile:
                    if not isinstance(item, six.string_types):
                        raise CephClientTypeError(
                            name='profile',
                            actual=item,
                            expected='list of strings')
            else:
                if not isinstance(profile, six.string_types):
                    raise CephClientTypeError(
                        name='profile',
                        actual=type(profile),
                        expected=six.string_types)
            if not isinstance(profile, list):
                profile = [profile]
            kwargs['profile'] = profile
        return self._request('osd erasure-code-profile set', **kwargs)

    def osd_erasure_code_profile_get(
            self, name, body='json', timeout=None):
        """get erasure code profile <name>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        return self._request('osd erasure-code-profile get', **kwargs)

    def osd_erasure_code_profile_rm(self, name, body='json', timeout=None):
        """remove erasure code profile <name>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        return self._request('osd erasure-code-profile rm', **kwargs)

    def osd_erasure_code_profile_ls(self, body='json', timeout=None):
        """list all erasure code profiles"""
        return self._request(
            'osd erasure-code-profile ls', body=body, timeout=timeout)

    OSD_SET_KEY_VALUES = \
        ['full', 'pause', 'noup', 'nodown', 'noout',
         'noin', 'nobackfill', 'norebalance',
         'norecover', 'noscrub', 'nodeep-scrub',
         'notieragent', 'nosnaptrim', 'sortbitwise',
         'recovery_deletes', 'require_jewel_osds',
         'require_kraken_osds']

    OSD_SET_SURE_VALUES = ['--yes-i-really-mean-it']

    def osd_set(self, key, sure=None, body='json', timeout=None):
        """set <key>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)
        supported = CephClient.OSD_SET_KEY_VALUES
        if key not in supported:
            raise CephClientInvalidChoice(
                function='osd_set',
                option='key',
                value=key,
                supported=', '.join(supported))

        kwargs['key'] = key
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_SET_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_set',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd set', **kwargs)

    OSD_UNSET_KEY_VALUES = \
        ['full', 'pause', 'noup', 'nodown', 'noout',
         'noin', 'nobackfill', 'norebalance',
         'norecover', 'noscrub', 'nodeep-scrub',
         'notieragent', 'nosnaptrim']

    def osd_unset(self, key, body='json', timeout=None):
        """unset <key>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)
        supported = CephClient.OSD_UNSET_KEY_VALUES
        if key not in supported:
            raise CephClientInvalidChoice(
                function='osd_unset',
                option='key',
                value=key,
                supported=', '.join(supported))

        kwargs['key'] = key
        return self._request('osd unset', **kwargs)

    OSD_REQUIRE_OSD_RELEASE_RELEASE_VALUES = ['luminous', 'mimic']

    OSD_REQUIRE_OSD_RELEASE_SURE_VALUES = ['--yes-i-really-mean-it']

    def osd_require_osd_release(
            self, release, sure=None, body='json', timeout=None):
        """set the minimum allowed OSD release to participate in the cluster"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(release, six.string_types):
            raise CephClientTypeError(
                name='release',
                actual=type(release),
                expected=six.string_types)
        supported = CephClient.OSD_REQUIRE_OSD_RELEASE_RELEASE_VALUES
        if release not in supported:
            raise CephClientInvalidChoice(
                function='osd_require_osd_release',
                option='release',
                value=release,
                supported=', '.join(supported))

        kwargs['release'] = release
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_REQUIRE_OSD_RELEASE_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_require_osd_release',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd require-osd-release', **kwargs)

    def osd_down(self, ids, body='json', timeout=None):
        """set osd(s) <id> [<id>...] down, or use <any|all> to set all osds down"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd down', **kwargs)

    def osd_out(self, ids, body='json', timeout=None):
        """set osd(s) <id> [<id>...] out, or use <any|all> to set all osds out"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd out', **kwargs)

    def osd_in(self, ids, body='json', timeout=None):
        """set osd(s) <id> [<id>...] in, can use <any|all> to automatically setall previously out osds in """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd in', **kwargs)

    def osd_rm(self, ids, body='json', timeout=None):
        """remove osd(s) <id> [<id>...], or use <any|all> to remove all osds"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd rm', **kwargs)

    def osd_add_noup(self, ids, body='json', timeout=None):
        """mark osd(s) <id> [<id>...] as noup, or use <all|any> to mark all osdsas noup """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd add-noup', **kwargs)

    def osd_add_nodown(self, ids, body='json', timeout=None):
        """mark osd(s) <id> [<id>...] as nodown, or use <all|any> to mark allosds as nodown """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd add-nodown', **kwargs)

    def osd_add_noin(self, ids, body='json', timeout=None):
        """mark osd(s) <id> [<id>...] as noin, or use <all|any> to mark all osdsas noin """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd add-noin', **kwargs)

    def osd_add_noout(self, ids, body='json', timeout=None):
        """mark osd(s) <id> [<id>...] as noout, or use <all|any> to mark all osdsas noout """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd add-noout', **kwargs)

    def osd_rm_noup(self, ids, body='json', timeout=None):
        """allow osd(s) <id> [<id>...] to be marked up (if they are currentlymarked as noup), can use <all|any> to automatically filter out all noup osds """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd rm-noup', **kwargs)

    def osd_rm_nodown(self, ids, body='json', timeout=None):
        """allow osd(s) <id> [<id>...] to be marked down (if they are currentlymarked as nodown), can use <all|any> to automatically filter out all nodown osds """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd rm-nodown', **kwargs)

    def osd_rm_noin(self, ids, body='json', timeout=None):
        """allow osd(s) <id> [<id>...] to be marked in (if they are currentlymarked as noin), can use <all|any> to automatically filter out all noin osds """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd rm-noin', **kwargs)

    def osd_rm_noout(self, ids, body='json', timeout=None):
        """allow osd(s) <id> [<id>...] to be marked out (if they are currentlymarked as noout), can use <all|any> to automatically filter out all noout osds """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(ids, list):
            for item in ids:
                if not isinstance(item, six.string_types):
                    raise CephClientTypeError(
                        name='ids',
                        actual=item,
                        expected='list of strings')
        else:
            if not isinstance(ids, six.string_types):
                raise CephClientTypeError(
                    name='ids',
                    actual=type(ids),
                    expected=six.string_types)

        if not isinstance(ids, list):
            ids = [ids]
        kwargs['ids'] = ids
        return self._request('osd rm-noout', **kwargs)

    def osd_reweight(self, _id, weight, body='json', timeout=None):
        """reweight osd to 0.0 < <weight> < 1.0"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0 or weight > 1.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max=1.0)

        kwargs['weight'] = weight
        return self._request('osd reweight', **kwargs)

    def osd_reweightn(self, weights, body='json', timeout=None):
        """reweight osds with {<id>: <weight>,...})"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(weights, six.string_types):
            raise CephClientTypeError(
                name='weights',
                actual=type(weights),
                expected=six.string_types)

        kwargs['weights'] = weights
        return self._request('osd reweightn', **kwargs)

    OSD_FORCE_CREATE_PG_SURE_VALUES = ['--yes-i-really-mean-it']

    def osd_force_create_pg(self, pgid, sure=None,
                            body='json', timeout=None):
        """force creation of pg <pgid>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_FORCE_CREATE_PG_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_force_create_pg',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd force-create-pg', **kwargs)

    def osd_pg_temp(self, pgid, _id=None, body='json', timeout=None):
        """set pg_temp mapping pgid:[<id> [<id>...]] (developers only)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        if _id is not None:
            if isinstance(_id, six.integer_types):
                pass
            elif isinstance(_id, six.string_types):
                _id = _id.lower()
                prefix = 'osd.'
                if not _id.startswith(prefix):
                    raise CephClientInvalidOsdIdValue(osdid=_id)
                _id = int(_id[len(prefix):])
            else:
                raise CephClientTypeError(
                    name='_id',
                    actual=type(_id),
                    expected='int or string')
            if not isinstance(_id, list):
                _id = [_id]
            kwargs['id'] = _id
        return self._request('osd pg-temp', **kwargs)

    def osd_pg_upmap(self, pgid, _id, body='json', timeout=None):
        """set pg_upmap mapping <pgid>:[<id> [<id>...]] (developers only)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        if not isinstance(_id, list):
            _id = [_id]
        kwargs['id'] = _id
        return self._request('osd pg-upmap', **kwargs)

    def osd_rm_pg_upmap(self, pgid, body='json', timeout=None):
        """clear pg_upmap mapping for <pgid> (developers only)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        return self._request('osd rm-pg-upmap', **kwargs)

    def osd_pg_upmap_items(self, pgid, _id, body='json', timeout=None):
        """set pg_upmap_items mapping <pgid>:{<id> to <id>, [...]} (developersonly) """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        if not isinstance(_id, list):
            _id = [_id]
        kwargs['id'] = _id
        return self._request('osd pg-upmap-items', **kwargs)

    def osd_rm_pg_upmap_items(self, pgid, body='json', timeout=None):
        """clear pg_upmap_items mapping for <pgid> (developers only)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        return self._request('osd rm-pg-upmap-items', **kwargs)

    def osd_primary_temp(self, pgid, _id, body='json', timeout=None):
        """set primary_temp mapping pgid:<id>|-1 (developers only)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pgid, six.string_types):
            raise CephClientTypeError(
                name='pgid',
                actual=type(pgid),
                expected=six.string_types)
        if not re.match(r'[0-9]+\.[0-9a-fA-F]+', pgid):
            raise CephClientInvalidPgid(
                name='pgid',
                actual=pgid)

        kwargs['pgid'] = pgid
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        return self._request('osd primary-temp', **kwargs)

    def osd_primary_affinity(self, _id, weight, body='json', timeout=None):
        """adjust osd primary-affinity from 0.0 <= <weight> <= 1.0"""
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if not isinstance(weight, (six.integer_types, float)):
            raise CephClientTypeError(
                name='weight',
                actual=type(weight),
                expected=int)
        if weight < 0.0 or weight > 1.0:
            raise CephClientValueOutOfBounds(
                name='weight',
                actual=weight,
                min=0.0,
                max=1.0)

        kwargs['weight'] = weight
        return self._request('osd primary-affinity', **kwargs)

    OSD_DESTROY_SURE_VALUES = ['--yes-i-really-mean-it']

    def osd_destroy(self, _id, sure=None, body='json', timeout=None):
        """mark osd as being destroyed. Keeps the ID intact (allowing reuse), butremoves cephx keys, config-key data and lockbox keys, rendering data permanently unreadable.  """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_DESTROY_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_destroy',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd destroy', **kwargs)

    OSD_PURGE_NEW_SURE_VALUES = ['--yes-i-really-mean-it']

    def osd_purge_new(self, _id, sure=None, body='json', timeout=None):
        """purge all traces of an OSD that was partially created but neverstarted """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_PURGE_NEW_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_purge_new',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd purge-new', **kwargs)

    OSD_PURGE_SURE_VALUES = ['--yes-i-really-mean-it']

    def osd_purge(self, _id, sure=None, body='json', timeout=None):
        """purge all osd data from the monitors. Combines `osd destroy`, `osdrm`, and `osd crush rm`.  """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_PURGE_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_purge',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd purge', **kwargs)

    OSD_LOST_SURE_VALUES = ['--yes-i-really-mean-it']

    def osd_lost(self, _id, sure=None, body='json', timeout=None):
        """mark osd as permanently lost. THIS DESTROYS DATA IF NO MORE REPLICAS EXIST, BE CAREFUL """
        kwargs = dict(body=body, timeout=timeout)
        if isinstance(_id, six.integer_types):
            pass
        elif isinstance(_id, six.string_types):
            _id = _id.lower()
            prefix = 'osd.'
            if not _id.startswith(prefix):
                raise CephClientInvalidOsdIdValue(osdid=_id)
            _id = int(_id[len(prefix):])
        else:
            raise CephClientTypeError(
                name='_id',
                actual=type(_id),
                expected='int or string')

        kwargs['id'] = _id
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_LOST_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_lost',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd lost', **kwargs)

    def osd_create(self, uuid=None, _id=None, body='json', timeout=None):
        """create new osd (with optional UUID and ID)"""
        kwargs = dict(body=body, timeout=timeout)
        if uuid is not None:

            kwargs['uuid'] = uuid
        if _id is not None:
            if isinstance(_id, six.integer_types):
                pass
            elif isinstance(_id, six.string_types):
                _id = _id.lower()
                prefix = 'osd.'
                if not _id.startswith(prefix):
                    raise CephClientInvalidOsdIdValue(osdid=_id)
                _id = int(_id[len(prefix):])
            else:
                raise CephClientTypeError(
                    name='_id',
                    actual=type(_id),
                    expected='int or string')
            kwargs['id'] = _id
        return self._request('osd create', **kwargs)

    def osd_new(self, uuid, _id=None, body='json', timeout=None):
        """Create a new OSD. If supplied, the `id` to be replaced needs to existand have been previously destroyed. Reads secrets from JSON file via `-i <file>` (see man page).  """
        kwargs = dict(body=body, timeout=timeout)
        kwargs['uuid'] = uuid
        if _id is not None:
            if isinstance(_id, six.integer_types):
                pass
            elif isinstance(_id, six.string_types):
                _id = _id.lower()
                prefix = 'osd.'
                if not _id.startswith(prefix):
                    raise CephClientInvalidOsdIdValue(osdid=_id)
                _id = int(_id[len(prefix):])
            else:
                raise CephClientTypeError(
                    name='_id',
                    actual=type(_id),
                    expected='int or string')
            kwargs['id'] = _id
        return self._request('osd new', **kwargs)

    OSD_BLACKLIST_BLACKLISTOP_VALUES = ['add', 'rm']

    def osd_blacklist(
            self, blacklistop, addr, expire=None, body='json',
            timeout=None):
        """add (optionally until <expire> seconds from now) or remove <addr> fromblacklist """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(blacklistop, six.string_types):
            raise CephClientTypeError(
                name='blacklistop',
                actual=type(blacklistop),
                expected=six.string_types)
        supported = CephClient.OSD_BLACKLIST_BLACKLISTOP_VALUES
        if blacklistop not in supported:
            raise CephClientInvalidChoice(
                function='osd_blacklist',
                option='blacklistop',
                value=blacklistop,
                supported=', '.join(supported))

        kwargs['blacklistop'] = blacklistop

        kwargs['addr'] = addr
        if expire is not None:
            if not isinstance(expire, (six.integer_types, float)):
                raise CephClientTypeError(
                    name='expire',
                    actual=type(expire),
                    expected=int)
            if expire < 0.0:
                raise CephClientValueOutOfBounds(
                    name='expire',
                    actual=expire,
                    min=0.0,
                    max='unlimited')
            kwargs['expire'] = expire
        return self._request('osd blacklist', **kwargs)

    def osd_blacklist_ls(self, body='json', timeout=None):
        """show blacklisted clients"""
        return self._request('osd blacklist ls',
                             body=body, timeout=timeout)

    def osd_blacklist_clear(self, body='json', timeout=None):
        """clear all blacklisted clients"""
        return self._request('osd blacklist clear',
                             body=body, timeout=timeout)

    def osd_pool_mksnap(self, pool, snap, body='json', timeout=None):
        """make snapshot <snap> in <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(snap, six.string_types):
            raise CephClientTypeError(
                name='snap',
                actual=type(snap),
                expected=six.string_types)

        kwargs['snap'] = snap
        return self._request('osd pool mksnap', **kwargs)

    def osd_pool_rmsnap(self, pool, snap, body='json', timeout=None):
        """remove snapshot <snap> from <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(snap, six.string_types):
            raise CephClientTypeError(
                name='snap',
                actual=type(snap),
                expected=six.string_types)

        kwargs['snap'] = snap
        return self._request('osd pool rmsnap', **kwargs)

    OSD_POOL_LS_DETAIL_VALUES = ['detail']

    def osd_pool_ls(self, detail=None, body='json', timeout=None):
        """list pools"""
        kwargs = dict(body=body, timeout=timeout)
        if detail is not None:
            if not isinstance(detail, six.string_types):
                raise CephClientTypeError(
                    name='detail',
                    actual=type(detail),
                    expected=six.string_types)
            supported = CephClient.OSD_POOL_LS_DETAIL_VALUES
            if detail not in supported:
                raise CephClientInvalidChoice(
                    function='osd_pool_ls',
                    option='detail',
                    value=detail,
                    supported=', '.join(supported))
            kwargs['detail'] = detail
        return self._request('osd pool ls', **kwargs)

    OSD_POOL_CREATE_POOL_TYPE_VALUES = ['replicated', 'erasure']

    def osd_pool_create(
            self, pool, pg_num, pgp_num=None, pool_type=None,
            erasure_code_profile=None, rule=None,
            expected_num_objects=None, body='json', timeout=None):
        """create pool"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(pg_num, six.integer_types):
            raise CephClientTypeError(
                name='pg_num',
                actual=type(pg_num),
                expected=int)
        if pg_num < 0:
            raise CephClientValueOutOfBounds(
                name='pg_num',
                actual=pg_num,
                min=0,
                max='unlimited')

        kwargs['pg_num'] = pg_num
        if pgp_num is not None:
            if not isinstance(pgp_num, six.integer_types):
                raise CephClientTypeError(
                    name='pgp_num',
                    actual=type(pgp_num),
                    expected=int)
            if pgp_num < 0:
                raise CephClientValueOutOfBounds(
                    name='pgp_num',
                    actual=pgp_num,
                    min=0,
                    max='unlimited')
            kwargs['pgp_num'] = pgp_num
        if pool_type is not None:
            if not isinstance(pool_type, six.string_types):
                raise CephClientTypeError(
                    name='pool_type',
                    actual=type(pool_type),
                    expected=six.string_types)
            supported = CephClient.OSD_POOL_CREATE_POOL_TYPE_VALUES
            if pool_type not in supported:
                raise CephClientInvalidChoice(
                    function='osd_pool_create',
                    option='pool_type',
                    value=pool_type,
                    supported=', '.join(supported))
            kwargs['pool_type'] = pool_type
        if erasure_code_profile is not None:
            if not isinstance(erasure_code_profile, six.string_types):
                raise CephClientTypeError(
                    name='erasure_code_profile',
                    actual=type(erasure_code_profile),
                    expected=six.string_types)
            kwargs['erasure_code_profile'] = erasure_code_profile
        if rule is not None:
            if not isinstance(rule, six.string_types):
                raise CephClientTypeError(
                    name='rule',
                    actual=type(rule),
                    expected=six.string_types)
            kwargs['rule'] = rule
        if expected_num_objects is not None:
            if not isinstance(expected_num_objects, six.integer_types):
                raise CephClientTypeError(
                    name='expected_num_objects',
                    actual=type(expected_num_objects),
                    expected=int)
            kwargs['expected_num_objects'] = expected_num_objects
        return self._request('osd pool create', **kwargs)

    def osd_pool_delete(self, pool, pool2=None,
                        sure=None, body='json', timeout=None):
        """delete pool"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if pool2 is not None:
            if not isinstance(pool2, six.string_types):
                raise CephClientTypeError(
                    name='pool2',
                    actual=type(pool2),
                    expected=six.string_types)
            kwargs['pool2'] = pool2
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            kwargs['sure'] = sure
        return self._request('osd pool delete', **kwargs)

    def osd_pool_rm(self, pool, pool2=None, sure=None,
                    body='json', timeout=None):
        """remove pool"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if pool2 is not None:
            if not isinstance(pool2, six.string_types):
                raise CephClientTypeError(
                    name='pool2',
                    actual=type(pool2),
                    expected=six.string_types)
            kwargs['pool2'] = pool2
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            kwargs['sure'] = sure
        return self._request('osd pool rm', **kwargs)

    def osd_pool_rename(self, srcpool, destpool,
                        body='json', timeout=None):
        """rename <srcpool> to <destpool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(srcpool, six.string_types):
            raise CephClientTypeError(
                name='srcpool',
                actual=type(srcpool),
                expected=six.string_types)

        kwargs['srcpool'] = srcpool
        if not isinstance(destpool, six.string_types):
            raise CephClientTypeError(
                name='destpool',
                actual=type(destpool),
                expected=six.string_types)

        kwargs['destpool'] = destpool
        return self._request('osd pool rename', **kwargs)

    OSD_POOL_GET_VAR_VALUES = \
        ['size', 'min_size', 'pg_num', 'pgp_num',
         'crush_rule', 'hashpspool', 'nodelete',
         'nopgchange', 'nosizechange',
         'write_fadvise_dontneed', 'noscrub',
         'nodeep-scrub', 'hit_set_type',
         'hit_set_period', 'hit_set_count',
         'hit_set_fpp', 'use_gmt_hitset', 'auid',
         'target_max_objects', 'target_max_bytes',
         'cache_target_dirty_ratio',
         'cache_target_dirty_high_ratio',
         'cache_target_full_ratio',
         'cache_min_flush_age', 'cache_min_evict_age',
         'erasure_code_profile',
         'min_read_recency_for_promote', 'all',
         'min_write_recency_for_promote', 'fast_read',
         'hit_set_grade_decay_rate',
         'hit_set_search_last_n', 'scrub_min_interval',
         'scrub_max_interval', 'deep_scrub_interval',
         'recovery_priority', 'recovery_op_priority',
         'scrub_priority', 'compression_mode',
         'compression_algorithm',
         'compression_required_ratio',
         'compression_max_blob_size',
         'compression_min_blob_size', 'csum_type',
         'csum_min_block', 'csum_max_block',
         'allow_ec_overwrites']

    def osd_pool_get(self, pool, var, body='json', timeout=None):
        """get pool parameter <var>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(var, six.string_types):
            raise CephClientTypeError(
                name='var',
                actual=type(var),
                expected=six.string_types)
        supported = CephClient.OSD_POOL_GET_VAR_VALUES
        if var not in supported:
            raise CephClientInvalidChoice(
                function='osd_pool_get',
                option='var',
                value=var,
                supported=', '.join(supported))

        kwargs['var'] = var
        return self._request('osd pool get', **kwargs)

    OSD_POOL_SET_VAR_VALUES = \
        ['size', 'min_size', 'pg_num', 'pgp_num',
         'crush_rule', 'hashpspool', 'nodelete',
         'nopgchange', 'nosizechange',
         'write_fadvise_dontneed', 'noscrub',
         'nodeep-scrub', 'hit_set_type',
         'hit_set_period', 'hit_set_count',
         'hit_set_fpp', 'use_gmt_hitset',
         'target_max_bytes', 'target_max_objects',
         'cache_target_dirty_ratio',
         'cache_target_dirty_high_ratio',
         'cache_target_full_ratio',
         'cache_min_flush_age', 'cache_min_evict_age',
         'auid', 'min_read_recency_for_promote',
         'min_write_recency_for_promote', 'fast_read',
         'hit_set_grade_decay_rate',
         'hit_set_search_last_n', 'scrub_min_interval',
         'scrub_max_interval', 'deep_scrub_interval',
         'recovery_priority', 'recovery_op_priority',
         'scrub_priority', 'compression_mode',
         'compression_algorithm',
         'compression_required_ratio',
         'compression_max_blob_size',
         'compression_min_blob_size', 'csum_type',
         'csum_min_block', 'csum_max_block',
         'allow_ec_overwrites']

    OSD_POOL_SET_FORCE_VALUES = ['--yes-i-really-mean-it']

    def osd_pool_set(self, pool, var, val, force=None,
                     body='json', timeout=None):
        """set pool parameter <var> to <val>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(var, six.string_types):
            raise CephClientTypeError(
                name='var',
                actual=type(var),
                expected=six.string_types)
        supported = CephClient.OSD_POOL_SET_VAR_VALUES
        if var not in supported:
            raise CephClientInvalidChoice(
                function='osd_pool_set',
                option='var',
                value=var,
                supported=', '.join(supported))

        kwargs['var'] = var
        if not isinstance(val, six.string_types):
            raise CephClientTypeError(
                name='val',
                actual=type(val),
                expected=six.string_types)

        kwargs['val'] = val
        if force is not None:
            if not isinstance(force, six.string_types):
                raise CephClientTypeError(
                    name='force',
                    actual=type(force),
                    expected=six.string_types)
            supported = CephClient.OSD_POOL_SET_FORCE_VALUES
            if force not in supported:
                raise CephClientInvalidChoice(
                    function='osd_pool_set',
                    option='force',
                    value=force,
                    supported=', '.join(supported))
            kwargs['force'] = force
        return self._request('osd pool set', **kwargs)

    OSD_POOL_SET_QUOTA_FIELD_VALUES = ['max_objects', 'max_bytes']

    def osd_pool_set_quota(self, pool, field, val,
                           body='json', timeout=None):
        """set object or byte limit on pool"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(field, six.string_types):
            raise CephClientTypeError(
                name='field',
                actual=type(field),
                expected=six.string_types)
        supported = CephClient.OSD_POOL_SET_QUOTA_FIELD_VALUES
        if field not in supported:
            raise CephClientInvalidChoice(
                function='osd_pool_set_quota',
                option='field',
                value=field,
                supported=', '.join(supported))

        kwargs['field'] = field
        if not isinstance(val, six.string_types):
            raise CephClientTypeError(
                name='val',
                actual=type(val),
                expected=six.string_types)

        kwargs['val'] = val
        return self._request('osd pool set-quota', **kwargs)

    def osd_pool_get_quota(self, pool, body='json', timeout=None):
        """obtain object or byte limits for pool"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('osd pool get-quota', **kwargs)

    OSD_POOL_APPLICATION_ENABLE_FORCE_VALUES = ['--yes-i-really-mean-it']

    def osd_pool_application_enable(
            self, pool, app, force=None, body='json', timeout=None):
        """enable use of an application <app> [cephfs,rbd,rgw] on pool <poolname>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(app, six.string_types):
            raise CephClientTypeError(
                name='app',
                actual=type(app),
                expected=six.string_types)

        kwargs['app'] = app
        if force is not None:
            if not isinstance(force, six.string_types):
                raise CephClientTypeError(
                    name='force',
                    actual=type(force),
                    expected=six.string_types)
            supported = CephClient.OSD_POOL_APPLICATION_ENABLE_FORCE_VALUES
            if force not in supported:
                raise CephClientInvalidChoice(
                    function='osd_pool_application_enable',
                    option='force',
                    value=force,
                    supported=', '.join(supported))
            kwargs['force'] = force
        return self._request('osd pool application enable', **kwargs)

    OSD_POOL_APPLICATION_DISABLE_FORCE_VALUES = ['--yes-i-really-mean-it']

    def osd_pool_application_disable(
            self, pool, app, force=None, body='json', timeout=None):
        """disables use of an application <app> on pool <poolname>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(app, six.string_types):
            raise CephClientTypeError(
                name='app',
                actual=type(app),
                expected=six.string_types)

        kwargs['app'] = app
        if force is not None:
            if not isinstance(force, six.string_types):
                raise CephClientTypeError(
                    name='force',
                    actual=type(force),
                    expected=six.string_types)
            supported = CephClient.OSD_POOL_APPLICATION_DISABLE_FORCE_VALUES
            if force not in supported:
                raise CephClientInvalidChoice(
                    function='osd_pool_application_disable',
                    option='force',
                    value=force,
                    supported=', '.join(supported))
            kwargs['force'] = force
        return self._request('osd pool application disable', **kwargs)

    def osd_pool_application_set(
            self, pool, app, key, value, body='json', timeout=None):
        """sets application <app> metadata key <key> to <value> on pool<poolname> """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(app, six.string_types):
            raise CephClientTypeError(
                name='app',
                actual=type(app),
                expected=six.string_types)

        kwargs['app'] = app
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        if not isinstance(value, six.string_types):
            raise CephClientTypeError(
                name='value',
                actual=type(value),
                expected=six.string_types)

        kwargs['value'] = value
        return self._request('osd pool application set', **kwargs)

    def osd_pool_application_rm(
            self, pool, app, key, body='json', timeout=None):
        """removes application <app> metadata key <key> on pool <poolname>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(app, six.string_types):
            raise CephClientTypeError(
                name='app',
                actual=type(app),
                expected=six.string_types)

        kwargs['app'] = app
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        return self._request('osd pool application rm', **kwargs)

    def osd_pool_application_get(
            self, pool, app=None, key=None, body='json', timeout=None):
        """get value of key <key> of application <app> on pool <poolname>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if app is not None:
            if not isinstance(app, six.string_types):
                raise CephClientTypeError(
                    name='app',
                    actual=type(app),
                    expected=six.string_types)
            kwargs['app'] = app
        if key is not None:
            if not isinstance(key, six.string_types):
                raise CephClientTypeError(
                    name='key',
                    actual=type(key),
                    expected=six.string_types)
            kwargs['key'] = key
        return self._request('osd pool application get', **kwargs)

    def osd_utilization(self, body='json', timeout=None):
        """get basic pg distribution stats"""
        return self._request('osd utilization', body=body, timeout=timeout)

    OSD_TIER_ADD_FORCE_NONEMPTY_VALUES = ['--force-nonempty']

    def osd_tier_add(
            self, pool, tierpool, force_nonempty=None, body='json',
            timeout=None):
        """add the tier <tierpool> (the second one) to base pool <pool> (thefirst one)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(tierpool, six.string_types):
            raise CephClientTypeError(
                name='tierpool',
                actual=type(tierpool),
                expected=six.string_types)

        kwargs['tierpool'] = tierpool
        if force_nonempty is not None:
            if not isinstance(force_nonempty, six.string_types):
                raise CephClientTypeError(
                    name='force_nonempty',
                    actual=type(force_nonempty),
                    expected=six.string_types)
            supported = CephClient.OSD_TIER_ADD_FORCE_NONEMPTY_VALUES
            if force_nonempty not in supported:
                raise CephClientInvalidChoice(
                    function='osd_tier_add',
                    option='force_nonempty',
                    value=force_nonempty,
                    supported=', '.join(supported))
            kwargs['force_nonempty'] = force_nonempty
        return self._request('osd tier add', **kwargs)

    def osd_tier_rm(self, pool, tierpool, body='json', timeout=None):
        """remove the tier <tierpool> (the second one) from base pool <pool> (thefirst one)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(tierpool, six.string_types):
            raise CephClientTypeError(
                name='tierpool',
                actual=type(tierpool),
                expected=six.string_types)

        kwargs['tierpool'] = tierpool
        return self._request('osd tier rm', **kwargs)

    def osd_tier_remove(self, pool, tierpool, body='json', timeout=None):
        """remove the tier <tierpool> (the second one) from base pool <pool> (thefirst one)"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(tierpool, six.string_types):
            raise CephClientTypeError(
                name='tierpool',
                actual=type(tierpool),
                expected=six.string_types)

        kwargs['tierpool'] = tierpool
        return self._request('osd tier remove', **kwargs)

    OSD_TIER_CACHE_MODE_MODE_VALUES = \
        ['none', 'writeback', 'forward', 'readonly',
         'readforward', 'proxy', 'readproxy']

    OSD_TIER_CACHE_MODE_SURE_VALUES = ['--yes-i-really-mean-it']

    def osd_tier_cache_mode(
            self, pool, mode, sure=None, body='json', timeout=None):
        """specify the caching mode for cache tier <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(mode, six.string_types):
            raise CephClientTypeError(
                name='mode',
                actual=type(mode),
                expected=six.string_types)
        supported = CephClient.OSD_TIER_CACHE_MODE_MODE_VALUES
        if mode not in supported:
            raise CephClientInvalidChoice(
                function='osd_tier_cache_mode',
                option='mode',
                value=mode,
                supported=', '.join(supported))

        kwargs['mode'] = mode
        if sure is not None:
            if not isinstance(sure, six.string_types):
                raise CephClientTypeError(
                    name='sure',
                    actual=type(sure),
                    expected=six.string_types)
            supported = CephClient.OSD_TIER_CACHE_MODE_SURE_VALUES
            if sure not in supported:
                raise CephClientInvalidChoice(
                    function='osd_tier_cache_mode',
                    option='sure',
                    value=sure,
                    supported=', '.join(supported))
            kwargs['sure'] = sure
        return self._request('osd tier cache-mode', **kwargs)

    def osd_tier_set_overlay(
            self, pool, overlaypool, body='json', timeout=None):
        """set the overlay pool for base pool <pool> to be <overlaypool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(overlaypool, six.string_types):
            raise CephClientTypeError(
                name='overlaypool',
                actual=type(overlaypool),
                expected=six.string_types)

        kwargs['overlaypool'] = overlaypool
        return self._request('osd tier set-overlay', **kwargs)

    def osd_tier_rm_overlay(self, pool, body='json', timeout=None):
        """remove the overlay pool for base pool <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('osd tier rm-overlay', **kwargs)

    def osd_tier_remove_overlay(self, pool, body='json', timeout=None):
        """remove the overlay pool for base pool <pool>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        return self._request('osd tier remove-overlay', **kwargs)

    def osd_tier_add_cache(self, pool, tierpool, size,
                           body='json', timeout=None):

        """add a cache <tierpool> (the second one) of size <size> to existingpool <pool> (the first one) """
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(pool, six.string_types):
            raise CephClientTypeError(
                name='pool',
                actual=type(pool),
                expected=six.string_types)

        kwargs['pool'] = pool
        if not isinstance(tierpool, six.string_types):
            raise CephClientTypeError(
                name='tierpool',
                actual=type(tierpool),
                expected=six.string_types)

        kwargs['tierpool'] = tierpool
        if not isinstance(size, six.integer_types):
            raise CephClientTypeError(
                name='size',
                actual=type(size),
                expected=int)
        if size < 0:
            raise CephClientValueOutOfBounds(
                name='size',
                actual=size,
                min=0,
                max='unlimited')

        kwargs['size'] = size
        return self._request('osd tier add-cache', **kwargs)

    def config_key_get(self, key, body='json', timeout=None):
        """get <key>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        return self._request('config-key get', **kwargs)

    def config_key_set(self, key, val=None, body='json', timeout=None):
        """set <key> to value <val>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        if val is not None:
            if not isinstance(val, six.string_types):
                raise CephClientTypeError(
                    name='val',
                    actual=type(val),
                    expected=six.string_types)
            kwargs['val'] = val
        return self._request('config-key set', **kwargs)

    def config_key_put(self, key, val=None, body='json', timeout=None):
        """put <key>, value <val>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        if val is not None:
            if not isinstance(val, six.string_types):
                raise CephClientTypeError(
                    name='val',
                    actual=type(val),
                    expected=six.string_types)
            kwargs['val'] = val
        return self._request('config-key put', **kwargs)

    def config_key_del(self, key, body='json', timeout=None):
        """delete <key>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        return self._request('config-key del', **kwargs)

    def config_key_rm(self, key, body='json', timeout=None):
        """rm <key>"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        return self._request('config-key rm', **kwargs)

    def config_key_exists(self, key, body='json', timeout=None):
        """check for <key>'s existence"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        return self._request('config-key exists', **kwargs)

    def config_key_list(self, body='json', timeout=None):
        """list keys"""
        return self._request('config-key list', body=body, timeout=timeout)

    def config_key_ls(self, body='json', timeout=None):
        """list keys"""
        return self._request('config-key ls', body=body, timeout=timeout)

    def config_key_dump(self, key=None, body='json', timeout=None):
        """dump keys and values (with optional prefix)"""
        kwargs = dict(body=body, timeout=timeout)
        if key is not None:
            if not isinstance(key, six.string_types):
                raise CephClientTypeError(
                    name='key',
                    actual=type(key),
                    expected=six.string_types)
            kwargs['key'] = key
        return self._request('config-key dump', **kwargs)

    def mgr_dump(self, epoch=None, body='json', timeout=None):
        """dump the latest MgrMap"""
        kwargs = dict(body=body, timeout=timeout)
        if epoch is not None:
            if not isinstance(epoch, six.integer_types):
                raise CephClientTypeError(
                    name='epoch',
                    actual=type(epoch),
                    expected=int)
            if epoch < 0:
                raise CephClientValueOutOfBounds(
                    name='epoch',
                    actual=epoch,
                    min=0,
                    max='unlimited')
            kwargs['epoch'] = epoch
        return self._request('mgr dump', **kwargs)

    def mgr_fail(self, who, body='json', timeout=None):
        """treat the named manager daemon as failed"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        return self._request('mgr fail', **kwargs)

    def mgr_module_ls(self, body='json', timeout=None):
        """list active mgr modules"""
        return self._request('mgr module ls', body=body, timeout=timeout)

    def mgr_services(self, body='json', timeout=None):
        """list service endpoints provided by mgr modules"""
        return self._request('mgr services', body=body, timeout=timeout)

    MGR_MODULE_ENABLE_FORCE_VALUES = ['--force']

    def mgr_module_enable(self, module, force=None,
                          body='json', timeout=None):
        """enable mgr module"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(module, six.string_types):
            raise CephClientTypeError(
                name='module',
                actual=type(module),
                expected=six.string_types)

        kwargs['module'] = module
        if force is not None:
            if not isinstance(force, six.string_types):
                raise CephClientTypeError(
                    name='force',
                    actual=type(force),
                    expected=six.string_types)
            supported = CephClient.MGR_MODULE_ENABLE_FORCE_VALUES
            if force not in supported:
                raise CephClientInvalidChoice(
                    function='mgr_module_enable',
                    option='force',
                    value=force,
                    supported=', '.join(supported))
            kwargs['force'] = force
        return self._request('mgr module enable', **kwargs)

    def mgr_module_disable(self, module, body='json', timeout=None):
        """disable mgr module"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(module, six.string_types):
            raise CephClientTypeError(
                name='module',
                actual=type(module),
                expected=six.string_types)

        kwargs['module'] = module
        return self._request('mgr module disable', **kwargs)

    def mgr_metadata(self, who=None, body='json', timeout=None):
        """dump metadata for all daemons or a specific daemon"""
        kwargs = dict(body=body, timeout=timeout)
        if who is not None:
            if not isinstance(who, six.string_types):
                raise CephClientTypeError(
                    name='who',
                    actual=type(who),
                    expected=six.string_types)
            kwargs['who'] = who
        return self._request('mgr metadata', **kwargs)

    def mgr_count_metadata(self, _property, body='json', timeout=None):
        """count ceph-mgr daemons by metadata field property"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(_property, six.string_types):
            raise CephClientTypeError(
                name='_property',
                actual=type(_property),
                expected=six.string_types)

        kwargs['property'] = _property
        return self._request('mgr count-metadata', **kwargs)

    def mgr_versions(self, body='json', timeout=None):
        """check running versions of ceph-mgr daemons"""
        return self._request('mgr versions', body=body, timeout=timeout)

    def config_set(self, who, name, value, body='json', timeout=None):
        """Set a configuration option for one or more entities"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        if not isinstance(value, six.string_types):
            raise CephClientTypeError(
                name='value',
                actual=type(value),
                expected=six.string_types)

        kwargs['value'] = value
        return self._request('config set', **kwargs)

    def config_rm(self, who, name, body='json', timeout=None):
        """Clear a configuration option for one or more entities"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        if not isinstance(name, six.string_types):
            raise CephClientTypeError(
                name='name',
                actual=type(name),
                expected=six.string_types)

        kwargs['name'] = name
        return self._request('config rm', **kwargs)

    def config_get(self, who, key, body='json', timeout=None):
        """Show configuration option(s) for an entity"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(who, six.string_types):
            raise CephClientTypeError(
                name='who',
                actual=type(who),
                expected=six.string_types)

        kwargs['who'] = who
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        return self._request('config get', **kwargs)

    def config_dump(self, body='json', timeout=None):
        """Show all configuration option(s)"""
        return self._request('config dump', body=body, timeout=timeout)

    def config_help(self, key, body='json', timeout=None):
        """Describe a configuration option"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(key, six.string_types):
            raise CephClientTypeError(
                name='key',
                actual=type(key),
                expected=six.string_types)

        kwargs['key'] = key
        return self._request('config help', **kwargs)

    def config_assimilate_conf(self, body='json', timeout=None):
        """Assimilate options from a conf, and return a new, minimal conf file"""
        return self._request('config assimilate-conf',
                             body=body, timeout=timeout)

    def config_log(self, num, body='json', timeout=None):
        """Show recent history of config changes"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(num, six.integer_types):
            raise CephClientTypeError(
                name='num',
                actual=type(num),
                expected=int)

        kwargs['num'] = num
        return self._request('config log', **kwargs)

    def config_reset(self, num, body='json', timeout=None):
        """Revert configuration to previous state"""
        kwargs = dict(body=body, timeout=timeout)
        if not isinstance(num, six.integer_types):
            raise CephClientTypeError(
                name='num',
                actual=type(num),
                expected=int)

        kwargs['num'] = num
        return self._request('config reset', **kwargs)
