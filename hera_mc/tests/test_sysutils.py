# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for hera_mc.cm_sysutils and hookup."""

import os.path
import subprocess
from argparse import Namespace

import pytest
import numpy as np

from .. import (cm_sysutils, cm_partconnect, cm_hookup, cm_utils, utils,
                cm_sysdef, cm_dossier, cm_active, cm_redis_corr,
                watch_dog, node)
from .. tests import requires_redis
from .. tests import TEST_DEFAULT_REDIS_HOST
import redis


@pytest.fixture(scope='function')
def sys_handle(mcsession):
    return cm_sysutils.Handling(mcsession)


@requires_redis
def test_set_redis_cminfo(mcsession):
    redishost = TEST_DEFAULT_REDIS_HOST
    rsession = redis.Redis(redishost)
    rsession.hmset('testing_corr:map', {'snap_host': b'{"SNPB000701":"heraNode700Snap700"}'})
    cm_redis_corr.set_redis_cminfo(redishost=redishost, session=mcsession, testing=True)
    test_out = rsession.hget('testing_corr:map', 'ant_to_snap')
    assert b'{"host": "SNPA000700", "channel": 0}' in test_out
    test_out = rsession.hget('testing_cminfo', 'cofa_lat')
    assert b'-30.72' in test_out
    test_out = rsession.hget('testing_corr:map', 'snap_to_ant')
    assert b'heraNode700Snap700' in test_out
    snap_info = 'e2>SNPC000008'
    redis_info = rsession.hget('corr:map', 'not_there')
    host, adc = cm_redis_corr.snap_part_to_host_input(part=snap_info, redis_info=redis_info)
    assert host == 'SNPC000008'
    host, adc = cm_redis_corr.snap_part_to_host_input(part=snap_info, redis_info=None)
    assert host == 'SNPC000008'
    assert adc == 1
    test_out = rsession.hget('testing_corr:map', 'all_snap_inputs')
    assert b'SNPC000702": [0, 1, 2, 3, 4, 5]' in test_out


def test_watch_dog(mcsession):
    ns = node.NodeSensor()
    ns.time = int(cm_utils.get_astropytime('2020-09-18').gps)
    ns.node = 700
    ns.top_sensor_temp = 28.0
    ns.middle_sensor_temp = None
    ns.bottom_sensor_temp = 32.0
    ns.humidity_sensor_temp = 46.0
    ns.humidity = 80.0
    mcsession.add(ns)
    mcsession.commit()
    msg = watch_dog.node_temperature(at_date=None, at_time=0.0,
                                     temp_threshold=45.0, time_threshold=10000.0,
                                     To=['test@hera.edu'], testing=True, session=mcsession)
    assert msg.startswith("From: hera@lists.berkeley.edu")
    msg = watch_dog.node_temperature(at_date='2020/09/19', at_time=0.0,
                                     temp_threshold=45.0, time_threshold=10000.0,
                                     To=['test@hera.edu'], testing=True, session=mcsession)
    assert msg.startswith("From: hera@lists.berkeley.edu")
    msg = watch_dog.node_temperature(at_date='2020/09/19', at_time=0.0,
                                     temp_threshold=45.0, time_threshold=0.0,
                                     To=['test@hera.edu'], testing=True, session=mcsession)
    assert msg is None


def test_ever_fully_connected(sys_handle):
    now_list = sys_handle.get_connected_stations(
        at_date='now', hookup_type='parts_hera')
    assert len(now_list) == 12


def test_publish_summary(sys_handle):
    msg = sys_handle.publish_summary()
    assert msg is None


def test_random_update(sys_handle):
    si = cm_sysutils.SystemInfo()
    si.update_arrays(None)


def test_sys_method_notes(mcsession):
    hookup = cm_hookup.Hookup(session=mcsession)
    hu = hookup.get_hookup('HH700')
    hu['HH700:A'].hookup['E<ground'] = []
    x = hookup.show_hookup(hu)
    assert x is None
    hookup.active.load_info()
    hookup.active.info['HH700:A'] = [cm_partconnect.PartInfo(hpn='HH700', hpn_rev='A',
                                                             comment='Comment3',
                                                             posting_gpstime=1232532198)]
    x = hookup.show_notes(hu)
    assert x.splitlines()[1].strip().startswith('HH700:A')
    hookup.active = None
    notes = hookup.get_notes(hu)
    assert list(notes.keys())[0] == 'HH700:A'
    prf = hookup._proc_hpnlist('default', True)
    assert prf[0][1] == 'HA'


