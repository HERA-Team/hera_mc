from sqlalchemy.orm import Session
import unittest
import hera_mc.mc as mc
import math
from astropy.time import Time, TimeDelta
import ephem


class test_hera_mc(unittest.TestCase):
    def setUp(self):
        self.test_db = mc.DB_declarative()
        self.test_db.create_tables()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = Session(bind=self.test_conn)

        self.real_db = mc.DB_automap()
        self.real_conn = self.real_db.engine.connect()
        self.real_trans = self.real_conn.begin()
        self.real_session = Session(bind=self.real_conn)

    def tearDown(self):
        # rollback - everything that happened with the Session above
        # (including calls to commit()) is rolled back.
        self.test_trans.rollback()
        self.real_trans.rollback()

        # return connection to the Engine
        self.test_conn.close()
        self.real_conn.close()

        self.test_db.drop_tables()

    def test_db_sane(self):
        from hera_mc.db_check import is_sane_database
        assert is_sane_database(self.test_db.Base, self.real_session) is True

    def test_add_obs(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        obsid = math.floor(t1.gps)
        hera = ephem.Observer()
        hera.lon = mc.HERA_LON
        hera.lat = mc.HERA_LAT
        hera.date = t1.datetime
        lst_start = float(repr(hera.sidereal_time()))/(15*ephem.degree)

        expected = [mc.HeraObs(obsid=obsid, starttime=t1.jd,
                               stoptime=t2.jd, lststart=lst_start)]

        # first test against test_db
        self.test_db.add_obs(starttime=t1, stoptime=t2,
                             session=self.test_session)
        result = self.test_db.get_obs(all=True, session=self.test_session)
        self.assertEqual(result, expected)

        # now test against real_db
        self.real_db.add_obs(starttime=t1, stoptime=t2,
                             session=self.real_session)
        result = self.real_db.get_obs(all=True, session=self.real_session)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
