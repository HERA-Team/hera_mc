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
from .. import (geo_location, cm_sysutils, mc, cm_transfer, cm_partconnect,
                cm_hookup, cm_utils, utils, cm_sysdef)
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
        self.sys_h = cm_sysutils.Handling(self.test_session)

    def test_ever_fully_connected(self):
        now_list = self.sys_h.get_all_fully_connected_at_date(at_date='now', hookup_type='parts_paper')
        self.assertEqual(len(now_list), 1)

    def test_publish_summary(self):
        msg = self.sys_h.publish_summary()
        self.assertEqual(msg, 'Not on "main"')

    def test_random_update(self):
        si = cm_sysutils.StationInfo()
        si.update_stn(None)
        si.update_arrays(None)

    def test_other_hookup(self):
        at_date = cm_utils.get_astropytime('2017-07-03')
        hookup = cm_hookup.Hookup(session=self.test_session)
        hookup.reset_memory_cache(None)
        self.assertEqual(hookup.cached_hookup_dict, None)
        hu = hookup.get_hookup(['A23'], 'H', 'all', at_date=at_date, exact_match=True, force_new_cache=True, hookup_type='parts_paper')
        with captured_output() as (out, err):
            hookup.show_hookup(hu, cols_to_show=['station'], state='all', revs=True, ports=True)
        self.assertTrue('HH23:A <ground' in out.getvalue().strip())
        hu = hookup.get_hookup('A23,A24', 'H', 'all', at_date=at_date, exact_match=True, force_db=True, hookup_type='parts_paper')
        self.assertTrue('A23:H' in hu.keys())
        hookup.reset_memory_cache(hu)
        self.assertEqual(hookup.cached_hookup_dict['A23:H'].hookup['e'][0].upstream_part, 'HH23')
        hu = hookup.get_hookup('cached', 'H', 'pol', force_new_cache=False, hookup_type='parts_paper')
        with captured_output() as (out, err):
            hookup.show_hookup(hu, state='all')
        self.assertTrue('1096484416' in out.getvalue().strip())
        hookup.cached_hookup_dict = None
        hookup._hookup_cache_to_use()
        with captured_output() as (out, err):
            hookup.show_hookup(hu, output_format='html')
        self.assertTrue('DF8B2' in out.getvalue().strip())
        with captured_output() as (out, err):
            hookup.show_hookup({}, cols_to_show=['station'], state='all', revs=True, ports=True)
        self.assertTrue('None found' in out.getvalue().strip())
        hufc = hookup.get_hookup_from_db(['HH'], 'active', 'e', at_date='now')
        self.assertEqual(len(hufc.keys()), 9)
        hufc = hookup.get_hookup_from_db(['N23'], 'active', 'e', at_date='now')
        self.assertEqual(len(hufc.keys()), 1)
        hufc = hookup.get_hookup_from_db(['SNPZ'], 'active', 'all', at_date='2019/02/21')
        self.assertEqual(len(hufc.keys()), 4)
        hufc = hookup.get_hookup_from_db(['SNPZ'], 'active', 'e', at_date='2019/04/01')
        self.assertEqual(len(hufc.keys()), 4)
        hufc = hookup.get_hookup_from_db(['PAM723'], 'A', 'all', at_date='2017/12/31')
        self.assertEqual(len(hufc.keys()), 0)
        hufc = hookup.get_hookup_from_db(['RO1A1E'], 'A', 'n', at_date='now')
        self.assertEqual(len(hufc.keys()), 0)

    def test_hookup_dossier(self):
        sysdef = cm_sysdef.Sysdef()
        hude = cm_hookup.HookupDossierEntry('testing:key', sysdef)
        with captured_output() as (out, err):
            hude.get_hookup_type_and_column_headers('x', 'rusty_scissors')
        self.assertTrue('Parts did not conform to any hookup_type' in out.getvalue().strip())
        with captured_output() as (out, err):
            print(hude)
        self.assertTrue('<testing:key:' in out.getvalue().strip())
        hude.get_part_in_hookup_from_type('rusty_scissors', include_revs=True, include_ports=True)
        hude.columns = {'x': 'y', 'hu': 'b', 'm': 'l'}
        hude.hookup['hu'] = []
        hude.hookup['hu'].append(Namespace(downstream_part='shoe', down_part_rev='testing',
                                 downstream_input_port='nail', upstream_output_port='screw'))
        xret = hude.get_part_in_hookup_from_type('b', include_revs=True, include_ports=True)
        self.assertEqual(xret['hu'], 'shoe:testing<screw')

    def test_sysdef(self):
        sysdef = cm_sysdef.Sysdef()
        part = Namespace(hpn='N0', rev='A', part_type='node')
        part.connections = Namespace(input_ports=['loc0', '@mars'], output_ports=[])
        hl = sysdef.handle_redirect_part_types(part, 'now', self.test_session)
        self.assertTrue(len(hl) == 3)
        part.hpn = 'RI123ZE'
        sysdef.setup(part, port_query='e')
        self.assertEqual(sysdef.pol, 'e')
        part.hpn = 'RI123Z'
        part.part_type = 'cable-post-amp(in)'
        sysdef.setup(part, port_query='e', hookup_type='parts_paper')
        self.assertEqual(sysdef.pol, None)
        sysdef.setup(part, port_query='all', hookup_type='parts_paper')
        self.assertEqual(sysdef.this_hookup_type, 'parts_paper')
        part.hpn = 'doorknob'
        part.part_type = 'node'
        sysdef.setup(part, port_query='all')
        self.assertTrue('e' in sysdef.pol)
        sysdef.setup(part, port_query='e')
        self.assertTrue('e' in sysdef.pol)
        part.connections.input_ports = ['@loc1', 'top', 'bottom']
        sysdef.setup(part, port_query='e')
        self.assertTrue('e' in sysdef.pol)
        rg = Namespace(direction='up', part='apart', rev='A', port='e1', pol='e')
        op = [Namespace(upstream_part='apart', upstream_output_port='eb', downstream_part='bpart', downstream_input_port='e1')]
        op.append(Namespace(upstream_part='aprt', upstream_output_port='eb', downstream_part='bprt', downstream_input_port='ea'))
        rg.port = 'e4'
        A = Namespace(hpn='apart', part_type='front-end')
        B = [Namespace(hpn='apart', part_type='cable-rfof'), Namespace(hpn='bpart', part_type='cable-rfof')]
        xxx = sysdef.next_connection(op, rg, A, B)
        self.assertEqual(xxx, None)
        rg.port = 'rug'
        op[0].downstream_input_port = 'rug'
        xxx = sysdef.next_connection(op, rg, A, B)
        self.assertEqual(xxx, None)
        self.assertRaises(ValueError, sysdef.find_hookup_type, 'dull_knife', 'parts_not')
        part = Namespace(part_type='nope')
        self.assertRaises(ValueError, sysdef.setup, part, port_query='nope', hookup_type='parts_hera')

    def test_hookup_cache_file_info(self):
        hookup = cm_hookup.Hookup(session=self.test_session)
        hookup.hookup_cache_file_info()
        hookup.reset_memory_cache(None)
        hookup.at_date = cm_utils.get_astropytime('2017-07-03')
        hookup.hookup_type = None
        hookup._hookup_cache_to_use()

    def test_some_fully_connected(self):
        x = self.sys_h.get_fully_connected_location_at_date('HH701', '2019/02/21')
        self.assertEqual(x.antenna_number, 701)

    def test_correlator_info(self):
        corr_dict = self.sys_h.get_cminfo_correlator(hookup_type='parts_hera')
        ant_names = corr_dict['antenna_names']
        self.assertEqual(len(ant_names), 4)

        corr_inputs = corr_dict['correlator_inputs']

        stn_types = corr_dict['station_types']

        index = np.where(np.array(ant_names) == 'HH703')[0]
        self.assertEqual(len(index), 1)
        index = index[0]

        self.assertEqual(stn_types[index], 'herahexn')

        self.assertEqual(corr_inputs[index], ('e6>SNPZ000042', 'n4>SNPZ000042'))

        self.assertEqual([int(name.split('HH')[1]) for name in ant_names],
                         corr_dict['antenna_numbers'])

        self.assertEqual(set(corr_dict['antenna_numbers']),
                         set([701, 703, 704, 705]))

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

    def test_get_pam_from_hookup(self):
        hookup = cm_hookup.Hookup(self.test_session)
        hud = hookup.get_hookup(['HH23'], at_date='2017-07-03', exact_match=True, hookup_type='parts_paper')
        pams = hud[list(hud.keys())[0]].get_part_in_hookup_from_type('post-amp', include_ports=True, include_revs=True)
        self.assertEqual(len(pams), 2)
        self.assertEqual(pams['e'], 'ea>PAM75123:B<eb')  # the actual pam number (the thing written on the case)

    def test_get_pam_info(self):
        sys_h = cm_sysutils.Handling(self.test_session)
        pams = sys_h.get_part_at_station_from_type('HH23', '2017-07-03', 'post-amp', include_ports=False, hookup_type='parts_paper')
        self.assertEqual(len(pams), 1)
        self.assertEqual(pams['HH23:A']['e'], 'PAM75123')  # the actual pam number (the thing written on the case)

    def test_system_comments(self):
        comments = self.sys_h.system_comments()
        self.assertEqual(comments[1], 'K')

    def test_apriori_antenna(self):
        cm_partconnect.update_apriori_antenna('HH2', 'needs_checking', '1214482618', session=self.test_session)
        g = self.sys_h.get_apriori_antenna_status_set()
        self.assertEqual(g['needs_checking'][0], 'HH2')
        self.assertRaises(ValueError, cm_partconnect.update_apriori_antenna, 'HH3', 'not_one', '1214482618', session=self.test_session)
        g = self.sys_h.get_apriori_status_for_antenna('HH2')
        self.assertEqual(g, 'needs_checking')
        g = cm_partconnect.AprioriAntenna()
        with captured_output() as (out, err):
            print(g)
        self.assertTrue('<None:' in out.getvalue().strip())
        d = self.sys_h.get_apriori_antenna_status_for_rtp('needs_checking')
        self.assertTrue(d == 'HH2')


if __name__ == '__main__':
    unittest.main()
