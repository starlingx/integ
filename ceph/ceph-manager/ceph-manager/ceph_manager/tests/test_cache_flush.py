#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import unittest
import mock

import subprocess
import math

from ..cache_tiering import CacheTiering
from ..cache_tiering import LOG as CT_LOG
from ..constants import CACHE_FLUSH_OBJECTS_THRESHOLD
from ..constants import CACHE_FLUSH_MIN_WAIT_OBJ_COUNT_DECREASE_SEC as MIN_WAIT
from ..constants import CACHE_FLUSH_MAX_WAIT_OBJ_COUNT_DECREASE_SEC as MAX_WAIT
from ..exception import CephCacheFlushFailure


class TestCacheFlush(unittest.TestCase):

    def setUp(self):
        self.service = mock.Mock()
        self.ceph_api = mock.Mock()
        self.service.ceph_api = self.ceph_api
        self.cache_tiering = CacheTiering(self.service)

    @mock.patch('subprocess.check_call')
    def test_set_param_fail(self, mock_proc_call):
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=False, status_code=500, reason='denied'),
            {})
        self.cache_tiering.cache_flush({'pool_name': 'test'})
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])

    @mock.patch('subprocess.check_call')
    def test_df_fail(self, mock_proc_call):
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {})
        self.ceph_api.df = mock.Mock()
        self.ceph_api.df.return_value = (
            mock.Mock(ok=False, status_code=500, reason='denied'),
            {})
        self.cache_tiering.cache_flush({'pool_name': 'test'})
        self.ceph_api.osd_set_pool_param.assert_called_once_with(
            'test-cache', 'target_max_objects', 1, force=None, body='json')
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])

    @mock.patch('subprocess.check_call')
    def test_rados_evict_fail_raises(self, mock_proc_call):
        mock_proc_call.side_effect = subprocess.CalledProcessError(1, ['cmd'])
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=False, status_code=500, reason='denied'),
            {})
        self.assertRaises(CephCacheFlushFailure,
                          self.cache_tiering.cache_flush,
                          {'pool_name': 'test'})
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])

    @mock.patch('subprocess.check_call')
    def test_df_missing_pool(self, mock_proc_call):
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {})
        self.ceph_api.df = mock.Mock()
        self.ceph_api.df.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {'output': {
                'pools': [
                    {'id': 0,
                     'name': 'rbd',
                     'stats': {'bytes_used': 0,
                               'kb_used': 0,
                               'max_avail': 9588428800,
                               'objects': 0}}]},
             'status': 'OK'})
        with mock.patch.object(CT_LOG, 'warn') as mock_lw:
            self.cache_tiering.cache_flush({'pool_name': 'test'})
            self.ceph_api.df.assert_called_once_with(body='json')
            for c in mock_lw.call_args_list:
                if 'Missing pool free space' in c[0][0]:
                    break
            else:
                self.fail('expected log warning')
        self.ceph_api.osd_set_pool_param.assert_called_once_with(
            'test-cache', 'target_max_objects', 1, force=None, body='json')
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])

    @mock.patch('subprocess.check_call')
    def test_df_objects_empty(self, mock_proc_call):
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {})
        self.ceph_api.df = mock.Mock()
        self.ceph_api.df.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {'output': {
                'pools': [
                    {'id': 0,
                     'name': 'test-cache',
                     'stats': {'bytes_used': 0,
                               'kb_used': 0,
                               'max_avail': 9588428800,
                               'objects': 0}}]},
             'status': 'OK'})
        self.cache_tiering.cache_flush({'pool_name': 'test'})
        self.ceph_api.df.assert_called_once_with(body='json')
        self.ceph_api.osd_set_pool_param.assert_called_once_with(
            'test-cache', 'target_max_objects', 1, force=None, body='json')
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])

    @mock.patch('time.sleep')
    @mock.patch('subprocess.check_call')
    def test_df_objects_above_threshold(self, mock_proc_call, mock_time_sleep):
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {})
        self.ceph_api.df = mock.Mock()
        self.ceph_api.df.side_effect = [
            (mock.Mock(ok=True, status_code=200, reason='OK'),
             {'output': {
                 'pools': [
                     {'id': 0,
                      'name': 'test-cache',
                      'stats': {'bytes_used': 0,
                                'kb_used': 0,
                                'max_avail': 9588428800,
                                'objects': CACHE_FLUSH_OBJECTS_THRESHOLD}}]},
              'status': 'OK'}),
            (mock.Mock(ok=True, status_code=200, reason='OK'),
             {'output': {
                 'pools': [
                     {'id': 0,
                      'name': 'test-cache',
                      'stats': {'bytes_used': 0,
                                'kb_used': 0,
                                'max_avail': 9588428800,
                                'objects':
                                    CACHE_FLUSH_OBJECTS_THRESHOLD - 1}}]},
              'status': 'OK'})]
        self.cache_tiering.cache_flush({'pool_name': 'test'})
        self.ceph_api.osd_set_pool_param.assert_called_once_with(
            'test-cache', 'target_max_objects', 1, force=None, body='json')
        self.ceph_api.df.assert_called_with(body='json')
        mock_time_sleep.assert_called_once_with(MIN_WAIT)
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])

    @mock.patch('time.sleep')
    @mock.patch('subprocess.check_call')
    def test_df_objects_interval_increase(self, mock_proc_call,
                                          mock_time_sleep):
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {})
        self.ceph_api.df = mock.Mock()
        self.ceph_api.df.side_effect = [
            (mock.Mock(ok=True, status_code=200, reason='OK'),
             {'output': {
                 'pools': [
                     {'id': 0,
                      'name': 'test-cache',
                      'stats': {'bytes_used': 0,
                                'kb_used': 0,
                                'max_avail': 9588428800,
                                'objects':
                                    CACHE_FLUSH_OBJECTS_THRESHOLD + 1}}]},
              'status': 'OK'}),
            (mock.Mock(ok=True, status_code=200, reason='OK'),
             {'output': {
                 'pools': [
                     {'id': 0,
                      'name': 'test-cache',
                      'stats': {'bytes_used': 0,
                                'kb_used': 0,
                                'max_avail': 9588428800,
                                'objects':
                                    CACHE_FLUSH_OBJECTS_THRESHOLD + 1}}]},
              'status': 'OK'}),
            (mock.Mock(ok=True, status_code=200, reason='OK'),
             {'output': {
                 'pools': [
                     {'id': 0,
                      'name': 'test-cache',
                      'stats': {'bytes_used': 0,
                                'kb_used': 0,
                                'max_avail': 9588428800,
                                'objects':
                                    CACHE_FLUSH_OBJECTS_THRESHOLD + 1}}]},
              'status': 'OK'}),
            (mock.Mock(ok=True, status_code=200, reason='OK'),
             {'output': {
                 'pools': [
                     {'id': 0,
                      'name': 'test-cache',
                      'stats': {'bytes_used': 0,
                                'kb_used': 0,
                                'max_avail': 9588428800,
                                'objects':
                                    CACHE_FLUSH_OBJECTS_THRESHOLD - 1}}]},
              'status': 'OK'})]
        self.cache_tiering.cache_flush({'pool_name': 'test'})
        self.ceph_api.osd_set_pool_param.assert_called_once_with(
            'test-cache', 'target_max_objects', 1, force=None, body='json')
        self.ceph_api.df.assert_called_with(body='json')
        self.assertEqual([c[0][0] for c in mock_time_sleep.call_args_list],
                         [MIN_WAIT,
                          MIN_WAIT * 2,
                          MIN_WAIT * 4])
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])

    @mock.patch('time.sleep')
    @mock.patch('subprocess.check_call')
    def test_df_objects_allways_over_threshold(self, mock_proc_call,
                                               mock_time_sleep):
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {})
        self.ceph_api.df = mock.Mock()
        self.ceph_api.df.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {'output': {
                'pools': [
                    {'id': 0,
                     'name': 'test-cache',
                     'stats': {'bytes_used': 0,
                               'kb_used': 0,
                               'max_avail': 9588428800,
                               'objects':
                                   CACHE_FLUSH_OBJECTS_THRESHOLD + 1}}]},
             'status': 'OK'})
        # noinspection PyTypeChecker
        mock_time_sleep.side_effect = \
            [None]*int(math.ceil(math.log(float(MAX_WAIT)/MIN_WAIT, 2)) + 1) \
            + [Exception('too many sleeps')]
        self.cache_tiering.cache_flush({'pool_name': 'test'})
        self.ceph_api.osd_set_pool_param.assert_called_once_with(
            'test-cache', 'target_max_objects', 1, force=None, body='json')
        self.ceph_api.df.assert_called_with(body='json')
        expected_sleep = []
        interval = MIN_WAIT
        while interval <= MAX_WAIT:
            expected_sleep.append(interval)
            interval *= 2
        self.assertEqual([c[0][0] for c in mock_time_sleep.call_args_list],
                         expected_sleep)
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])

    @mock.patch('time.sleep')
    @mock.patch('subprocess.check_call')
    def test_df_objects_increase(self, mock_proc_call, mock_time_sleep):
        self.ceph_api.osd_set_pool_param = mock.Mock()
        self.ceph_api.osd_set_pool_param.return_value = (
            mock.Mock(ok=True, status_code=200, reason='OK'),
            {})
        self.ceph_api.df = mock.Mock()
        self.ceph_api.df.side_effect = [
            (mock.Mock(ok=True, status_code=200, reason='OK'),
             {'output': {
                 'pools': [
                     {'id': 0,
                      'name': 'test-cache',
                      'stats': {'bytes_used': 0,
                                'kb_used': 0,
                                'max_avail': 9588428800,
                                'objects':
                                    CACHE_FLUSH_OBJECTS_THRESHOLD + 1}}]},
                 'status': 'OK'}),
            (mock.Mock(ok=True, status_code=200, reason='OK'),
             {'output': {
                 'pools': [
                    {'id': 0,
                     'name': 'test-cache',
                     'stats': {'bytes_used': 0,
                               'kb_used': 0,
                               'max_avail': 9588428800,
                               'objects':
                                   CACHE_FLUSH_OBJECTS_THRESHOLD + 2}}]},
                 'status': 'OK'})]
        with mock.patch.object(CT_LOG, 'warn') as mock_lw:
            self.cache_tiering.cache_flush({'pool_name': 'test'})
            for c in mock_lw.call_args_list:
                if 'Unexpected increase' in c[0][0]:
                    break
            else:
                self.fail('expected log warning')
        self.ceph_api.df.assert_called_with(body='json')
        mock_time_sleep.assert_called_once_with(MIN_WAIT)
        self.ceph_api.osd_set_pool_param.assert_called_once_with(
            'test-cache', 'target_max_objects', 1, force=None, body='json')
        mock_proc_call.assert_called_with(
            ['/usr/bin/rados', '-p', 'test-cache', 'cache-flush-evict-all'])
