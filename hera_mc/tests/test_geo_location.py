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
        found_it = self.h.is_in_database(self.test_element_station_name, 'geo_location')
        self.assertTrue(found_it)

    def test_ever_fully_connected(self):
        now_list = self.h.get_all_fully_connected_at_date(at_date='now')
        ever_list = self.h.get_all_fully_connected_ever()

        self.assertEqual(len(now_list), 1)
        self.assertEqual(len(ever_list), 2)

        ever_ends = [loc['stop_date'] for loc in ever_list]
        # The '==' notation below is required (rather than the pep8 suggestion of 'is') for the test to pass.
        self.assertEqual(len(np.where(np.array(ever_ends) == None)[0]), len(now_list))

        now_station_names = [loc['station_name'] for loc in now_list]
        ever_station_names = [loc['station_name'] for loc in ever_list]
        for name in now_station_names:
            self.assertTrue(name in ever_station_names)

        # check that every location fully connected now appears in fully connected ever
        for loc_i, loc in enumerate(now_list):
            this_station_list = [ever_list[i] for i in np.where(np.array(ever_station_names) == loc['station_name'])[0]]
            this_station_starts = [loc['start_date'] for loc in this_station_list]
            this_index = np.where(np.array(this_station_starts) == loc['start_date'])[0]

            if len(this_index) == 1:
                this_index = this_index[0]
                print(loc)
                print(this_station_list[this_index])
                self.assertEqual(this_station_list[this_index], loc)

    def test_correlator_info(self):
        corr_dict = self.h.get_cminfo_correlator(cm_csv_path=mc.test_data_path)

        ant_names = corr_dict['antenna_names']
        self.assertEqual(len(ant_names), 1)

        corr_inputs = corr_dict['correlator_inputs']

        stn_types = corr_dict['station_types']

        index = np.where(np.array(ant_names) == 'HH0')[0]
        self.assertEqual(len(index), 1)
        index = index[0]

        self.assertEqual(stn_types[index], 'herahex')

        self.assertEqual(corr_inputs[index], ('DF8B2', 'DF8B1'))

        self.assertEqual([int(name.split('HH')[1]) for name in ant_names],
                         corr_dict['antenna_numbers'])

        self.assertEqual(set(corr_dict['antenna_numbers']),
                         set([0]))

        self.assertTrue(corr_dict['cm_version'] is not None)

        # cm_version should be the same as the git hash of m&c for the test data
        mc_dir = os.path.dirname(os.path.realpath(__file__))
        mc_git_hash = subprocess.check_output(['git', '-C', mc_dir, 'rev-parse', 'HEAD'],
                                              stderr=subprocess.STDOUT).strip()
        self.assertEqual(corr_dict['cm_version'], mc_git_hash)

        expected_keys = ['antenna_numbers', 'antenna_names', 'station_types',
                         'correlator_inputs', 'antenna_utm_datum_vals',
                         'antenna_utm_tiles', 'antenna_utm_eastings',
                         'antenna_utm_northings', 'antenna_positions',
                         'cm_version', 'cofa_lat', 'cofa_lon', 'cofa_alt']
        self.assertEqual(set(corr_dict.keys()), set(expected_keys))

        cofa = self.h.cofa()[0]
        self.assertEqual(cofa.lat, corr_dict['cofa_lat'])
        self.assertEqual(cofa.lon, corr_dict['cofa_lon'])
        self.assertEqual(cofa.elevation, corr_dict['cofa_alt'])


if __name__ == '__main__':
    unittest.main()
