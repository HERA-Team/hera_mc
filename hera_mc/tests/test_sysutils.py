# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.geo_location and geo_handling`."""

from __future__ import absolute_import, division, print_function

import os.path
import subprocess
from argparse import Namespace

import six
import pytest
import numpy as np

from .. import (cm_sysutils, cm_partconnect, cm_hookup, cm_utils, utils,
                cm_sysdef)


@pytest.fixture(scope='function')
def sys_handle(mcsession):
    return cm_sysutils.Handling(mcsession)


def test_ever_fully_connected(sys_handle):
    now_list = sys_handle.get_all_fully_connected_at_date(
        at_date='now', hookup_type='parts_paper')
    assert len(now_list) == 1


def test_publish_summary(sys_handle):
    msg = sys_handle.publish_summary()
    assert msg == 'Not on "main"'


def test_random_update(sys_handle):
    si = cm_sysutils.SystemInfo()
    si.update_arrays(None)


def test_other_hookup(sys_handle, mcsession, capsys):
    at_date = cm_utils.get_astropytime('2017-07-03')
    hookup = cm_hookup.Hookup(session=mcsession)
    hookup.reset_memory_cache(None)
    assert hookup.cached_hookup_dict is None
    hu = hookup.get_hookup(
        ['A23'], 'H', 'all', at_date=at_date, exact_match=True,
        force_new_cache=True, hookup_type='parts_paper')
    hookup.show_hookup(hu, cols_to_show=['station'], state='all',
                       revs=True, ports=True)
    captured = capsys.readouterr()
    assert 'HH23:A <ground' in captured.out.strip()
    hu = hookup.get_hookup(
        'A23,A24', 'H', 'all', at_date=at_date, exact_match=True, force_db=True,
        hookup_type='parts_paper')
    assert 'A23:H' in hu.keys()
    hookup.reset_memory_cache(hu)
    assert (hookup.cached_hookup_dict['A23:H'].hookup['e'][0].upstream_part
            == 'HH23')
    hu = hookup.get_hookup('cached', 'H', 'pol', force_new_cache=False,
                           hookup_type='parts_paper')
    hookup.show_hookup(hu, state='all', output_format='csv')
    captured = capsys.readouterr()
    assert '1096484416' in captured.out.strip()
    hookup.cached_hookup_dict = None
    hookup._hookup_cache_to_use()
    hookup.show_hookup(hu, output_format='html')
    captured = capsys.readouterr()
    assert 'DF8B2' in captured.out.strip()
    hookup.show_hookup({}, cols_to_show=['station'], state='all',
                       revs=True, ports=True)
    captured = capsys.readouterr()
    assert 'None found' in captured.out.strip()
    hufc = hookup.get_hookup_from_db(['HH'], 'active', 'e', at_date='now')
    assert len(hufc.keys()) == 9
    hufc = hookup.get_hookup_from_db(['N23'], 'active', 'e', at_date='now')
    assert len(hufc.keys()) == 1
    hufc = hookup.get_hookup_from_db(['SNPZ'], 'active', 'all',
                                     at_date='2019/02/21')
    assert len(hufc.keys()) == 4
    hufc = hookup.get_hookup_from_db(['SNPZ'], 'active', 'e',
                                     at_date='2019/04/01')
    assert len(hufc.keys()) == 4
    hufc = hookup.get_hookup_from_db(['PAM723'], 'A', 'all',
                                     at_date='2017/12/31')
    assert len(hufc.keys()) == 0
    hufc = hookup.get_hookup_from_db(['RO1A1E'], 'A', 'n', at_date='now')
    assert len(hufc.keys()) == 0
    hookup.hookup_type = None
    hookup._hookup_cache_file_OK()
    assert hookup.hookup_type == 'parts_paper'


