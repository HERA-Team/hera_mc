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

    def setUp(self):
        super(TestGeo, self).setUp()

        # Add a test elelment
        self.test_element_stn = 'test_element'
        self.test_element_prefix = 'TE'
        st = geo_location.StationType()
        st.station_type_name = self.test_element_stn
        st.prefix = self.test_element_prefix
        self.test_session.add(st)
        self.test_session.commit()
        gl = geo_location.GeoLocation()
        gl.station_name = self.test_element_prefix + '_ELEMENT'
        self.test_element_station_name = gl.station_name
        gl.station_type_name = self.test_element_stn
        gl.datum = 'WGS84'
        gl.tile = '34J'
        gl.northing = 6601181.0
        gl.easting = 541007.0
        gl.elevation = 1051.69
        gl.created_gpstime = 1172530000
        self.test_session.add(gl)
        self.test_session.commit()

        self.h = geo_handling.Handling(self.test_session)

    def test_cofa(self):
        cofa = self.h.cofa()
        self.assertTrue('cofa' in cofa.station_name.lower())

    def test_get_location(self):
        located = self.h.get_location([self.test_element_station_name], 'now')
        self.assertTrue(located[0].station_name == self.test_element_station_name)

    def test_update_new(self):
        nte = self.test_element_prefix + '_new_test_element'
        data = [[nte, 'station_name', nte],
                [nte, 'station_type_name', self.test_element_stn],
                [nte, 'datum', 'WGS84'],
                [nte, 'tile', '34J'],
                [nte, 'northing', 6600000.0],
                [nte, 'easting', 541000.0],
                [nte, 'elevation', 1050.0],
                [nte, 'created_gpstime', 1172530000]]
        geo_location.update(self.test_session, data, add_new_geo=True)
        located = self.h.get_location([nte], 'now')
        self.assertTrue(located[0].station_type_name == self.test_element_stn)

    def test_update_update(self):
        data = [[self.test_element_station_name, 'elevation', 1100.0]]
        geo_location.update(self.test_session, data, add_new_geo=False)
        located = self.h.get_location([self.test_element_station_name], 'now')
        self.assertTrue(located[0].elevation == 1100.0)

    def test_station_types(self):
        self.h.get_station_types(add_stations=True)
        self.assertTrue(self.h.station_types['COFA']['Name'] == 'cofa')

    def test_is_in_geo_location(self):
        found_it = self.h.is_in_geo_location(self.test_element_station_name)
        self.assertTrue(found_it)


if __name__ == '__main__':
    unittest.main()
