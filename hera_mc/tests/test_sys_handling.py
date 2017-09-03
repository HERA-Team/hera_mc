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
from hera_mc import geo_location, sys_handling, mc, cm_transfer, part_connect
from hera_mc import cm_hookup, cm_utils, cm_revisions
from hera_mc.tests import TestHERAMC
from astropy.time import Time


class TestGeo(TestHERAMC):

    def setUp(self):
        super(TestGeo, self).setUp()
        self.h = sys_handling.Handling(self.test_session)

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

    def test_get_pam_from_hookup(self):
        h = sys_handling.Handling()
        at_date = cm_utils._get_astropytime('2017-09-03')
        fc = cm_revisions.get_full_revision('HH51', at_date, h.session)
        hu = fc[0].hookup
        H = cm_hookup.Hookup()
        pams = H.get_pam_from_hookup(hu)
        self.assertEqual(len(pams), 2)
        self.assertEqual(pams['e'][0], 'RI4A1E')  # the rcvr cable (which tells us location)
        self.assertEqual(pams['e'][1], 'RCVR93')  # the actual pam number (the thing written on the case)

    def test_get_pam_info(self):
        h = sys_handling.Handling()
        pams = h.get_pam_info('HH23', '2017-09-03')
        self.assertEqual(len(pams), 2)
        self.assertEqual(pams['e'][0], 'RI5A3E')  # the rcvr cable (which tells us location)
        self.assertEqual(pams['e'][1], 'PAM75103')  # the actual pam number (the thing written on the case)


if __name__ == '__main__':
    unittest.main()
