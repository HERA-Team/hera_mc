# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.librarian`.

"""
import unittest
import numpy as np
from math import floor
from astropy.time import Time, TimeDelta

from hera_mc import mc
from hera_mc.librarian import LibStatus


class test_hera_mc(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_db.create_tables()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)

        time = Time.now()
        self.status_names = ['time', 'num_files', 'data_volume_gb',
                             'free_space_gb', 'upload_min_elapsed',
                             'num_processes', 'git_version', 'git_hash']
        self.status_values = [time, 135, 3.6, 8.2, 12.2, 3, 'v0.0.1', 'lskdjf24l']
        self.status_columns = dict(zip(self.status_names, self.status_values))

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()
        self.test_db.drop_tables()

    def test_add_rtp_status(self):
        self.test_session.add_lib_status(*self.status_values)

        exp_columns = self.status_columns.copy()
        exp_columns['time'] = exp_columns['time'].gps
        expected = LibStatus(**exp_columns)

        result = self.test_session.get_lib_status(self.status_columns['time'])[0]

        self.assertEqual(result, expected)

        new_status_time = self.status_columns['time'] + TimeDelta(5 * 60, format='sec')
        self.test_session.add_lib_status(new_status_time,
                                         self.status_columns['num_files'] + 2,
                                         self.status_columns['data_volume_gb'] + .2,
                                         self.status_columns['free_space_gb'] - .2,
                                         2.2, self.status_columns['num_processes'],
                                         self.status_columns['git_version'],
                                         self.status_columns['git_hash'])

        result_mult = self.test_session.get_lib_status(self.status_columns['time'],
                                                       stoptime=new_status_time)
        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_lib_status(new_status_time)[0]
        self.assertFalse(result2 == expected)

    def test_errors_lib_status(self):
        self.assertRaises(ValueError, self.test_session.add_lib_status, 'foo',
                          *self.status_values[1:])

        self.test_session.add_lib_status(*self.status_values)
        self.assertRaises(ValueError, self.test_session.get_lib_status, 'unhappy')
        self.assertRaises(ValueError, self.test_session.get_lib_status,
                          self.status_columns['time'], stoptime='unhappy')
