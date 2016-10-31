import os.path as op
import unittest
import hera_mc
import hera_mc.mc as mc
import math
import numpy as np
from astropy.time import Time, TimeDelta
from astropy.coordinates import EarthLocation


class test_hera_mc(unittest.TestCase):
    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_db.create_tables()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)

    def tearDown(self):
        # rollback - everything that happened with the Session above
        # (including calls to commit()) is rolled back.
        self.test_trans.rollback()

        # return connection to the Engine
        self.test_conn.close()

        self.test_db.drop_tables()

    def test_add_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        # t1.delta_ut1_utc = mc.iers_a.ut1_utc(t1)
        # t2.delta_ut1_utc = mc.iers_a.ut1_utc(t2)

        obsid = math.floor(t1.gps)
        t1.location = EarthLocation.from_geodetic(mc.HERA_LON, mc.HERA_LAT)

        expected = [mc.HeraObs(obsid=obsid, start_time_jd=t1.jd,
                               stop_time_jd=t2.jd,
                               lst_start_hr=t1.sidereal_time('apparent').hour)]

        self.test_session.add_obs(t1, t2)
        result = self.test_session.get_obs()
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
