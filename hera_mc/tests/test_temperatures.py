# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.temperatures`.

"""
from __future__ import absolute_import, division, print_function

import unittest

import numpy as np
from astropy.time import Time, TimeDelta
from hera_mc import mc, temperatures


class test_temperatures(unittest.TestCase):

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

    def test_add_paper_temps(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        temp_list = (np.arange(28) + 300.).tolist()
        temp2_list = (np.arange(28) + 310.).tolist()
        temp_colnames = ['balun_east', 'cable_east',
                         'balun_west', 'cable_west',
                         'rcvr_1a', 'rcvr_1b', 'rcvr_2a', 'rcvr_2b',
                         'rcvr_3a', 'rcvr_3b', 'rcvr_4a', 'rcvr_4b',
                         'rcvr_5a', 'rcvr_5b', 'rcvr_6a', 'rcvr_6b',
                         'rcvr_7a', 'rcvr_7b', 'rcvr_8a', 'rcvr_8b']
        temp_indices = (np.array([1, 2, 3, 4, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18,
                                  19, 20, 22, 23, 24, 25]) - 1).tolist()

        temp_values = [temp_list[i] for i in temp_indices]
        temp2_values = [temp2_list[i] for i in temp_indices]

        temp_dict = dict(zip(temp_colnames, temp_values))
        temp2_dict = dict(zip(temp_colnames, temp2_values))

        self.test_session.add(temperatures.PaperTemperatures.new_from_text_row(t1, temp_list))
        self.test_session.add(temperatures.PaperTemperatures.new_from_text_row(t2, temp2_list))

        expected = [temperatures.PaperTemperatures(gps_time=t1.gps, jd_time=t1.jd, **temp_dict)]
        result = self.test_session.get_paper_temps(t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(result, expected)

        result = self.test_session.get_paper_temps(t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

        expected2 = [temperatures.PaperTemperatures(gps_time=t1.gps, jd_time=t1.jd,
                                                    **temp_dict),
                     temperatures.PaperTemperatures(gps_time=t2.gps, jd_time=t2.jd,
                                                    **temp2_dict)]
        result = self.test_session.get_paper_temps(t1 - TimeDelta(3.0, format='sec'),
                                                   stoptime=t2 + TimeDelta(1.0, format='sec'))
        self.assertEqual(result, expected2)


if __name__ == '__main__':
    unittest.main()
