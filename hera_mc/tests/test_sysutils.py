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
                cm_sysdef, cm_dossier, cm_active)


@pytest.fixture(scope='function')
def sys_handle(mcsession):
    return cm_sysutils.Handling(mcsession)


def test_ever_fully_connected(sys_handle):
    now_list = sys_handle.get_all_fully_connected_at_date(
        at_date='now', hookup_type='parts_hera')
    assert len(now_list) == 12


def test_publish_summary(sys_handle):
    msg = sys_handle.publish_summary()
    assert msg == 'Not on "main"'


def test_random_update(sys_handle):
    si = cm_sysutils.SystemInfo()
    si.update_arrays(None)


def test_other_hookup(sys_handle, mcsession, capsys):
    at_date = cm_utils.get_astropytime('2017-07-03')
    hookup = cm_hookup.Hookup(session=mcsession)
    assert hookup.cached_hookup_dict is None

    hu = hookup.get_hookup(['A700'], 'all', at_date='now', exact_match=True,
                           hookup_type='parts_hera')
    out = hookup.show_hookup(hu, cols_to_show=['station'], state='all',
                             revs=True, ports=True)
    assert 'HH700:A <ground' in out
    hu = hookup.get_hookup('A700,A701', 'all', at_date='now', exact_match=True,
                           hookup_type='parts_hera')
    assert 'A700:H' in hu.keys()
    hookup.write_hookup_cache_to_file(log_msg='For testing.')
    hu = hookup.get_hookup('cache', pol='all', hookup_type='parts_hera')
    out = hookup.show_hookup(hu, state='all', output_format='csv')
    assert '1230375618' in out
    out = hookup.show_hookup(hu, output_format='html')
    assert 'NBP700' in out
    out = hookup.show_hookup({}, cols_to_show=['station'], state='all',
                             revs=True, ports=True)
    assert out is None
    hufc = hookup.get_hookup_from_db(['HH'], 'e', at_date='now')
    assert len(hufc.keys()), 13
    hufc = hookup.get_hookup_from_db(['N700'], 'e', at_date='now')
    assert len(hufc.keys()) == 3
    assert hookup.hookup_type, 'parts_hera'


def test_hookup_dossier(sys_handle, capsys):
    sysdef = cm_sysdef.Sysdef()
    hude = cm_dossier.HookupEntry(entry_key='testing:key', sysdef=sysdef)
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
    hude = cm_dossier.HookupEntry(entry_key='testing:key', sysdef=sysdef)
    hude_dict = hude._to_dict()

    pytest.raises(ValueError, cm_dossier.HookupEntry,
                  entry_key='testing:key', input_dict=hude_dict)
    pytest.raises(ValueError, cm_dossier.HookupEntry, sysdef=sysdef,
                  input_dict=hude_dict)
    pytest.raises(ValueError, cm_dossier.HookupEntry,
                  entry_key='testing:key')
    pytest.raises(ValueError, cm_dossier.HookupEntry, sysdef=sysdef)


def test_sysdef(sys_handle, mcsession):
    sysdef = cm_sysdef.Sysdef()
    active = cm_active.ActiveData(session=mcsession)
    active.load_parts(at_date=None)
    active.load_connections(at_date=None)
    part = Namespace(hpn='N700', hpn_rev='A', hptype='node')
    part.connections = Namespace(input_ports=['loc0', '@mars'],
                                 output_ports=[])
    hl = sysdef.handle_redirect_part_types(part, active)
    assert len(hl), 4
    part.hpn = 'doorknob'
    part.part_type = 'node'
    sysdef.setup(part, pol='all')
    assert 'E<loc0' in sysdef.ppkeys
    sysdef.setup(part, pol='e')
    assert 'E<loc0' in sysdef.ppkeys
    part.connections.input_ports = ['@loc1', 'top', 'bottom']
    sysdef.setup(part, pol='e')
    assert 'E<loc0' in sysdef.ppkeys
    rg = Namespace(direction='up', part='apart', rev='A', port='e1', pol='e')
    op = [Namespace(upstream_part='apart', upstream_output_port='eb',
                    downstream_part='bpart', downstream_input_port='e1')]
    op.append(Namespace(upstream_part='aprt', upstream_output_port='eb',
                        downstream_part='bprt', downstream_input_port='ea'))
    rg.port = 'e4'
    A = Namespace(hpn='apart', part_type='front-end')
    B = [Namespace(hpn='apart', part_type='cable-rfof'),
         Namespace(hpn='bpart', part_type='cable-rfof')]
    rg.port = 'rug'
    op[0].downstream_input_port = 'rug'
    pytest.raises(ValueError, sysdef.find_hookup_type, 'dull_knife',
                  'parts_not')
    part = Namespace(part_type='nope')
    pytest.raises(ValueError, sysdef.setup, part, pol='nope',
                  hookup_type='parts_hera')