def test_hookup_dossier(sys_handle, capsys):
    sysdef = cm_sysdef.Sysdef()
    hude = cm_hookup.HookupDossierEntry(entry_key='testing:key', sysdef=sysdef)
    hude.get_hookup_type_and_column_headers('x', 'rusty_scissors')
    captured = capsys.readouterr()
    assert 'Parts did not conform to any hookup_type' in captured.out.strip()
    print(hude)
    captured = capsys.readouterr()
    assert '<testing:key:' in captured.out.strip()
    hude.get_part_in_hookup_from_type('rusty_scissors', include_revs=True,
                                      include_ports=True)
    hude.columns = {'x': 'y', 'hu': 'b', 'm': 'l'}
    hude.hookup['hu'] = []
    hude.hookup['hu'].append(Namespace(
        downstream_part='shoe', down_part_rev='testing',
        downstream_input_port='nail', upstream_output_port='screw'))
    xret = hude.get_part_in_hookup_from_type('b', include_revs=True,
                                             include_ports=True)
    assert xret['hu'] == 'shoe:testing<screw'

    # test errors
    hude = cm_hookup.HookupDossierEntry(entry_key='testing:key', sysdef=sysdef)
    hude_dict = hude._to_dict()

    pytest.raises(ValueError, cm_hookup.HookupDossierEntry,
                  entry_key='testing:key', input_dict=hude_dict)
    pytest.raises(ValueError, cm_hookup.HookupDossierEntry, sysdef=sysdef,
                  input_dict=hude_dict)
    pytest.raises(ValueError, cm_hookup.HookupDossierEntry,
                  entry_key='testing:key')
    pytest.raises(ValueError, cm_hookup.HookupDossierEntry, sysdef=sysdef)


def test_sysdef(sys_handle, mcsession):
    sysdef = cm_sysdef.Sysdef()
    part = Namespace(hpn='N0', rev='A', part_type='node')
    part.connections = Namespace(input_ports=['loc0', '@mars'], output_ports=[])
    hl = sysdef.handle_redirect_part_types(part, 'now', mcsession)
    assert len(hl) == 3
    part.hpn = 'RI123ZE'
    sysdef.setup(part, port_query='e')
    assert sysdef.pol == 'e'
    part.hpn = 'RI123Z'
    part.part_type = 'cable-post-amp(in)'
    sysdef.setup(part, port_query='e', hookup_type='parts_paper')
    assert sysdef.pol is None
    sysdef.setup(part, port_query='all', hookup_type='parts_paper')
    assert sysdef.this_hookup_type == 'parts_paper'
    part.hpn = 'doorknob'
    part.part_type = 'node'
    sysdef.setup(part, port_query='all')
    assert 'e' in sysdef.pol
    sysdef.setup(part, port_query='e')
    assert 'e' in sysdef.pol
    part.connections.input_ports = ['@loc1', 'top', 'bottom']
    sysdef.setup(part, port_query='e')
    assert 'e' in sysdef.pol
    rg = Namespace(direction='up', part='apart', rev='A', port='e1', pol='e')
    op = [Namespace(upstream_part='apart', upstream_output_port='eb',
                    downstream_part='bpart', downstream_input_port='e1')]
    op.append(Namespace(upstream_part='aprt', upstream_output_port='eb',
                        downstream_part='bprt', downstream_input_port='ea'))
    rg.port = 'e4'
    A = Namespace(hpn='apart', part_type='front-end')
    B = [Namespace(hpn='apart', part_type='cable-rfof'),
         Namespace(hpn='bpart', part_type='cable-rfof')]
    xxx = sysdef.next_connection(op, rg, A, B)
    assert xxx is None
    rg.port = 'rug'
    op[0].downstream_input_port = 'rug'
    xxx = sysdef.next_connection(op, rg, A, B)
    assert xxx is None
    pytest.raises(ValueError, sysdef.find_hookup_type, 'dull_knife',
                  'parts_not')
    part = Namespace(part_type='nope')
    pytest.raises(ValueError, sysdef.setup, part, port_query='nope',
                  hookup_type='parts_hera')


def test_hookup_cache_file_info(sys_handle, mcsession):
    hookup = cm_hookup.Hookup(session=mcsession)
    hookup.hookup_cache_file_info()
    hookup.reset_memory_cache(None)
    hookup.at_date = cm_utils.get_astropytime('2017-07-03')
    hookup.hookup_type = None
    hookup._hookup_cache_to_use()


def test_some_fully_connected(sys_handle):
    x = sys_handle.get_fully_connected_location_at_date('HH701', '2019/02/21')
    assert x.antenna_number == 701


