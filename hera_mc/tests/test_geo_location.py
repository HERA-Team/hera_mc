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

from .. import geo_location, geo_handling, mc, cm_transfer
from ..tests import TestHERAMC, checkWarnings
from astropy.time import Time


class TestGeo(TestHERAMC):

    def setUp(self):
        super(TestGeo, self).setUp()
        self.h = geo_handling.Handling(self.test_session, testing=True)

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

    def test_random(self):
        self.h.start_file('test')

    def test_geo_location(self):
        g = geo_location.GeoLocation()
        g.geo(station_name='TestSetAttr')
        self.assertEqual(g.station_name, 'TESTSETATTR')
        print(g)
        s = geo_location.StationType()
        print(s)
        rv = geo_location.update()
        self.assertFalse(rv)
        rv = geo_location.update(session=self.test_session, data='HH0:Tile')
        self.assertFalse(rv)
        rv = geo_location.update(session=self.test_session, data='HH0:Tile:34J,Elevation:0.0,Northing')
        self.assertTrue(rv)
        rv = geo_location.update(session=self.test_session, data='HHX:Tile:34J')
        self.assertTrue(rv)
        rv = geo_location.update(session=self.test_session, data='HH0:Tile:34J', add_new_geo=True)
        self.assertTrue(rv)
        rv = geo_location.update(session=self.test_session, data='HH0:NotThere:34J')
        self.assertTrue(rv)

    def test_station_types(self):
        self.h.get_station_types()
        self.assertTrue(self.h.station_types['cofa']['Prefix'] == 'COFA')

    def test_get_ants_installed_since(self):
        query_date = Time('2017-05-01 01:00:00', scale='utc')
        ants_in = self.h.get_ants_installed_since(query_date, station_types_to_check=['HH'])
        self.assertEqual(len(ants_in), 7)

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
        self.h.plot_station_types(query_date=query_date, station_types_to_use=['HH'],
                                  xgraph='E', ygraph='N',
                                  show_state='active', show_label='name')
        self.h.print_loc_info(None)
        self.h.print_loc_info(stations)
        self.h.plot_all_stations()
        self.h.set_graph('testit')
        self.assertEqual(self.h.graph, 'testit')
        self.h.plot_all_stations()

    def test_antenna_label(self):
        stations_to_plot = ['HH0']
        query_date = Time('2017-08-25 01:00:00', scale='utc')
        stations = self.h.get_location(stations_to_plot, query_date)
        x = self.h.get_antenna_label('name', stations[0], query_date)
        self.assertEqual(x, 'HH0')
        x = self.h.get_antenna_label('num', stations[0], query_date)
        self.assertEqual(x, '0')
        x = self.h.get_antenna_label('ser', stations[0], query_date)
        self.assertEqual(x, 'H3')

    def test_parse_station_types(self):
        st = self.h.parse_station_types_to_check('all')
        self.assertTrue('container' in st)
        st = self.h.parse_station_types_to_check('hh')
        self.assertTrue('herahexe' in st)

    def test_get_active_stations(self):
        active = self.h.get_active_stations('now', ['HH'], hookup_type='parts_paper')
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
        c = checkWarnings(self.h.find_antenna_at_station, ['HH68', 'now'],
                          message='More than one active connection between station and antenna.\n\tupstream HH68 -> downstream A66\n\tupstream HH68 -> downstream A68')
        self.assertEqual(len(c), 2)
        stn = self.h.find_station_of_antenna('A23', 'now')
        self.assertTrue(stn == 'HH23')
        stn = self.h.find_station_of_antenna(23, 'now')
        self.assertTrue(stn == 'HH23')
        stn = self.h.find_station_of_antenna(1024, 'now')
        self.assertTrue(stn is None)
        self.assertRaises(ValueError, self.h.find_station_of_antenna, 68, 'now')


if __name__ == '__main__':
    unittest.main()