def test_hookup_cache_file_info(sys_handle, mcsession):
    hookup = cm_hookup.Hookup(session=mcsession)
    cfi = hookup.hookup_cache_file_info()
    assert 'json does not exist' in cfi


def test_some_fully_connected(sys_handle):
    x = sys_handle.get_fully_connected_location_at_date('HH701', '2019/02/21')
    assert x.antenna_number == 701


def test_correlator_info(sys_handle):
    corr_dict = sys_handle.get_cminfo_correlator(hookup_type='parts_hera')
    ant_names = corr_dict['antenna_names']
    assert len(ant_names) == 12

    corr_inputs = corr_dict['correlator_inputs']

    stn_types = corr_dict['station_types']

    index = np.where(np.array(ant_names) == 'HH703')[0]
    assert len(index) == 1
    index = index[0]

    assert stn_types[index] == 'herahexw'
    assert corr_inputs[index] == ('e10>SNPA000700', 'n8>SNPA000700')

    assert ([int(name.split('HH')[1]) for name in ant_names]
            == corr_dict['antenna_numbers'])

    assert set(corr_dict['antenna_numbers']) == set(range(701, 713))

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
    hud = hookup.get_hookup(['HH701'], at_date='2019-07-03', exact_match=True,
                            hookup_type='parts_hera')
    pams = hud[list(hud.keys())[0]].get_part_in_hookup_from_type(
        'post-amp', include_ports=True, include_revs=True)
    assert len(pams) == 2
    # the actual pam number (the thing written on the case)
    assert pams['E<ground'] == 'e>PAM701:A<e'


def test_get_pam_info(sys_handle, mcsession):
    sys_h = cm_sysutils.Handling(mcsession)
    pams = sys_h.get_part_at_station_from_type(
        'HH701', '2019-07-03', 'post-amp', include_ports=False,
        hookup_type='parts_hera')
    assert len(pams) == 1
    # the actual pam number (the thing written on the case)
    assert pams['HH701:A']['E'] == 'PAM701'


def test_apriori_antenna(sys_handle, mcsession, capsys):
    cm_partconnect.update_apriori_antenna('HH701', 'needs_checking',
                                          '1214382618', session=mcsession)
    d = sys_handle.get_apriori_antenna_status_for_rtp('needs_checking')
    assert d == 'HH701'
    g = sys_handle.get_apriori_antenna_status_set()
    assert g['needs_checking'][0] == 'HH701'
    pytest.raises(ValueError, cm_partconnect.update_apriori_antenna,
                  'HH3', 'not_one', '1214482618', session=mcsession)
    g = sys_handle.get_apriori_status_for_antenna('HH701')
    assert g == 'needs_checking'
    cm_partconnect.update_apriori_antenna(
        'HH700', 'needs_checking', '1214482818', '1214483000',
        session=mcsession)
    pytest.raises(ValueError, cm_partconnect.update_apriori_antenna, 'HH700',
                  'needs_checking', '1214482838', session=mcsession)
    print(cm_partconnect.AprioriAntenna())
    captured = capsys.readouterr()
    assert '<None:' in captured.out.strip()
