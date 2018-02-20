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
from hera_mc import geo_location, geo_handling, mc, cm_transfer, part_connect
from hera_mc import cm_hookup
from hera_mc.tests import TestHERAMC
from astropy.time import Time


class TestGeo(TestHERAMC):

    def setUp(self):
        super(TestGeo, self).setUp()

        # Add a test element
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
        self.h = geo_handling.Handling(self.test_session, testing=True)
        pa1 = part_connect.Parts()
        self.upte = 'TE_ELEMENT'
        self.upterev = 'A'
        pa1.hpn = self.upte
        pa1.hpn_rev = self.upterev
        pa1.hptype = 'station'
        pa1.start_gpstime = Time('2017-07-01 01:00:00', scale='utc').gps
        self.test_session.add(pa1)
        pa2 = part_connect.Parts()
        self.dna = 'A_ELEMENT'
        self.dnarev = 'A'
        pa2.hpn = self.dna
        pa2.hpn_rev = self.dnarev
        pa2.hptype = 'antenna'
        pa2.start_gpstime = Time('2017-07-01 01:00:00', scale='utc').gps
        self.test_session.add(pa2)
        self.test_session.commit()
        co = part_connect.Connections()
        co.upstream_part = self.upte
        co.up_part_rev = self.upterev
        co.upstream_output_port = 'output'
        co.downstream_part = self.dna
        co.down_part_rev = self.dnarev
        co.downstream_input_port = 'input'
        co.start_gpstime = Time('2017-07-01 01:00:00', scale='utc').gps
        self.test_session.add(co)
        self.test_session.commit()

    def test_cofa(self):
        cofa = self.h.cofa()[0]
        self.assertTrue('cofa' in cofa.station_name.lower())

        # test that function works the same as method
        cofa_func = geo_handling.cofa(session=self.test_session)[0]
        self.assertTrue(cofa.isclose(cofa_func))

    def test_get_location(self):
        located = self.h.get_location([self.test_element_station_name], 'now')
        self.assertTrue(located[0].station_name == self.test_element_station_name)

        # test that function works the same as method
        located_func = geo_handling.get_location([self.test_element_station_name],
                                                 'now', session=self.test_session)
        for loc_i in range(len(located)):
            self.assertTrue(located[loc_i].isclose(located_func[loc_i]))
        rlf = self.h.print_loc_info(located_func)
        self.assertTrue(rlf)
        rlf = self.h.print_loc_info(None)
        self.assertFalse(rlf)

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
        self.h.get_station_types()
        self.assertTrue(self.h.station_types['cofa']['Prefix'] == 'COFA')

    def test_get_ants_installed_since(self):
        query_date = Time('2017-05-01 01:00:00', scale='utc')
        ants_in = self.h.get_ants_installed_since(query_date, station_types_to_check=['HH'])
        print(ants_in)
        self.assertTrue(len(ants_in) == 3)

    def test_plotting(self):
        stations_to_plot = ['HH0']
        query_date = Time('2017-08-25 01:00:00', scale='utc')
        state_args = {'verbosity': 'm',
                      'xgraph': 'E',
                      'ygraph': 'N',
                      'station_types': ['HH'],
                      'marker_color': 'r',
                      'marker_shape': '*',
                      'marker_size': 12,
                      'show_state': 'active',
                      'show_label': 'name',
                      'fig_num': 1}
        self.h.plot_stations(stations_to_plot, query_date, xgraph='E', ygraph='N', show_label='name',
                             marker_color='k', marker_shape='*', marker_size=14)
        self.h.plot_stations(stations_to_plot, query_date, xgraph='E', ygraph='N', show_label='num',
                             marker_color='k', marker_shape='*', marker_size=14)
        self.h.plot_stations(stations_to_plot, query_date, xgraph='E', ygraph='N', show_label='ser',
                             marker_color='k', marker_shape='*', marker_size=14)
        self.h.plot_stations(stations_to_plot, query_date, xgraph='E', ygraph='N', show_label='other_thing',
                             marker_color='k', marker_shape='*', marker_size=14)
        self.h.plot_station_types(query_date=query_date, station_types_to_use=['HH'],
                                  xgraph='E', ygraph='N',
                                  show_state='active', show_label='name')

    def test_is_in_database(self):
        self.assertTrue(self.h.is_in_database(self.test_element_station_name, 'geo_location'))
        self.assertTrue(self.h.is_in_database(self.upte, 'connections'))
        self.assertRaises(ValueError, self.h.is_in_database, self.upte, 'wrong_one')

    def test_find_antenna_station_pair(self):
        ant, rev = self.h.find_antenna_at_station(self.upte, 'now')
        self.assertTrue(ant == self.dna)
        stn = self.h.find_station_of_antenna(self.dna, 'now')
        self.assertTrue(stn == self.upte)


if __name__ == '__main__':
    unittest.main()
