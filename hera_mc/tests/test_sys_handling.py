# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.geo_location and geo_handling`.


"""

from __future__ import absolute_import, division, print_function

import unittest
import os.path
import subprocess
import six
import numpy as np
from astropy.time import Time, TimeDelta

from .. import (geo_location, sys_handling, mc, cm_transfer, part_connect,
                cm_hookup, cm_utils, cm_revisions, utils)
from . import TestHERAMC


class TestSys(TestHERAMC):

    def setUp(self):
        super(TestSys, self).setUp()
        self.sys_h = sys_handling.Handling(self.test_session)

    def test_ever_fully_connected(self):
        now_list = self.sys_h.get_all_fully_connected_at_date(at_date='now')
        self.assertEqual(len(now_list), 1)

    def test_publish_summary(self):
        msg = self.sys_h.publish_summary()
        self.assertEqual(msg, 'Not on "main"')

    def test_random_update(self):
        si = sys_handling.StationInfo()
        si.update_stn(None)
        si.update_arrays(None)

    def test_other_hookup(self):
        at_date = cm_utils.get_astropytime('2017-07-03')
        hookup = cm_hookup.Hookup(at_date=at_date, session=self.test_session)
        hookup.reset_memory_cache(None)
        self.assertEqual(hookup.cached_hookup_dict, None)
        hu = hookup.get_hookup(['A23'], 'H', 'pol', exact_match=True, force_new=True)
        hookup.reset_memory_cache(hu)
        self.assertEqual(hookup.cached_hookup_dict['A23:H'].hookup['e'][0].upstream_part, 'HH23')

    def test_hookup_cache_file_info(self):
        hookup = cm_hookup.Hookup(at_date='now', session=self.test_session)
        hookup.hookup_cache_file_info()

    def test_some_fully_connected(self):
        x = self.sys_h.get_fully_connected_location_at_date('HH98', 'now')
        self.sys_h.H = None
        x = self.sys_h.get_fully_connected_location_at_date('HH98', 'now')

    def test_correlator_info(self):
        corr_dict = self.sys_h.get_cminfo_correlator()
        ant_names = corr_dict['antenna_names']
        self.assertEqual(len(ant_names), 1)

        corr_inputs = corr_dict['correlator_inputs']

        stn_types = corr_dict['station_types']

        index = np.where(np.array(ant_names) == 'HH0')[0]
        self.assertEqual(len(index), 1)
        index = index[0]

        self.assertEqual(stn_types[index], 'herahexw')

        self.assertEqual(corr_inputs[index], ('input>DF8B2', 'input>DF8B1'))

        self.assertEqual([int(name.split('HH')[1]) for name in ant_names],
                         corr_dict['antenna_numbers'])

        self.assertEqual(set(corr_dict['antenna_numbers']),
                         set([0]))

        self.assertTrue(corr_dict['cm_version'] is not None)

        # cm_version should be the same as the git hash of m&c for the test data
        mc_dir = os.path.dirname(os.path.realpath(__file__))
        mc_git_hash = subprocess.check_output(['git', '-C', mc_dir, 'rev-parse', 'HEAD'],
                                              stderr=subprocess.STDOUT).strip()

        # In Python 3, we sometimes get Unicode, sometimes bytes
        if isinstance(mc_git_hash, six.binary_type):
            mc_git_hash = utils.bytes_to_str(mc_git_hash)

        self.assertEqual(corr_dict['cm_version'], mc_git_hash)

        expected_keys = ['antenna_numbers', 'antenna_names', 'station_types',
                         'correlator_inputs', 'antenna_utm_datum_vals',
                         'antenna_utm_tiles', 'antenna_utm_eastings',
                         'antenna_utm_northings', 'antenna_positions',
                         'cm_version', 'cofa_lat', 'cofa_lon', 'cofa_alt']
        self.assertEqual(set(corr_dict.keys()), set(expected_keys))

        cofa = self.sys_h.cofa()[0]
        self.assertEqual(cofa.lat, corr_dict['cofa_lat'])
        self.assertEqual(cofa.lon, corr_dict['cofa_lon'])
        self.assertEqual(cofa.elevation, corr_dict['cofa_alt'])

    def test_cm_utils(self):
        import datetime
        a, b, c, d = cm_utils.split_connection_key('a:b:c:d')
        self.assertEqual(c[0], 'c')
        a = cm_utils.listify(None)
        self.assertEqual(a, None)
        a = cm_utils.listify([1, 2, 3])
        self.assertEqual(a[0], 1)
        a = cm_utils.stringify(None)
        self.assertEqual(a, None)
        a = cm_utils.stringify('a')
        self.assertEqual(a[0], 'a')
        a = cm_utils.get_astropytime(datetime.datetime.now())
        a = cm_utils.get_astropytime('2018-01-01', '12:00')
        a = cm_utils.get_date_from_pair(None, None)
        self.assertEqual(a, None)
        a = cm_utils.get_date_from_pair(1, 2)
        self.assertEqual(a, 1)
        a = cm_utils.get_date_from_pair(1, 2, 'latest')
        self.assertEqual(a, 2)

    def test_dubitable(self):
        at_date = cm_utils.get_astropytime('2017-01-01')
        part_connect.update_dubitable(self.test_session, at_date.gps, ['1', '2', '3'])
        dubitable_ants = self.sys_h.get_dubitable_list()
        dubitable_ants_list = dubitable_ants.split(",")
        self.assertEqual(len(dubitable_ants_list), 3)
        dubitable_ants = self.sys_h.get_dubitable_list(return_full=True)
        self.assertEqual(len(dubitable_ants[2]), 3)

    def test_get_pam_from_hookup(self):
        at_date = cm_utils.get_astropytime('2017-07-03')
        hookup = cm_hookup.Hookup(at_date, self.test_session)
        stn = 'HH23'
        hud = hookup.get_hookup([stn], exact_match=True)
        pams = hud[list(hud.keys())[0]].get_part_in_hookup_from_type('post-amp', include_ports=False)
        self.assertEqual(len(pams), 2)
        self.assertEqual(pams['e'], 'PAM75123')  # the actual pam number (the thing written on the case)

    def test_get_pam_info(self):
        sys_h = sys_handling.Handling(self.test_session)
        pams = sys_h.get_part_at_station_from_type('HH23', '2017-07-03', 'post-amp', include_ports=False)
        self.assertEqual(len(pams), 1)
        self.assertEqual(pams['HH23:A']['e'], 'PAM75123')  # the actual pam number (the thing written on the case)

    def test_system_comments(self):
        comments = self.sys_h.system_comments()
        self.assertEqual(comments[0], 'N')


if __name__ == '__main__':
    unittest.main()
