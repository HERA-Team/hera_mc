# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.geo_location and geo_handling`.


"""

from __future__ import absolute_import, division, print_function

import unittest

from hera_mc import geo_location, geo_handling, mc


class test_geo(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()

    def test_add_part(self):
        self.test_session.add(geo_location.GeoLocation())

    #def test_cofa(self):
    #    h = geo_handling.Handling(self.test_db)
    #    h.cofa(False)
    #    self.assertTrue('cofa' in cofa.station_name.lower())

    #def test_get_location(self):
    #    h = geo_handling.Handling(self.test_db)
    #    located = geo_handling.get_location(['HH0'])
    #    self.assertTrue(located[0].station_name=='HH0')

    # def test_commit_part(self):
    #     part = connections.Parts()
    #     part.hpn ='happy_thing'
    #     part.manufacture_date = 'Oct 26, 2011'
    #     part.kind = 'vapor'
    #     print(part)
    #     self.test_session.add(part)
    #     self.test_session.commit()

if __name__ == '__main__':
    unittest.main()
