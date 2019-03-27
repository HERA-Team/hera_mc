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
import sys
import numpy as np
from astropy.time import Time, TimeDelta
from argparse import Namespace
from contextlib import contextmanager
from .. import (geo_location, sys_handling, mc, cm_transfer, part_connect,
                cm_hookup, cm_utils, cm_revisions, utils, cm_sysdef)
from . import TestHERAMC


# define a context manager for checking stdout
# from https://stackoverflow.com/questions/4219717/how-to-assert-output-with-nosetest-unittest-in-python
@contextmanager
def captured_output():
    new_out, new_err = six.StringIO(), six.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


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
        hu = hookup.get_hookup(['A23'], 'H', 'all', exact_match=True, force_new_cache=True, levels=True)
        with captured_output() as (out, err):
            hookup.show_hookup(hu, cols_to_show=['station', 'level'], state='all', levels=True, revs=True, ports=True)
        self.assertTrue('HH23:A <ground' in out.getvalue().strip())
        hu = hookup.get_hookup(['A23'], 'H', 'all', exact_match=True, force_db_at_date='now')
        self.assertTrue('A23:H' in hu.keys())
        hookup.reset_memory_cache(hu)
        self.assertEqual(hookup.cached_hookup_dict['A23:H'].hookup['e'][0].upstream_part, 'HH23')
        hu = hookup.get_hookup('cached', 'H', 'pol', force_new_cache=False, levels=True)
        with captured_output() as (out, err):
            hookup.show_hookup(hu)
        self.assertTrue('1096484416' in out.getvalue().strip())
        with captured_output() as (out, err):
            hu = hookup.get_hookup('A23,A23', 'H', 'all', force_new_cache=False, levels=True)
        self.assertTrue('Correlator' in out.getvalue().strip())
        hookup.cached_hookup_dict = None
        hookup.determine_hookup_cache_to_use()
        with captured_output() as (out, err):
            hookup.show_hookup(hu)
        self.assertTrue('1096484416' in out.getvalue().strip())
        with captured_output() as (out, err):
            hookup.show_hookup({}, cols_to_show=['station', 'level'], state='all', levels=True, revs=True, ports=True)
        self.assertTrue('None found' in out.getvalue().strip())
        hufc = hookup.get_hookup_from_db(['HH'], 'active', '_x', at_date='now')
        self.assertEqual(len(hufc.keys()), 0)
        hufc = hookup.get_hookup_from_db(['N23'], 'active', 'e', at_date='now')
        self.assertEqual(len(hufc.keys()), 0)

    def test_hookup_dossier(self):
        hude = cm_hookup.HookupDossierEntry('testing:key')
        with captured_output() as (out, err):
            hude.get_hookup_type_and_column_headers('x', 'rusty_scissors')
        self.assertTrue('Parts did not conform to any hookup_type' in out.getvalue().strip())
        hude.get_part_in_hookup_from_type('rusty_scissors', include_revs=True, include_ports=True)
        hude.columns = {'x': 'y', 'hu': 'b', 'm': 'l'}
        hude.hookup['hu'] = []
        hude.hookup['hu'].append(Namespace(downstream_part='shoe', down_part_rev='testing',
                                 downstream_input_port='nail', upstream_output_port='screw'))
        xret = hude.get_part_in_hookup_from_type('b', include_revs=True, include_ports=True)
        self.assertEqual(xret['hu'], 'shoe:testing<screw')

    def test_sysdef(self):
        part = Namespace(hpn='rusty_scissors')
        part.connections = Namespace(input_ports=['e', '@loc', 'n'], output_ports=[])
        with captured_output() as (out, err):
            cm_sysdef.handle_redirect_part_types(part)
        self.assertTrue('rusty_scissors' in out.getvalue().strip())
        with captured_output() as (out, err):
            xxx = cm_sysdef.get_port_pols_to_do(part, port_query='nail')
        self.assertTrue('Invalid port query' in out.getvalue().strip())
        part.hpn = 'RI123ZE'
        xxx = cm_sysdef.get_port_pols_to_do(part, port_query='e')
        self.assertEqual(len(xxx), 1)
        part.hpn = 'RI123Z'
        xxx = cm_sysdef.get_port_pols_to_do(part, port_query='e')
        self.assertEqual(xxx, None)
        part.hpn = 'doorknob'
        xxx = cm_sysdef.get_port_pols_to_do(part, port_query='pol')
        self.assertTrue('e' in xxx)
        xxx = cm_sysdef.get_port_pols_to_do(part, port_query='e')
        self.assertTrue('e' in xxx)
        part.connections.input_ports = ['@loc1', 'top', 'bottom']
        xxx = cm_sysdef.get_port_pols_to_do(part, port_query='e')
        self.assertTrue('e' in xxx)
        rg = Namespace(direction='up', part='apart', rev='A', port='e1', pol='e')
        op = [Namespace(upstream_part='apart', upstream_output_port='eb', downstream_part='bpart', downstream_input_port='e1')]
        op.append(Namespace(upstream_part='aprt', upstream_output_port='eb', downstream_part='bprt', downstream_input_port='ea'))
        rg.port = 'e4'
        xxx = cm_sysdef.next_connection(op, rg)
        self.assertEqual(xxx, None)
        rg.port = 'rug'
        op[0].downstream_input_port = 'rug'
        xxx = cm_sysdef.next_connection(op, rg)
        self.assertEqual(xxx.upstream_part, 'apart')

    def test_hookup_cache_file_info(self):
        hookup = cm_hookup.Hookup(at_date='now', session=self.test_session)
        hookup.hookup_cache_file_info()
        hookup.reset_memory_cache(None)
        hookup.determine_hookup_cache_to_use()

    def test_some_fully_connected(self):
        x = self.sys_h.get_fully_connected_location_at_date('HH98', 'now')
        self.assertEqual(x, None)

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
                         'correlator_inputs', 'antenna_utm_datum_vals', 'epoch',
                         'antenna_utm_tiles', 'antenna_utm_eastings',
                         'antenna_utm_northings', 'antenna_positions',
                         'cm_version', 'cofa_lat', 'cofa_lon', 'cofa_alt']
        self.assertEqual(set(corr_dict.keys()), set(expected_keys))

        cofa = self.sys_h.cofa()[0]
        self.assertEqual(cofa.lat, corr_dict['cofa_lat'])
        self.assertEqual(cofa.lon, corr_dict['cofa_lon'])
        self.assertEqual(cofa.elevation, corr_dict['cofa_alt'])

    def test_dubitable(self):
        dubitable_ants = self.sys_h.get_dubitable_list()
        self.assertTrue(dubitable_ants is None)
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
        pams = hud[list(hud.keys())[0]].get_part_in_hookup_from_type('post-amp', include_ports=True, include_revs=True)
        self.assertEqual(len(pams), 2)
        self.assertEqual(pams['e'], 'ea>PAM75123:B<eb')  # the actual pam number (the thing written on the case)

    def test_get_pam_info(self):
        sys_h = sys_handling.Handling(self.test_session)
        pams = sys_h.get_part_at_station_from_type('HH23', '2017-07-03', 'post-amp', include_ports=False)
        self.assertEqual(len(pams), 1)
        self.assertEqual(pams['HH23:A']['e'], 'PAM75123')  # the actual pam number (the thing written on the case)

    def test_system_comments(self):
        comments = self.sys_h.system_comments()
        self.assertEqual(comments[1], 'K')


if __name__ == '__main__':
    unittest.main()
