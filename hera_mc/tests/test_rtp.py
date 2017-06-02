# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.rtp`.

"""
import unittest

import numpy as np
import datetime
import pytz

from hera_mc import mc
from hera_mc.rtp import RTPStatus


class test_hera_mc(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_db.create_tables()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)
        self.column_names = ['time', 'status', 'event_min_elapsed',
                             'num_processes', 'restart_hours_elapsed']
        self.column_values = [pytz.utc.localize(datetime.datetime.utcnow()),
                              'happy', 3.6, 8, 10.2]
        self.columns = dict(zip(self.column_names, self.column_values))
        self.test_session.add_rtp_status(*self.column_values)

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()
        self.test_db.drop_tables()

    def test_add_rtp_status(self):
        expected = RTPStatus(**self.columns)

        result = self.test_session.get_rtp_status(self.columns['time'])[0]

        self.assertEqual(result, expected)

        new_status_time = self.columns['time'] + datetime.timedelta(minutes=5)
        new_status = 'unhappy'
        self.test_session.add_rtp_status(new_status_time, new_status,
                                         self.columns['event_min_elapsed'] + 5,
                                         self.columns['num_processes'],
                                         self.columns['restart_hours_elapsed'] + 5. / 60.)

        result_mult = self.test_session.get_rtp_status(self.columns['time'],
                                                       stoptime=new_status_time)
        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_rtp_status(new_status_time)[0]
        self.assertFalse(result2 == expected)

    def test_errors_server_status(self):
        self.assertRaises(ValueError, self.test_session.get_rtp_status, 'unhappy')
        self.assertRaises(ValueError, self.test_session.get_rtp_status,
                          self.columns['time'], stoptime='unhappy')


if __name__ == '__main__':
    unittest.main()
