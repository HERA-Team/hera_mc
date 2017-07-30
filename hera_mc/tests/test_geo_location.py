# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.geo_location and geo_handling`.


"""

from __future__ import absolute_import, division, print_function

import unittest

from hera_mc import geo_location, geo_handling, mc, cm_transfer
from hera_mc.tests import TestHERAMC


class TestGeo(TestHERAMC):

    def test_add_cofa(self):
        gl = geo_location.GeoLocation()
        gl.station_name = 'cofa_null'
        gl.station_type_name = 'cofa'
        gl.created_gpstime = 1172539000
        self.test_session.add(gl)
        self.test_session.commit()
        self.assertTrue

    def test_add_loc(self):
        gl = geo_location.GeoLocation()
        gl.station_name = 'ELEMENT'
        gl.station_type_name = 'herahex'
        gl.created_gpstime = 1172539000
        self.test_session.add(gl)
        self.test_session.commit()
        self.assertTrue

    def test_cofa(self):
        h = geo_handling.Handling(self.test_session)
        cofa = h.cofa()
        self.assertTrue('cofa' in cofa.station_name.lower())

    def test_get_location(self):
        h = geo_handling.Handling(self.test_session)
        located = h.get_location(['ELEMENT'], 'now')
        self.assertTrue(located[0].station_name == 'ELEMENT')


if __name__ == '__main__':
    unittest.main()