def test_other_hookup(sys_handle, mcsession, capsys):
    hookup = cm_hookup.Hookup(session=mcsession)
    assert hookup.cached_hookup_dict is None
    test_ret = hookup.hookup_cache_file_OK(None)
    assert not test_ret
    hu = hookup.get_hookup(['A700'], 'all', at_date='now', exact_match=True,
                           hookup_type='parts_hera')
    out = hookup.show_hookup(hu, cols_to_show=['station'], state='all',
                             revs=True, ports=True)
    assert 'HH700:A <ground' in out
    hu = hookup.get_hookup('A700,A701', 'all', at_date='now', exact_match=True,
                           hookup_type='parts_hera')
    assert 'A700:H' in hu.keys()
    hookup.write_hookup_cache_to_file(log_msg='For testing.')
    hu = hookup.get_hookup('HH', 'all', at_date='now', exact_match=True, use_cache=True)
    assert len(hu) == 0
    hookup.hookup_type = None
    test_ret = hookup.hookup_cache_file_OK({'hookup_type': 'parts_test', 'at_date_gps': 1269541796})
    assert not test_ret
    hookup.hookup_type = 'not this one'
    hookup.read_hookup_cache_from_file()
    captured = capsys.readouterr()
    assert '<<<Cache is NOT' in captured.out.strip()
    hu = hookup.get_hookup('cache', pol='all', hookup_type='parts_hera')
    out = hookup.show_hookup(hu, state='all', sortby='station', output_format='csv')
    out = out.splitlines()[6].strip('"')
    assert out.startswith('HH702')
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
    gptf = hookup._get_part_types_found([])
    assert len(gptf) == 0
    x = hookup._get_port(Namespace(port=None), 'A')
    assert x is None
    hookup.hookup_list_to_cache = ['A1']
    x = hookup._requested_list_OK_for_cache(['B1'])
    assert x is False
    x = hookup.get_hookup_from_db('N91', 'N', 'now')
    assert len(x) == 0


def test_hookup_notes(mcsession, capsys):
    hookup = cm_hookup.Hookup(session=mcsession)
    hu = hookup.get_hookup(['HH'])
    notes = hookup.get_notes(hu)
    assert len(notes) == 13
    print(hookup.show_notes(hu))
    captured = capsys.readouterr()
    assert '---HH700:A---' in captured.out.strip()


def test_hookup_dossier(sys_handle, capsys):
    sysdef = cm_sysdef.Sysdef()
    hude = cm_dossier.HookupEntry(entry_key='testing:key', sysdef=sysdef)
    hude.get_hookup_type_and_column_headers('x', 'rusty_scissors')
    captured = capsys.readouterr()
    assert 'Parts did not conform to any hookup_type' in captured.out.strip()
    print(hude)
    captured = capsys.readouterr()
    assert '<testing:key:' in captured.out.strip()
    hude.get_part_from_type('rusty_scissors', include_revs=True,
                            include_ports=True)
    hude.columns = {'x': 'y', 'hu': 'b', 'm': 'l'}
    hude.hookup['hu'] = []
    hude.hookup['hu'].append(Namespace(
        downstream_part='shoe', down_part_rev='testing',
        downstream_input_port='nail', upstream_output_port='screw'))
    xret = hude.get_part_from_type('b', include_revs=True,
                                   include_ports=True)
    assert xret['hu'] == 'shoe:testing<screw'
    test_part = Namespace(hpn='ABC', hpn_rev='X', hptype='node')
    sysdef.hookup_type = 'parts_hera'
    hl = sysdef.handle_redirect_part_types(test_part, Namespace(connections={}))
    assert len(hl) == 0

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


def test_hookup_misc(mcsession):
    hookup = cm_hookup.Hookup(mcsession)
    hookup.col_list = ['antenna', 'front-end']
    sk_ret = hookup._sort_hookup_display('antenna,front-end', {})
    assert len(sk_ret) == 0
    hookup.hookup_type = 'test-hookup'
    test_current = Namespace(direction='up', key='', part=['E'], rev='', hptype='type-a',
                             port='x', pol='E', allowed_ports=['y'], type='')
    options = ['y']
    hookup.sysdef.single_pol_labeled_parts['test-hookup'] = ['type-a']
    test_ret = hookup._get_port(test_current, options)
    assert test_ret == 'y'


