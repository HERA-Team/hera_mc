# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.observations`.

"""
from __future__ import absolute_import, division, print_function

import unittest
import numpy as np
from math import floor
from sqlalchemy import desc
from sqlalchemy.orm import sessionmaker
from astropy.time import Time, TimeDelta
from astropy.coordinates import EarthLocation

from hera_mc import mc, geo_handling, utils
from hera_mc.observations import Observation, HeraObsView
from hera_mc.tests import TestHERAMC


class TestObservation(TestHERAMC):

    def setUp(self):
        super(TestObservation, self).setUp()

    def test_new_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        t3 = t1 + TimeDelta(1e-3, format='sec')
        t4 = t2 + TimeDelta(1e-3, format='sec')

        h = geo_handling.Handling(session=self.test_session)
        hera_cofa = h.cofa()[0]

        obs1 = Observation.create(t1, t2, utils.calculate_obsid(t1), hera_cofa)
        obs2 = Observation.create(t3, t4, utils.calculate_obsid(t3), hera_cofa)
        self.assertFalse(obs1 == obs2)

    def test_add_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        # generated test hera_lat, hera_lon using the output of geo.py -c
        # with this website: http://www.uwgb.edu/dutchs/usefuldata/ConvertUTMNoOZ.HTM

        obsid_calc = int(floor(t1.gps))
        obsid = utils.calculate_obsid(t1)
        self.assertEqual(obsid_calc, obsid)
        t1.location = EarthLocation.from_geodetic(21.4283038269, -30.7215261207)

        expected = Observation(obsid=obsid, starttime=t1.gps, stoptime=t2.gps,
                               jd_start=t1.jd,
                               lst_start_hr=t1.sidereal_time('apparent').hour)

        self.test_session.add_obs(t1, t2, obsid)
        result = self.test_session.get_obs()
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertEqual(result.length, 120.0)
        self.assertTrue(result.isclose(expected))

        t3 = t1 + TimeDelta(10 * 60., format='sec')
        t4 = t2 + TimeDelta(10 * 60., format='sec')
        self.test_session.add_obs(t3, t4, utils.calculate_obsid(t3))

        result_mult = self.test_session.get_obs_by_time(starttime=t1, stoptime=t4)
        self.assertEqual(len(result_mult), 2)

        result_most_recent = self.test_session.get_obs_by_time(most_recent=True)
        self.assertEqual(result_most_recent[0], result_mult[1])

        result_orig = self.test_session.get_obs(obsid=obsid)
        self.assertEqual(len(result_orig), 1)
        result_orig = result_orig[0]
        self.assertTrue(result_orig.isclose(expected))

    def test_obs_view(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        self.test_session.add_obs(t1, t2, utils.calculate_obsid(t1))

        view_result = self.test_session.query(HeraObsView).all()
        view_result = view_result[0]

        self.assertTrue(np.abs(t1.unix - view_result.starttime_unix) < 5)
        self.assertTrue(np.abs(t2.unix - view_result.stoptime_unix) < 5)

    def test_obs_view_automap(self):
        # just tests that a call to the view on the default DB doesn't error
        # -- makes sure the alembic revision worked
        default_db = mc.connect_to_mc_db(None)
        engine = default_db.engine
        conn = engine.connect()
        trans = conn.begin()

        Session = sessionmaker(bind=engine)
        session = Session()
        view_result = session.query(HeraObsView).order_by(desc('obsid')).limit(1)

    def test_error_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')
        self.assertRaises(ValueError, self.test_session.add_obs, 'foo', t2, utils.calculate_obsid(t1))
        self.assertRaises(ValueError, self.test_session.add_obs, t1, 'foo', utils.calculate_obsid(t1))
        self.assertRaises(ValueError, self.test_session.add_obs, t1, t2, 'foo')
        self.assertRaises(ValueError, utils.calculate_obsid, 'foo')
        self.assertRaises(ValueError, self.test_session.add_obs, t1, t2, utils.calculate_obsid(t1) + 2)
        self.assertRaises(TypeError, self.test_session.get_obs_by_time, most_recent=t1)
        self.assertRaises(TypeError, self.test_session.get_obs_by_time, t1)


if __name__ == '__main__':
    unittest.main()
