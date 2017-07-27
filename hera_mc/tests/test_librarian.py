# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.librarian`.

"""
import unittest
from math import floor
import numpy as np
from astropy.time import Time, TimeDelta

from hera_mc import mc, cm_transfer
from hera_mc.librarian import LibStatus, LibRAIDStatus, LibRAIDErrors, LibRemoteStatus, LibFiles
from hera_mc import utils


class test_hera_mc(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)
        cm_transfer._initialization(self.test_session)

        time = Time.now()
        self.status_names = ['time', 'num_files', 'data_volume_gb',
                             'free_space_gb', 'upload_min_elapsed',
                             'num_processes', 'git_version', 'git_hash']
        self.status_values = [time, 135, 3.6, 8.2, 12.2, 3, 'v0.0.1', 'lskdjf24l']
        self.status_columns = dict(zip(self.status_names, self.status_values))

        self.raid_status_names = ['time', 'hostname', 'num_disks', 'info']
        self.raid_status_values = [time, 'raid_1', 16, 'megaraid controller is happy']
        self.raid_status_columns = dict(zip(self.raid_status_names, self.raid_status_values))

        self.raid_error_names = ['time', 'hostname', 'disk', 'log']
        self.raid_error_values = [time, 'raid_1', 'd4', 'unhappy disk']
        self.raid_error_columns = dict(zip(self.raid_error_names, self.raid_error_values))

        self.remote_status_names = ['time', 'remote_name', 'ping_time',
                                    'num_file_uploads', 'bandwidth_mbs']
        self.remote_status_values = [time, 'nrao', .13, 5, 56.4]
        self.remote_status_columns = dict(zip(self.remote_status_names,
                                              self.remote_status_values))

        obsid = utils.calculate_obsid(time)
        self.observation_names = ['starttime', 'stoptime', 'obsid']
        self.observation_values = [time, time + TimeDelta(10 * 60, format='sec'),
                                   obsid]
        self.observation_columns = dict(zip(self.observation_names,
                                            self.observation_values))
        self.test_session.add_obs(*self.observation_values)
        obs_result = self.test_session.get_obs()
        self.assertTrue(len(obs_result), 1)

        self.file_names = ['filename', 'obsid', 'time', 'size_gb']
        self.file_values = ['file1', obsid, time, 2.4]
        self.file_columns = dict(zip(self.file_names, self.file_values))

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()

    def test_add_lib_status(self):
        self.test_session.add_lib_status(*self.status_values)

        exp_columns = self.status_columns.copy()
        exp_columns['time'] = int(floor(exp_columns['time'].gps))
        expected = LibStatus(**exp_columns)

        result = self.test_session.get_lib_status(self.status_columns['time'] -
                                                  TimeDelta(2, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]

        self.assertTrue(result.isclose(expected))

        new_status_time = self.status_columns['time'] + TimeDelta(5 * 60, format='sec')
        self.test_session.add_lib_status(new_status_time,
                                         self.status_columns['num_files'] + 2,
                                         self.status_columns['data_volume_gb'] + .2,
                                         self.status_columns['free_space_gb'] - .2,
                                         2.2, self.status_columns['num_processes'],
                                         self.status_columns['git_version'],
                                         self.status_columns['git_hash'])

        result_mult = self.test_session.get_lib_status(self.status_columns['time'] -
                                                       TimeDelta(2, format='sec'),
                                                       stoptime=new_status_time)
        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_lib_status(new_status_time -
                                                   TimeDelta(2, format='sec'))
        self.assertEqual(len(result2), 1)
        result2 = result2[0]
        self.assertFalse(result2.isclose(expected))

    def test_errors_lib_status(self):
        self.assertRaises(ValueError, self.test_session.add_lib_status, 'foo',
                          *self.status_values[1:])

        self.test_session.add_lib_status(*self.status_values)
        self.assertRaises(ValueError, self.test_session.get_lib_status, 'unhappy')
        self.assertRaises(ValueError, self.test_session.get_lib_status,
                          self.status_columns['time'], stoptime='unhappy')

    def test_add_raid_status(self):
        exp_columns = self.raid_status_columns.copy()
        exp_columns['time'] = int(floor(exp_columns['time'].gps))
        expected = LibRAIDStatus(**exp_columns)

        self.test_session.add_lib_raid_status(*self.raid_status_values)

        result = self.test_session.get_lib_raid_status(self.raid_status_columns['time'] -
                                                       TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]

        self.assertTrue(result.isclose(expected))

        self.test_session.add_lib_raid_status(self.raid_status_values[0], 'raid_2',
                                              *self.raid_status_values[2:])
        result_host = self.test_session.get_lib_raid_status(self.raid_status_columns['time'] -
                                                            TimeDelta(2, format='sec'),
                                                            hostname=self.raid_status_columns['hostname'],
                                                            stoptime=self.raid_status_columns['time'] +
                                                            TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result_host), 1)
        result_host = result_host[0]
        self.assertTrue(result_host.isclose(expected))

        result_mult = self.test_session.get_lib_raid_status(self.raid_status_columns['time'] -
                                                            TimeDelta(2, format='sec'),
                                                            stoptime=self.raid_status_columns['time'] +
                                                            TimeDelta(2 * 60, format='sec'))

        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_lib_raid_status(self.raid_status_columns['time'] -
                                                        TimeDelta(2, format='sec'),
                                                        hostname='raid_2')
        self.assertEqual(len(result2), 1)
        result2 = result2[0]

        self.assertFalse(result2.isclose(expected))

    def test_errors_lib_raid_status(self):
        self.assertRaises(ValueError, self.test_session.add_lib_raid_status,
                          'foo', *self.raid_status_values[1:])

        self.test_session.add_lib_raid_status(*self.raid_status_values)
        self.assertRaises(ValueError, self.test_session.get_lib_raid_status, 'foo')
        self.assertRaises(ValueError, self.test_session.get_lib_raid_status,
                          self.raid_status_columns['time'], stoptime='foo')

    def test_add_raid_error(self):
        exp_columns = self.raid_error_columns.copy()
        exp_columns['time'] = int(floor(exp_columns['time'].gps))
        expected = LibRAIDErrors(**exp_columns)

        self.test_session.add_lib_raid_error(*self.raid_error_values)

        result = self.test_session.get_lib_raid_error(self.raid_error_columns['time'] -
                                                      TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]

        self.assertTrue(result.isclose(expected))

        self.test_session.add_lib_raid_error(self.raid_error_values[0], 'raid_2',
                                             *self.raid_error_values[2:])
        result_host = self.test_session.get_lib_raid_error(self.raid_error_columns['time'] -
                                                           TimeDelta(2, format='sec'),
                                                           hostname=self.raid_error_columns['hostname'],
                                                           stoptime=self.raid_error_columns['time'] +
                                                           TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result_host), 1)
        result_host = result_host[0]
        self.assertTrue(result_host.isclose(expected))

        result_mult = self.test_session.get_lib_raid_error(self.raid_error_columns['time'] -
                                                           TimeDelta(2, format='sec'),
                                                           stoptime=self.raid_error_columns['time'] +
                                                           TimeDelta(2 * 60, format='sec'))

        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_lib_raid_error(self.raid_error_columns['time'] -
                                                       TimeDelta(2, format='sec'),
                                                       hostname='raid_2')[0]

        self.assertFalse(result2.isclose(expected))

    def test_errors_lib_raid_error(self):
        self.assertRaises(ValueError, self.test_session.add_lib_raid_error,
                          'foo', *self.raid_error_values[1:])

        self.test_session.add_lib_raid_error(*self.raid_error_values)
        self.assertRaises(ValueError, self.test_session.get_lib_raid_error, 'foo')
        self.assertRaises(ValueError, self.test_session.get_lib_raid_error,
                          self.raid_error_columns['time'], stoptime='foo')

    def test_add_remote_status(self):
        exp_columns = self.remote_status_columns.copy()
        exp_columns['time'] = int(floor(exp_columns['time'].gps))
        expected = LibRemoteStatus(**exp_columns)

        self.test_session.add_lib_remote_status(*self.remote_status_values)

        result = self.test_session.get_lib_remote_status(self.remote_status_columns['time'] -
                                                         TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]

        self.assertTrue(result.isclose(expected))

        self.test_session.add_lib_remote_status(self.remote_status_values[0], 'penn',
                                                *self.remote_status_values[2:])
        result_remote = self.test_session.get_lib_remote_status(
            self.remote_status_columns['time'] - TimeDelta(2, format='sec'),
            remote_name=self.remote_status_columns['remote_name'],
            stoptime=self.remote_status_columns['time'] + TimeDelta(2 * 60, format='sec'))

        self.assertEqual(len(result_remote), 1)
        result_remote = result_remote[0]
        self.assertTrue(result_remote.isclose(expected))

        result_mult = self.test_session.get_lib_remote_status(
            self.remote_status_columns['time'] - TimeDelta(2, format='sec'),
            stoptime=self.remote_status_columns['time'] + TimeDelta(2 * 60, format='sec'))

        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_lib_remote_status(self.remote_status_columns['time'] -
                                                          TimeDelta(2, format='sec'),
                                                          remote_name='penn')
        self.assertEqual(len(result2), 1)
        result2 = result2[0]

        self.assertFalse(result2.isclose(expected))

    def test_errors_lib_remote_status(self):
        self.assertRaises(ValueError, self.test_session.add_lib_remote_status,
                          'foo', *self.remote_status_values[1:])

        self.test_session.add_lib_remote_status(*self.remote_status_values)
        self.assertRaises(ValueError, self.test_session.get_lib_remote_status, 'foo')
        self.assertRaises(ValueError, self.test_session.get_lib_remote_status,
                          self.remote_status_columns['time'], stoptime='foo')

    def test_add_lib_file(self):
        # raise error if try to add process event with unmatched obsid
        # self.assertRaises(NoForeignKeysError, self.test_session.add_lib_file,
        #                   self.file_values[0], self.file_values[1] + 2,
        #                   self.file_values[2:5])

        self.test_session.add_lib_file(*self.file_values)

        exp_columns = self.file_columns.copy()
        exp_columns['time'] = int(floor(exp_columns['time'].gps))
        expected = LibFiles(**exp_columns)

        result_file = self.test_session.get_lib_files(filename=self.file_columns['filename'])[0]
        self.assertTrue(result_file.isclose(expected))

        result = self.test_session.get_lib_files(starttime=self.file_columns['time'] -
                                                 TimeDelta(2, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_obsid = self.test_session.get_lib_files(starttime=self.file_columns['time'] -
                                                       TimeDelta(2, format='sec'),
                                                       obsid=self.file_columns['obsid'])
        self.assertEqual(len(result_obsid), 1)
        result_obsid = result_obsid[0]
        self.assertTrue(result_obsid.isclose(expected))

        new_file_time = self.file_columns['time'] + TimeDelta(3 * 60, format='sec')
        new_file = 'file2'
        self.test_session.add_lib_file(new_file, self.file_values[1], new_file_time, 1.4)
        result_obsid = self.test_session.get_lib_files(obsid=self.file_columns['obsid'])
        self.assertEqual(len(result_obsid), 2)

        result_all = self.test_session.get_lib_files()
        self.assertEqual(len(result_obsid), len(result_all))
        for i in range(0, len(result_obsid)):
            self.assertTrue(result_obsid[i].isclose(result_all[i]))

    def test_errors_add_lib_file(self):
        self.assertRaises(ValueError, self.test_session.add_lib_file,
                          self.status_values[0], self.status_values[1], 'foo',
                          self.status_values[3])

        self.test_session.add_lib_file(*self.file_values)
        self.assertRaises(ValueError, self.test_session.get_lib_files, starttime='foo')
        self.assertRaises(ValueError, self.test_session.get_lib_files,
                          starttime=self.file_columns['time'], stoptime='bar')
