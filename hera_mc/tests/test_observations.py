# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.observations`.

"""
import unittest

import numpy as np
from math import floor
from astropy.time import Time, TimeDelta
from astropy.coordinates import EarthLocation

from hera_mc import mc
from hera_mc.observations import Observation


class test_hera_mc(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()

    def test_new_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        t3 = t1 + TimeDelta(1e-3, format='sec')
        t4 = t2 + TimeDelta(1e-3, format='sec')

        obs1 = Observation.new_observation(t1, t2)
        obs2 = Observation.new_observation(t3, t4)
        self.assertFalse(obs1 == obs2)

    def test_add_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        # generated test hera_lat, hera_lon using the output of geo.py -c
        # with this website: http://www.uwgb.edu/dutchs/usefuldata/ConvertUTMNoOZ.HTM

        obsid = floor(t1.gps)
        t1.location = EarthLocation.from_geodetic(21.4283038269, -30.7215261207)

        expected = Observation(obsid=obsid, start_time_jd=t1.jd,
                               stop_time_jd=t2.jd,
                               lst_start_hr=t1.sidereal_time('apparent').hour)

        self.test_session.add_obs(t1, t2)
        result = self.test_session.get_obs()
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertEqual(result, expected)

        t3 = t1 + TimeDelta(10 * 60., format='sec')
        t4 = t2 + TimeDelta(10 * 60., format='sec')
        self.test_session.add_obs(t3, t4)

        result_mult = self.test_session.get_obs(starttime=t1, stoptime=t4)
        self.assertEqual(len(result_mult), 2)

        result_orig = self.test_session.get_obs(obsid=obsid)
        self.assertEqual(len(result_orig), 1)
        result_orig = result_orig[0]
        self.assertEqual(result_orig, expected)

    def test_error_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')
        self.assertRaises(ValueError, self.test_session.add_obs, 'foo', t2)
        self.assertRaises(ValueError, self.test_session.add_obs, t1, 'foo')


if __name__ == '__main__':
    unittest.main()
