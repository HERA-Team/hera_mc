# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.geo_location and geo_handling`.
"""

from __future__ import absolute_import, division, print_function

import unittest
import os.path
import subprocess
import numpy as np

from .. import geo_location, geo_handling, mc, cm_transfer, part_connect
from .. import cm_hookup
from ..tests import TestHERAMC
from astropy.time import Time


class TestGeo(TestHERAMC):

    def setUp(self):
        super(TestGeo, self).setUp()
        self.h = geo_handling.Handling(self.test_session)

    def test_cofa(self):
        self.h.get_station_types()
        station_types = [type.lower() for type in self.h.station_types.keys()]
        self.assertTrue('cofa' in station_types)

        cofa = self.h.cofa()[0]

        # test that function works the same as method
        cofa_func = geo_handling.cofa(session=self.test_session)[0]
        self.assertTrue(cofa.isclose(cofa_func))

    def test_update_new(self):
        nte = 'HH_new_test_element'
        data = [[nte, 'station_name', nte],
                [nte, 'station_type_name', 'herahex'],
                [nte, 'datum', 'WGS84'],
                [nte, 'tile', '34J'],
                [nte, 'northing', 6600000.0],
                [nte, 'easting', 541000.0],
                [nte, 'elevation', 1050.0],
                [nte, 'created_gpstime', 1172530000]]
        geo_location.update(self.test_session, data, add_new_geo=True)
        located = self.h.get_location([nte], 'now')
        self.assertTrue(located[0].station_type_name == 'herahex')

    def test_update_update(self):
        data = [["HH23", 'elevation', 1100.0]]
        geo_location.update(self.test_session, data, add_new_geo=False)
        located = self.h.get_location(["HH23"], 'now')
        self.assertTrue(located[0].elevation == 1100.0)

    def test_station_types(self):
        self.h.get_station_types()
        self.assertTrue(self.h.station_types['cofa']['Prefix'] == 'COFA')

    def test_get_ants_installed_since(self):
        query_date = Time('2017-05-01 01:00:00', scale='utc')
        ants_in = self.h.get_ants_installed_since(query_date, station_types_to_check=['HH'])
        self.assertTrue(len(ants_in) == 3)

    def test_plotting(self):
        stations_to_plot = ['HH0']
        query_date = Time('2017-08-25 01:00:00', scale='utc')
        stations = self.h.get_location(stations_to_plot, query_date)
        self.h.plot_stations(stations, xgraph='E', ygraph='N', show_label='name',
                             marker_color='k', marker_shape='*', marker_size=14)
        self.h.plot_stations(stations, xgraph='E', ygraph='N', show_label='num',
                             marker_color='k', marker_shape='*', marker_size=14)
        self.h.plot_stations(stations, xgraph='E', ygraph='N', show_label='ser',
                             marker_color='k', marker_shape='*', marker_size=14)
        self.h.plot_stations(stations, xgraph='E', ygraph='N', show_label='other_thing',
                             marker_color='k', marker_shape='*', marker_size=14)
        self.h.plot_station_types(query_date=query_date, station_types_to_use=['HH'],
                                  xgraph='E', ygraph='N',
                                  show_state='active', show_label='name')
        self.h.print_loc_info(None)
        self.h.print_loc_info(stations)

    def test_parse_station_types(self):
        st = self.h.parse_station_types_to_check('all')
        self.assertTrue('container' in st)
        st = self.h.parse_station_types_to_check('hh')
        self.assertTrue('herahexe' in st)

    def test_get_active_stations(self):
        active = self.h.get_active_stations('now', ['HH'])
        self.assertEqual(active[0].station_name, 'HH0')

    def test_is_in_database(self):
        self.assertTrue(self.h.is_in_database('HH23', 'geo_location'))
        self.assertTrue(self.h.is_in_database('HH23', 'connections'))
        self.assertFalse(self.h.is_in_database('BB0', 'geo_location'))
        self.assertRaises(ValueError, self.h.is_in_database, 'HH666', 'wrong_one')

    def test_find_antenna_station_pair(self):
        ant, rev = self.h.find_antenna_at_station('HH23', 'now')
        self.assertTrue(ant == 'A23')
        ant, rev = self.h.find_antenna_at_station('BB23', 'now')
        self.assertEqual(ant, None)
        stn = self.h.find_station_of_antenna('A23', 'now')
        self.assertTrue(stn == 'HH23')
        stn = self.h.find_station_of_antenna(23, 'now')
        self.assertTrue(stn == 'HH23')


if __name__ == '__main__':
    unittest.main()
