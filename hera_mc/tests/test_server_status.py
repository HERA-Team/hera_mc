# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.server_status`.

"""
import unittest
from math import floor
import numpy as np
from astropy.time import Time, TimeDelta

from hera_mc import mc
from hera_mc.rtp import RTPServerStatus
from hera_mc.librarian import LibServerStatus


class test_hera_mc(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)
        self.column_names = ['hostname', 'mc_time', 'ip_address', 'system_time',
                             'num_cores', 'cpu_load_pct', 'uptime_days',
                             'memory_used_pct', 'memory_size_gb',
                             'disk_space_pct', 'disk_size_gb',
                             'network_bandwidth_mbs']
        self.column_values = ['test_host', Time.now(), '0.0.0.0', Time.now(),
                              16, 20.5, 31.4, 43.2, 32., 46.8, 510.4, 10.4]
        self.columns = dict(zip(self.column_names, self.column_values))

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()

    def test_repr(self):
        for sub in ['rtp', 'lib']:
            exp_columns = self.columns.copy()
            exp_columns['mc_time'] = int(floor(exp_columns['mc_time'].gps))
            exp_columns.pop('system_time')
            exp_columns['mc_system_timediff'] = 0

            if sub == 'rtp':
                servstat = RTPServerStatus(**exp_columns)
                class_name = 'RTPServerStatus'
            elif sub == 'lib':
                servstat = LibServerStatus(**exp_columns)
                class_name = 'LibServerStatus'

        rep_string = ('<' + class_name + '(test_host, ' + str(exp_columns['mc_time']) +
                      ', 0.0.0.0, ' + str(exp_columns['mc_system_timediff']) +
                      ', 16, 20.5, 31.4, 43.2, 32.0, 46.8, 510.4, 10.4)>')
        self.assertEqual(str(servstat), rep_string)

    def test_add_server_status(self):
        for sub in ['rtp', 'lib']:
            exp_columns = self.columns.copy()
            exp_columns['mc_time'] = int(floor(exp_columns['mc_time'].gps))
            exp_columns.pop('system_time')
            exp_columns['mc_system_timediff'] = 0

            if sub == 'rtp':
                expected = RTPServerStatus(**exp_columns)
            elif sub == 'lib':
                expected = LibServerStatus(**exp_columns)

            self.test_session.add_server_status(sub, self.column_values[0],
                                                *self.column_values[2:11],
                                                network_bandwidth_mbs=self.column_values[11])
            result = self.test_session.get_server_status(sub, self.columns['system_time'] -
                                                         TimeDelta(2, format='sec'))
            self.assertEqual(len(result), 1)
            result = result[0]

            self.assertTrue(result.isclose(expected))

            self.test_session.add_server_status(sub, 'test_host2', *self.column_values[2:11],
                                                network_bandwidth_mbs=self.column_values[11])
            result_host = self.test_session.get_server_status(sub, self.columns['system_time'] -
                                                              TimeDelta(2, format='sec'),
                                                              hostname=self.columns['hostname'],
                                                              stoptime=self.columns['system_time'] +
                                                              TimeDelta(2 * 60, format='sec'))
            self.assertEqual(len(result_host), 1)
            result_host = result_host[0]
            self.assertTrue(result_host.isclose(expected))

            result_mult = self.test_session.get_server_status(sub, self.columns['system_time'] -
                                                              TimeDelta(2, format='sec'),
                                                              stoptime=self.columns['system_time'] +
                                                              TimeDelta(2 * 60, format='sec'))

            self.assertEqual(len(result_mult), 2)

            result2 = self.test_session.get_server_status(sub, self.columns['system_time'] -
                                                          TimeDelta(2, format='sec'),
                                                          hostname='test_host2')[0]
            # mc_times will be different, so won't match. set them equal so that we can test the rest
            expected.mc_time = result2.mc_time
            self.assertFalse(result2.isclose(expected))

    def test_errors_server_status(self):
        for sub in ['rtp', 'lib']:
            self.assertRaises(ValueError, self.test_session.add_server_status, sub,
                              self.column_values[0], self.column_values[2],
                              'foo', *self.column_values[4:11],
                              network_bandwidth_mbs=self.column_values[11])

            self.test_session.add_server_status(sub, self.column_values[0],
                                                *self.column_values[2:11],
                                                network_bandwidth_mbs=self.column_values[11])
            self.assertRaises(ValueError, self.test_session.get_server_status, sub, 'test_host')
            self.assertRaises(ValueError, self.test_session.get_server_status,
                              sub, self.columns['system_time'], stoptime='test_host')

        self.assertRaises(ValueError, self.test_session.add_server_status, 'foo',
                          self.column_values[0], *self.column_values[2:11],
                          network_bandwidth_mbs=self.column_values[11])
        self.assertRaises(ValueError, self.test_session.get_server_status, 'foo',
                          self.column_values[1])


if __name__ == '__main__':
    unittest.main()