def test_correlator_info(sys_handle):
    corr_dict = sys_handle.get_cminfo_correlator(hookup_type='parts_hera')
    ant_names = corr_dict['antenna_names']
    assert len(ant_names) == 4

    corr_inputs = corr_dict['correlator_inputs']

    stn_types = corr_dict['station_types']

    index = np.where(np.array(ant_names) == 'HH703')[0]
    assert len(index) == 1
    index = index[0]

    assert stn_types[index] == 'herahexn'

    assert corr_inputs[index] == ('e6>SNPZ000042', 'n4>SNPZ000042')

    assert ([int(name.split('HH')[1]) for name in ant_names]
            == corr_dict['antenna_numbers'])

    assert set(corr_dict['antenna_numbers']) == set([701, 703, 704, 705])

    assert corr_dict['cm_version'] is not None

    # cm_version should be the same as the git hash of m&c for the test data
    mc_dir = os.path.dirname(os.path.realpath(__file__))
    mc_git_hash = subprocess.check_output(['git', '-C', mc_dir, 'rev-parse',
                                           'HEAD'],
                                          stderr=subprocess.STDOUT).strip()

    # In Python 3, we sometimes get Unicode, sometimes bytes
    if isinstance(mc_git_hash, six.binary_type):
        mc_git_hash = utils.bytes_to_str(mc_git_hash)

    assert corr_dict['cm_version'] == mc_git_hash

    expected_keys = ['antenna_numbers', 'antenna_names', 'station_types',
                     'correlator_inputs', 'antenna_utm_datum_vals', 'epoch',
                     'antenna_utm_tiles', 'antenna_utm_eastings',
                     'antenna_utm_northings', 'antenna_positions',
                     'cm_version', 'cofa_lat', 'cofa_lon', 'cofa_alt']
    assert set(corr_dict.keys()) == set(expected_keys)

    cofa = sys_handle.cofa()[0]
    assert cofa.lat == corr_dict['cofa_lat']
    assert cofa.lon == corr_dict['cofa_lon']
    assert cofa.elevation == corr_dict['cofa_alt']


def test_get_pam_from_hookup(sys_handle, mcsession):
    hookup = cm_hookup.Hookup(mcsession)
    hud = hookup.get_hookup(['HH23'], at_date='2017-07-03', exact_match=True,
                            hookup_type='parts_paper')
    pams = hud[list(hud.keys())[0]].get_part_in_hookup_from_type(
        'post-amp', include_ports=True, include_revs=True)
    assert len(pams) == 2
    # the actual pam number (the thing written on the case)
    assert pams['e'] == 'ea>PAM75123:B<eb'


def test_get_pam_info(sys_handle, mcsession):
    sys_h = cm_sysutils.Handling(mcsession)
    pams = sys_h.get_part_at_station_from_type(
        'HH23', '2017-07-03', 'post-amp', include_ports=False,
        hookup_type='parts_paper')
    assert len(pams) == 1
    # the actual pam number (the thing written on the case)
    assert pams['HH23:A']['e'] == 'PAM75123'


def test_apriori_antenna(sys_handle, mcsession, capsys):
    cm_partconnect.update_apriori_antenna('HH2', 'needs_checking',
                                          '1214482618', session=mcsession)
    d = sys_handle.get_apriori_antenna_status_for_rtp('needs_checking')
    assert d == 'HH2'
    g = sys_handle.get_apriori_antenna_status_set()
    assert g['needs_checking'][0] == 'HH2'
    pytest.raises(ValueError, cm_partconnect.update_apriori_antenna,
                  'HH3', 'not_one', '1214482618', session=mcsession)
    g = sys_handle.get_apriori_status_for_antenna('HH2')
    assert g == 'needs_checking'
    cm_partconnect.update_apriori_antenna(
        'HH2', 'needs_checking', '1214482818', '1214483000', session=mcsession)
    pytest.raises(ValueError, cm_partconnect.update_apriori_antenna,
                  'HH2', 'needs_checking', '1214482838', session=mcsession)
    print(cm_partconnect.AprioriAntenna())
    captured = capsys.readouterr()
    assert '<None:' in captured.out.strip()
