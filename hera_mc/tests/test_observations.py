# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.observations`.

"""
import unittest

import numpy as np
from astropy.time import Time, TimeDelta
from astropy.coordinates import EarthLocation

from hera_mc import mc, observations


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

    def test_add_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        # t1.delta_ut1_utc = mc.iers_a.ut1_utc(t1)
        # t2.delta_ut1_utc = mc.iers_a.ut1_utc(t2)

        from math import floor
        obsid = floor(t1.gps)
        t1.location = EarthLocation.from_geodetic(observations.HERA_LON, observations.HERA_LAT)

        expected = [observations.Observation(obsid=obsid, start_time_jd=t1.jd,
                                             stop_time_jd=t2.jd,
                                             lst_start_hr=t1.sidereal_time('apparent').hour)]

        self.test_session.add(observations.Observation.new_with_astropy(t1, t2))
        result = self.test_session.get_obs()
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
