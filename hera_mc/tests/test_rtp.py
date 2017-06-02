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

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()
        self.test_db.drop_tables()

    def test_add_rtp_status(self):
        status_time = pytz.utc.localize(datetime.datetime.utcnow())
        status = 'happy'
        event_min_elapsed = 3.6
        num_processes = 8
        restart_hours_elapsed = 10.2

        expected = RTPStatus(time=status_time, status=status,
                             event_min_elapsed=event_min_elapsed,
                             num_processes=num_processes,
                             restart_hours_elapsed=restart_hours_elapsed)

        self.test_session.add_rtp_status(status_time, status, event_min_elapsed,
                                         num_processes, restart_hours_elapsed)
        result = self.test_session.get_rtp_status(status_time)[0]

        self.assertEqual(result, expected)

        new_status_time = status_time + datetime.timedelta(minutes=5)
        new_status = 'unhappy'
        self.test_session.add_rtp_status(new_status_time, new_status,
                                         event_min_elapsed + 5, num_processes,
                                         restart_hours_elapsed + 5. / 60.)

        result_mult = self.test_session.get_rtp_status(status_time,
                                                       stoptime=new_status_time)
        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_rtp_status(new_status_time)[0]
        self.assertFalse(result2 == expected)


if __name__ == '__main__':
    unittest.main()