def test_which_node(capsys, mcsession):
    ant_node = cm_sysutils.which_node(701, mcsession)
    assert ant_node[701][1] == 'N700'
    ant_node = cm_sysutils.which_node('1,2,701', mcsession)
    an_print = cm_sysutils.formatted__which_node__string(ant_node)
    assert 'Not installed (N00)' in an_print
    ant_node = {700: ['N700', 'N700'], 701: ['N701', 'N700']}
    cm_sysutils.print_which_node(ant_node)
    captured = capsys.readouterr()
    assert 'Warning:  Antenna 701' in captured.out.strip()
    na_dict = {'N700': ['HH700'], 'N701': ['HH700']}
    pytest.raises(ValueError, cm_sysutils._find_ant_node, 700, na_dict)


def test_sysdef(sys_handle, mcsession):
    sysdef = cm_sysdef.Sysdef(hookup_type='parts_hera')
    active = cm_active.ActiveData(session=mcsession)
    active.load_parts(at_date=None)
    active.load_connections(at_date=None)
    part = Namespace(hpn='N700', hpn_rev='A', hptype='node')
    part.connections = Namespace(input_ports=['loc0', 'mars'],
                                 output_ports=[])
    hl = sysdef.handle_redirect_part_types(part, active)
    print(hl)
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
    rg.port = 'rug'
    op[0].downstream_input_port = 'rug'
    pytest.raises(ValueError, sysdef.find_hookup_type, 'dull_knife',
                  'parts_not')
    part = Namespace(part_type='nope')
    pytest.raises(ValueError, sysdef.setup, part, pol='nope',
                  hookup_type='parts_hera')
    curr = active.set_times(cm_utils.get_astropytime('2017-07-03'))
    assert int(curr) == 1183075218
    active.load_apriori('now')
    assert active.apriori['HH700:A'].status == 'not_connected'
    ap = cm_partconnect.AprioriAntenna()
    ap.antenna = 'HH700'
    ap.start_gpstime = int(cm_utils.get_astropytime('2019-01-01').gps)
    ap.status = 'duplicate'
    mcsession.add(ap)
    mcsession.commit()
    with pytest.raises(ValueError) as apdup:
        active.load_apriori('now')
    assert str(apdup.value).startswith("HH700:A already has an active apriori state")
    all_ports = sysdef.get_all_ports()
    assert 'ground' in all_ports
    sysdef.hptype = 'not-real'
    sysdef.setup(sysdef, hookup_type='parts_hera')
    assert len(sysdef.ppkeys) == 0
    gprt = sysdef.get_ports('e', 'not-real')
    assert len(gprt) == 0


def test_sysutil_node(capsys, mcsession):
    xni = cm_sysutils.node_info(['N91'], mcsession)
    assert not len(xni['N91']['ants-file'])
    apn = cm_sysutils.node_antennas(session=mcsession)
    assert 'N10' in apn.keys()
    apn = cm_sysutils.node_antennas(source='hookup', session=mcsession)
    assert 'N700' in apn.keys()
    xni = cm_sysutils.node_info([10], mcsession)
    assert 'nodes' in xni.keys()
    testns = Namespace(hookup={'not-a-port': None})
    testhu = {'this-test': testns}
    eret = cm_sysutils._get_dict_elements('this-test', testhu, 'a', 'b')
    assert len(eret['a']) == 0
    xa = cm_sysutils.node_info('active', mcsession)
    assert 'N700' in xa['nodes']
    xa = cm_sysutils.node_info('all', mcsession)
    assert 'N00' in xa['nodes']
    testns.hookup['@<middle'] = [Namespace(upstream_part='UP', downstream_part='DN')]
    testhu = {'this-test': testns}
    eret = cm_sysutils._get_dict_elements('this-test', testhu, 'dn', 'up')
    assert eret['up'] == 'UP'
    eret = cm_sysutils._get_dict_elements('this-test', testhu, 'up', 'dn')
    assert eret['up'] == 'UP'
    xni = cm_sysutils.node_info([701], mcsession)
    assert 'SNPD000703' in xni.keys()
    xni = cm_sysutils.node_info([700], mcsession)
    assert 'SNPA000700' in xni.keys()
    cm_sysutils.print_node(xni)
    captured = capsys.readouterr()
    assert '| Node   |' in captured.out.strip()
    xni['N700']['wr'] = 'notthere'
    xni['N700']['arduino'] = 'notthere'
    xni['N700']['snaps'].append('notthere')
    xni['nodes'].append('NONODE')
    xni['NONODE'] = {'snaps': [], 'ncm': '', 'wr': '', 'arduino': ''}
    cm_sysutils.print_node(xni)
    captured = capsys.readouterr()
    assert 'notthere' in captured.out.strip()
    cm_sysutils.print_node(xni, output_format='csv')
    captured = capsys.readouterr()
    assert captured.out.strip().startswith('"Node"')
    cm_sysutils.print_node(xni, output_format='html')
    captured = capsys.readouterr()
    assert captured.out.strip().startswith('<html>')


