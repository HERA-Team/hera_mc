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

        self.test_session.add_paper_temps(t1, temp_list)
        self.test_session.add_paper_temps(t2, temp2_list)

        expected = [mc.PaperTemperatures(gps_time=t1.gps, jd_time=t1.jd, **temp_dict)]
        result = self.test_session.get_paper_temps(t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(result, expected)

        result = self.test_session.get_paper_temps(t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

        expected2 = [mc.PaperTemperatures(gps_time=t1.gps, jd_time=t1.jd,
                                          **temp_dict),
                     mc.PaperTemperatures(gps_time=t2.gps, jd_time=t2.jd,
                                          **temp2_dict)]
        result = self.test_session.get_paper_temps(t1 - TimeDelta(3.0, format='sec'),
                                                   stoptime=t2 + TimeDelta(1.0, format='sec'))
        self.assertEqual(result, expected2)


if __name__ == '__main__':
    unittest.main()
