# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.server_status`.

"""
import unittest
import numpy as np
from astropy.time import Time, TimeDelta

from hera_mc import mc
from hera_mc.server_status import ServerStatus


class test_hera_mc(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_db.create_tables()
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
        self.test_db.drop_tables()

    def test_repr(self):
        servstat = ServerStatus(**self.columns)

        rep_string = ('<ServerStatus(test_host, ' + str(self.columns['mc_time']) +
                      ', 0.0.0.0, ' + str(self.columns['system_time']) +
                      ', 16, 20.5, 31.4, 43.2, 32.0, 46.8, 510.4, 10.4)>')
        self.assertEqual(str(servstat), rep_string)

    def test_add_server_status(self):
        exp_columns = self.columns.copy()
        exp_columns['mc_time'] = exp_columns['mc_time'].gps
        exp_columns['system_time'] = exp_columns['system_time'].gps
        expected = ServerStatus(**exp_columns)

        self.test_session.add_server_status(self.column_values[0], *self.column_values[2:11],
                                            network_bandwidth_mbs=self.column_values[11])
        result = self.test_session.get_server_status(self.columns['system_time'])[0]

        # mc_times should be different
        self.assertFalse(result == expected)

        # check that the mc_times are very close
        mc_time_diff = abs(expected.mc_time - result.mc_time)
        self.assertTrue(mc_time_diff < 0.1)
        # they are close enough. set them equal to test the rest of the objects
        expected.mc_time = result.mc_time

        self.assertEqual(result, expected)

        self.test_session.add_server_status('test_host2', *self.column_values[2:11],
                                            network_bandwidth_mbs=self.column_values[11])
        result_host = self.test_session.get_server_status(self.columns['system_time'],
                                                          hostname=self.columns['hostname'],
                                                          stoptime=self.columns['system_time'] +
                                                          TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result_host), 1)
        result_host = result_host[0]
        self.assertEqual(result_host, expected)

        result_mult = self.test_session.get_server_status(self.columns['system_time'],
                                                          stoptime=self.columns['system_time'] +
                                                          TimeDelta(2 * 60, format='sec'))

        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_server_status(self.columns['system_time'],
                                                      hostname='test_host2')[0]
        # mc_times will be different, so won't match. set them equal so that we can test the rest
        expected.mc_time = result2.mc_time
        self.assertFalse(result2 == expected)

    def test_errors_server_status(self):
        self.assertRaises(ValueError, self.test_session.add_server_status,
                          self.column_values[0], self.column_values[2],
                          'foo', *self.column_values[4:11],
                          network_bandwidth_mbs=self.column_values[11])

        self.test_session.add_server_status(self.column_values[0], *self.column_values[2:11],
                                            network_bandwidth_mbs=self.column_values[11])
        self.assertRaises(ValueError, self.test_session.get_server_status, 'test_host')
        self.assertRaises(ValueError, self.test_session.get_server_status,
                          self.columns['system_time'], stoptime='test_host')

if __name__ == '__main__':
    unittest.main()