def test_hookup_cache_file_info(sys_handle, mcsession):
    hookup = cm_hookup.Hookup(session=mcsession)
    cfi = hookup.hookup_cache_file_info()
    assert 'json does not exist' in cfi


def test_correlator_info(sys_handle):
    corr_dict = sys_handle.get_cminfo_correlator(hookup_type='parts_hera')
    ant_names = corr_dict['antenna_names']
    assert len(ant_names) == 12

    corr_inputs = corr_dict['correlator_inputs']

    index = np.where(np.array(ant_names) == 'HH703')[0]
    assert len(index) == 1
    index = index[0]

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
    if isinstance(mc_git_hash, bytes):
        mc_git_hash = utils.bytes_to_str(mc_git_hash)

    assert corr_dict['cm_version'] == mc_git_hash

    expected_keys = ['antenna_numbers', 'antenna_names', 'antenna_positions',
                     'correlator_inputs', 'cm_version',
                     'cofa_lat', 'cofa_lon', 'cofa_alt']
    assert set(corr_dict.keys()) == set(expected_keys)

    cofa = sys_handle.cofa()[0]
    assert cofa.lat == corr_dict['cofa_lat']
    assert cofa.lon == corr_dict['cofa_lon']
    assert cofa.elevation == corr_dict['cofa_alt']


def test_get_pam_from_hookup(sys_handle, mcsession):
    hookup = cm_hookup.Hookup(mcsession)
    hud = hookup.get_hookup(['HH701'], at_date='2019-07-03', exact_match=True,
                            hookup_type='parts_hera')
    pams = hud[list(hud.keys())[0]].get_part_from_type(
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
    assert pams['HH701:A']['E<ground'] == 'PAM701'


@pytest.mark.parametrize(
    'status', [
        "dish_maintenance",
        "dish_ok",
        "RF_maintenance",
        "RF_ok",
        "digital_maintenance",
        "digital_ok",
        "calibration_maintenance",
        "calibration_ok",
        "calibration_triage"
    ]
)
def test_apriori_antenna(sys_handle, mcsession, capsys, status):
    cm_partconnect.update_apriori_antenna('HH701', status,
                                          '1214382618', session=mcsession)
    d = sys_handle.get_apriori_antenna_status_for_rtp(status)
    assert d == 'HH701'
    g = sys_handle.get_apriori_antenna_status_set()
    assert g[status][0] == 'HH701'

    g = sys_handle.get_apriori_status_for_antenna('HH701')
    assert g == status


@pytest.mark.parametrize(
    'status', [
        "passed_checks",
        "needs_checking",
        "known_bad",
        "not_connected",
    ]
)
def test_apriori_antenna_old(sys_handle, mcsession, capsys, status):
    with pytest.raises(ValueError) as cm:
        cm_partconnect.update_apriori_antenna(
            'HH701', status, '1214382618', session=mcsession
        )
    assert str(cm.value).startswith(
        "The status '{0}' is deprecated. "
        "Please select one of the new status values {1}."
        .format(status, cm_partconnect.get_apriori_antenna_status_enum())
    )


def test_apriori_antenna_unknown_status(sys_handle, mcsession, capsys):
    with pytest.raises(ValueError) as cm:
        cm_partconnect.update_apriori_antenna(
            'HH3', 'not_one', '1214482618', session=mcsession
        )
    assert str(cm.value).startswith("Antenna apriori status must be in")


def test_apriori_update_after_stopped(sys_handle, mcsession, capsys):
    cm_partconnect.update_apriori_antenna(
        'HH700', "RF_ok", '1214482818', '1214483000', session=mcsession
    )
    with pytest.raises(ValueError) as cm:
        cm_partconnect.update_apriori_antenna(
            'HH700', "RF_ok", '1214482838', session=mcsession
        )
    assert str(cm.value).startswith("Stop time must be None to update AprioriAntenna")


def test_apriori_repr(capsys):
    print(cm_partconnect.AprioriAntenna())
    captured = capsys.readouterr()
    assert '<None:' in captured.out.strip()
