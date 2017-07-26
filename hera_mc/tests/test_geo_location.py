# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.geo_location and geo_handling`.


"""

from __future__ import absolute_import, division, print_function

import unittest

from hera_mc import geo_location, geo_handling, mc, cm_transfer


class test_geo(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)
        cm_transfer._initialization(self.test_session)

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()

    def test_add_part(self):
        self.test_session.add(geo_location.GeoLocation())

    def test_cofa(self):
        h = geo_handling.Handling(self.test_session)
        cofa = h.cofa()
        self.assertTrue('cofa' in cofa.station_name.lower())

    def test_get_location(self):
        h = geo_handling.Handling(self.test_session)
        located = h.get_location(['HH0'], 'now')
        self.assertTrue(located[0].station_name == 'HH0')


if __name__ == '__main__':
    unittest.main()
