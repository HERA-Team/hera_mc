# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.correlator`."""
from __future__ import absolute_import, division, print_function

import os
import copy
import time
import datetime
import hashlib
from math import floor

import pytest
import yaml
import numpy as np
from astropy.time import Time, TimeDelta

from hera_mc import mc, cm_partconnect
import hera_mc.correlator as corr
from hera_mc.data import DATA_PATH
from ..tests import onsite, checkWarnings


@pytest.fixture(scope='module')
def corrcommand():
    return {
        'taking_data': {'state': True,
                        'timestamp': Time(1512770942, format='unix')},
        'phase_switching': {'state': False,
                            'timestamp': Time(1512770944, format='unix')},
        'noise_diode': {'state': True,
                        'timestamp': Time(1512770946, format='unix')},
    }


@pytest.fixture(scope='module')
def corrstate_nonetime():
    return {'taking_data': {'state': False, 'timestamp': None}}


@pytest.fixture(scope='module')
def config():
    config_file = os.path.join(DATA_PATH, 'test_data',
                               'hera_feng_config_example.yaml')
    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)

    return config_file, config


@pytest.fixture(scope='module')
def corrconfig(config):
    return {'time': Time(1512770942, format='unix'),
            'hash': 'testhash', 'config': config[1]}


@pytest.fixture(scope='module')
def init_args():
    return ("Namespace(config_file=None, eth=True, initialize=True, "
            + "mansync=False, noise=False, program=False, "
            + "redishost='redishost', sync=True, tvg=False)")


@pytest.fixture(scope='module')
def snapversion(config, init_args):
    return {
        'udpSender:hera_node_keep_alive.py': {
            'timestamp': datetime.datetime(2019, 4, 2, 19, 7, 17, 438357),
            'version': '0.0.1-1eaa49ea'},
        'hera_corr_f:hera_snap_redis_monitor.py': {
            'timestamp': datetime.datetime(2019, 4, 2, 19, 7, 14, 317679),
            'version': '0.0.1-3c7fdaf6'},
        'udpSender:hera_node_cmd_check.py': {
            'timestamp': datetime.datetime(2019, 4, 2, 19, 7, 17, 631614),
            'version': '0.0.1-1eaa49ea'},
        'udpSender:hera_node_receiver.py': {
            'timestamp': datetime.datetime(2019, 4, 2, 19, 7, 16, 555086),
            'version': '0.0.1-1eaa49ea'},
        'hera_corr_cm': {
            'timestamp': datetime.datetime(2019, 4, 2, 19, 7, 17, 644984),
            'version': '0.0.1-11a573c9'},
        'snap': {'config': config[1],
                 'config_md5': 'testhash',
                 'config_timestamp': datetime.datetime(
                     2019, 2, 18, 5, 41, 29, 376363),
                 'init_args': init_args,
                 'timestamp':
                 datetime.datetime(2019, 3, 27, 8, 28, 25, 806626),
                 'version': '0.0.1-3c7fdaf6'}}


@pytest.fixture(scope='module')
def snapstatus():
    return {
        'heraNode700Snap0': {'last_programmed':
                             datetime.datetime(2016, 1, 10, 23, 16, 3),
                             'pmb_alert': False,
                             'pps_count': 595687,
                             'serial': 'SNPA000700',
                             'temp': 57.984954833984375,
                             'timestamp': datetime.datetime(
                                 2016, 1, 5, 20, 44, 52, 741137),
                             'uptime': 595686},
        'heraNode701Snap3': {'last_programmed':
                             datetime.datetime(2016, 1, 10, 23, 16, 3),
                             'pmb_alert': False,
                             'pps_count': 595699,
                             'serial': 'SNPD000703',
                             'temp': 59.323028564453125,
                             'timestamp': datetime.datetime(
                                 2016, 1, 5, 20, 44, 52, 739322),
                             'uptime': 595699}}


@pytest.fixture(scope='module')
def snapstatus_none():
    return {
        'heraNode700Snap0': {'last_programmed': 'None',
                             'pmb_alert': 'None',
                             'pps_count': 'None',
                             'serial': 'None',
                             'temp': 'None',
                             'timestamp': datetime.datetime(
                                 2016, 1, 5, 20, 44, 52, 741137),
                             'uptime': 'None'},
        'heraNode701Snap3': {'last_programmed':
                             datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
                             'pmb_alert': False,
                             'pps_count': 595699,
                             'serial': 'SNPD000703',
                             'temp': 59.323028564453125,
                             'timestamp': 'None',
                             'uptime': 595699}}


@pytest.fixture(scope='module')
def antstatus():
    return {
        '4:e': {'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
                'f_host': 'heraNode700Snap0',
                'host_ant_id': 3,
                'adc_mean': -0.5308380126953125,
                'adc_rms': 3.0134560488579285,
                'adc_power': 9.080917358398438,
                'pam_atten': 0,
                'pam_power': -13.349140985640002,
                'pam_voltage': 10.248,
                'pam_current': 0.6541,
                'pam_id': [112, 217, 32, 59, 1, 0, 0, 14],
                'fem_voltage': 6.496,
                'fem_current': 0.5627000000000001,
                'fem_id': [0, 168, 19, 212, 51, 51, 255, 255],
                'fem_temp': 26.327341308593752,
                'eq_coeffs': (np.zeros((1024)) + 56.921875).tolist(),
                'histogram': [np.arange(-128, 182, dtype=np.int).tolist(),
                              (np.zeros((256)) + 10).tolist()]},
        '31:n': {'timestamp':
                 datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
                 'f_host': 'heraNode4Snap3',
                 'host_ant_id': 7,
                 'adc_mean': -0.4805450439453125,
                 'adc_rms': 16.495319974304454,
                 'adc_power': 272.0955810546875,
                 'pam_atten': 0,
                 'pam_power': -32.03119784856,
                 'pam_voltage': 10.268,
                 'pam_current': 0.6695000000000001,
                 'pam_id': [112, 84, 143, 59, 1, 0, 0, 242],
                 'fem_voltage': float('nan'),
                 'fem_current': float('nan'),
                 'fem_id': [0, 168, 19, 212, 51, 51, 255, 255],
                 'fem_temp': 27.828854980468755,
                 'eq_coeffs': (np.zeros((1024)) + 73.46875).tolist(),
                 'histogram': [np.arange(-128, 182, dtype=np.int).tolist(),
                               (np.zeros((256)) + 12).tolist()]}}


@pytest.fixture(scope='module')
def antstatus_none():
    return {
        '4:e': {'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
                'f_host': 'None',
                'host_ant_id': 'None',
                'adc_mean': 'None',
                'adc_rms': 'None',
                'adc_power': 'None',
                'pam_atten': 'None',
                'pam_power': 'None',
                'eq_coeffs': 'None',
                'pam_voltage': 'None',
                'pam_current': 'None',
                'pam_id': 'None',
                'fem_voltage': 'None',
                'fem_current': 'None',
                'fem_id': 'None',
                'fem_temp': 'None',
                'eq_coeffs': 'None',
                'histogram': 'None'}}


def test_py3_hashing(config):
    # make sure I get the same answer as with python 2.7 & no explicit encoding
    # (like the correlator)
    py27_hash = '3b03414da0abe738aae071cccb911377'

    with open(config[0], 'r') as fh:
        config_string = fh.read().encode('utf-8')
        config_hash = hashlib.md5(config_string).hexdigest()

    assert py27_hash == config_hash


def test_add_corr_command_state(mcsession):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    test_session.add_correlator_control_state(t1, 'taking_data', True)

    expected = corr.CorrelatorControlState(
        time=int(floor(t1.gps)), state_type='taking_data', state=True)
    result = test_session.get_correlator_control_state(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_correlator_control_state(t1, 'phase_switching', False)

    result = test_session.get_correlator_control_state(
        starttime=t1 - TimeDelta(3.0, format='sec'), state_type='taking_data')
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_control_state(
        state_type='taking_data')
    assert len(result_most_recent), 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    expected = corr.CorrelatorControlState(
        time=int(floor(t1.gps)), state_type='phase_switching', state=False)

    result = test_session.get_correlator_control_state(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        state_type='phase_switching')
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_control_state(
        state_type='phase_switching')
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_correlator_control_state(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 2

    result_most_recent = test_session.get_correlator_control_state()
    assert len(result) == 2

    result = test_session.get_correlator_control_state(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_add_correlator_control_state_from_corrcm(mcsession, corrcommand):
    test_session = mcsession
    corr_state_obj_list = \
        test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=corrcommand, testing=True)

    for obj in corr_state_obj_list:
        test_session.add(obj)

    t1 = Time(1512770942.726777, format='unix')
    result = test_session.get_correlator_control_state(
        starttime=t1 - TimeDelta(3.0, format='sec'))

    expected = corr.CorrelatorControlState(
        time=int(floor(t1.gps)), state_type='taking_data', state=True)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_control_state(
        state_type='taking_data')
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result_most_recent = test_session.get_correlator_control_state()
    assert len(result_most_recent) == 1
    assert result_most_recent[0].state_type == 'noise_diode'

    result = test_session.get_correlator_control_state(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        stoptime=t1 + TimeDelta(5.0, format='sec'))
    assert len(result) == 3


def test_add_correlator_control_state_from_corrcm_nonetime_noprior(
        mcsession, corrstate_nonetime):
    test_session = mcsession
    test_session.add_correlator_control_state_from_corrcm(
        corr_state_dict=corrstate_nonetime)

    result = test_session.get_correlator_control_state(most_recent=True)
    res_time = result[0].time
    assert Time.now().gps - res_time < 2.

    expected = corr.CorrelatorControlState(
        time=res_time, state_type='taking_data', state=False)

    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


def test_add_correlator_control_state_from_corrcm_nonetime_priortrue(
        mcsession, corrcommand, corrstate_nonetime):
    test_session = mcsession
    test_session.add_correlator_control_state_from_corrcm(
        corr_state_dict=corrcommand)

    test_session.add_correlator_control_state_from_corrcm(
        corr_state_dict=corrstate_nonetime)

    result = test_session.get_correlator_control_state(most_recent=True)
    res_time = result[0].time
    assert Time.now().gps - res_time < 2.

    expected = corr.CorrelatorControlState(
        time=res_time, state_type='taking_data', state=False)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


def test_add_correlator_control_state_from_corrcm_nonetime_priorfalse(
        mcsession, corrstate_nonetime):
    test_session = mcsession
    not_taking_data_state_dict = {'taking_data': {
        'state': False, 'timestamp': Time(1512770942, format='unix')}}
    corr_state_obj_list = \
        test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=not_taking_data_state_dict)

    corr_state_obj_list = \
        test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=corrstate_nonetime, testing=True)
    test_session._insert_ignoring_duplicates(
        corr.CorrelatorControlState, corr_state_obj_list)

    result = test_session.get_correlator_control_state(most_recent=True)

    expected = corr.CorrelatorControlState(
        time=Time(1512770942, format='unix').gps, state_type='taking_data',
        state=False)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


def test_control_state_errors(mcsession):
    test_session = mcsession
    pytest.raises(ValueError, test_session.add_correlator_control_state,
                  'foo', 'taking_data', True)

    t1 = Time('2016-01-10 01:15:23', scale='utc')
    pytest.raises(ValueError, test_session.add_correlator_control_state,
                  t1, 'foo', True)

    bad_corr_state_dict = {'taking_data': {'state': True, 'timestamp': None}}
    pytest.raises(ValueError,
                  test_session.add_correlator_control_state_from_corrcm,
                  corr_state_dict=bad_corr_state_dict, testing=True)

    bad_corr_state_dict = {'phase_switching': {'state': False,
                                               'timestamp': None}}
    pytest.raises(ValueError,
                  test_session.add_correlator_control_state_from_corrcm,
                  corr_state_dict=bad_corr_state_dict, testing=True)


@onsite
def test_add_corr_control_state_from_corrcm(mcsession):
    test_session = mcsession

    test_session.add_correlator_control_state_from_corrcm()
    result = test_session.get_correlator_control_state(
        state_type='taking_data', most_recent=True)
    assert len(result) == 1
    result = test_session.get_correlator_control_state(
        state_type='phase_switching', most_recent=True)
    assert len(result) == 1
    result = test_session.get_correlator_control_state(
        state_type='noise_diode', most_recent=True)
    assert len(result) == 1


def test_add_corr_config(mcsession, config):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')

    config_hash = 'testhash'

    test_session.add_correlator_config_file(config_hash, config[0])
    test_session.commit()
    test_session.add_correlator_config_status(t1, config_hash)
    test_session.commit()

    file_expected = corr.CorrelatorConfigFile(config_hash=config_hash,
                                              filename=config[0])
    status_expected = corr.CorrelatorConfigStatus(time=int(floor(t1.gps)),
                                                  config_hash=config_hash)

    file_result = test_session.get_correlator_config_file(config_hash)
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    status_result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(status_result) == 1
    status_result = status_result[0]
    assert status_result.isclose(status_expected)

    config_hash2 = 'testhash2'
    test_session.add_correlator_config_file(config_hash2, config[0])
    test_session.commit()
    test_session.add_correlator_config_status(t2, config_hash2)
    test_session.commit()

    result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), config_hash=config_hash)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(status_expected)

    result_most_recent = test_session.get_correlator_config_status(
        config_hash=config_hash)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(status_expected)

    status_expected = corr.CorrelatorConfigStatus(
        time=int(floor(t2.gps)), config_hash=config_hash2)

    result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), config_hash=config_hash2)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(status_expected)

    result_most_recent = test_session.get_correlator_config_status(
        config_hash=config_hash2)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(status_expected)

    result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t2)
    assert len(result) == 2

    result_most_recent = test_session.get_correlator_config_status()
    assert len(result_most_recent) == 1

    result = test_session.get_correlator_config_status(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_add_correlator_config_from_corrcm(mcsession, corrconfig):
    test_session = mcsession
    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=corrconfig, testing=True)

    for obj in corr_config_list:
        test_session.add(obj)
        test_session.commit()

    t1 = Time(1512770942.726777, format='unix')
    status_result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(status_result) == 1
    file_result = test_session.get_correlator_config_file(
        status_result[0].config_hash)

    config_filename = 'correlator_config_' + str(int(floor(t1.gps))) + '.yaml'

    file_expected = corr.CorrelatorConfigFile(config_hash='testhash',
                                              filename=config_filename)
    status_expected = corr.CorrelatorConfigStatus(time=int(floor(t1.gps)),
                                                  config_hash='testhash')

    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    assert len(status_result) == 1
    status_result = status_result[0]
    assert status_result.isclose(status_expected)


def test_add_correlator_config_from_corrcm_match_prior(mcsession, corrconfig):
    test_session = mcsession
    # test behavior when matching config exists at an earlier time
    t1 = Time(1512770942.726777, format='unix')
    t0 = t1 - TimeDelta(30, format='sec')
    config_hash = 'testhash'
    config_filename = 'correlator_config_' + str(int(floor(t1.gps))) + '.yaml'
    test_session.add_correlator_config_file(config_hash, config_filename)
    test_session.commit()
    test_session.add_correlator_config_status(t0, config_hash)
    test_session.commit()

    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=corrconfig, testing=True)

    status_expected = corr.CorrelatorConfigStatus(time=int(floor(t1.gps)),
                                                  config_hash='testhash')

    assert corr_config_list[0].isclose(status_expected)


def test_add_correlator_config_from_corrcm_duplicate(mcsession, corrconfig):
    test_session = mcsession
    # test behavior when duplicate config exists
    t1 = Time(1512770942.726777, format='unix')
    config_hash = 'testhash'
    config_filename = 'correlator_config_' + str(int(floor(t1.gps))) + '.yaml'
    test_session.add_correlator_config_file(config_hash, config_filename)
    test_session.commit()
    test_session.add_correlator_config_status(t1, config_hash)
    test_session.commit()

    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=corrconfig, testing=True)

    assert len(corr_config_list) == 0


def test_config_errors(mcsession):
    test_session = mcsession
    pytest.raises(ValueError, test_session.add_correlator_config_status,
                  'foo', 'testhash')


@onsite
def test_add_correlator_config_from_corrcm_onsite(mcsession):
    test_session = mcsession

    result = test_session.add_correlator_config_from_corrcm(testing=True)

    assert len(result) > 0
    if len(result) == 2:
        assert result[0].__class__ == corr.CorrelatorConfigFile
        assert result[1].__class__ == corr.CorrelatorConfigStatus
    else:
        assert result[0].__class__ == corr.CorrelatorConfigStatus


@pytest.mark.parametrize(
    ("command"),
    list(set(corr.command_dict.keys())
         - set(['take_data', 'update_config'])))
def test_control_command_no_recent_status(mcsession, command):
    test_session = mcsession
    # test things on & off with no recent status
    command_list = test_session.correlator_control_command(
        command, testing=True)

    assert len(command_list) == 1
    command_time = command_list[0].time
    assert Time.now().gps - command_time < 2.

    command_time_obj = Time(command_time, format='gps')
    expected = corr.CorrelatorControlCommand.create(command_time_obj,
                                                    command)

    assert command_list[0].isclose(expected)

    # test adding the command(s) to the database and retrieving them
    for cmd in command_list:
        test_session.add(cmd)
    result_list = test_session.get_correlator_control_command(
        starttime=Time.now() - TimeDelta(10, format='sec'),
        stoptime=Time.now() + TimeDelta(10, format='sec'), command=command)
    assert len(result_list) == 1
    assert command_list[0].isclose(result_list[0])


def test_take_data_command_no_recent_status(mcsession):
    test_session = mcsession
    # test take_data command with no recent status
    starttime = Time.now() + TimeDelta(10, format='sec')

    command_list = test_session.correlator_control_command(
        'take_data', starttime=starttime, duration=100, tag='engineering',
        testing=True)

    assert len(command_list) == 2
    command_time = command_list[0].time
    assert Time.now().gps - command_time < 2.

    command_time_obj = Time(command_time, format='gps')
    expected_comm = corr.CorrelatorControlCommand.create(command_time_obj,
                                                         'take_data')

    assert command_list[0].isclose(expected_comm)

    int_time = corr.DEFAULT_ACCLEN_SPECTRA * ((2.0 * 16384) / 500e6)
    expected_args = corr.CorrelatorTakeDataArguments.create(
        command_time_obj, starttime, 100, corr.DEFAULT_ACCLEN_SPECTRA,
        int_time, 'engineering')

    assert command_list[1].isclose(expected_args)

    # check warning with non-standard acclen_spectra
    command_list = checkWarnings(test_session.correlator_control_command,
                                 ['take_data'],
                                 {'starttime': starttime, 'duration': 100,
                                  'acclen_spectra': 2048, 'tag': 'engineering',
                                  'testing': True,
                                  'overwrite_take_data': True},
                                 message='Using a non-standard acclen_spectra')

    assert len(command_list) == 2
    command_time = command_list[0].time
    assert Time.now().gps - command_time < 2.

    command_time_obj = Time(command_time, format='gps')
    expected_comm = corr.CorrelatorControlCommand.create(command_time_obj,
                                                         'take_data')
    assert command_list[0].isclose(expected_comm)

    int_time = 2048 * ((2.0 * 16384) / 500e6)
    expected_args = corr.CorrelatorTakeDataArguments.create(
        command_time_obj, starttime, 100, 2048,
        int_time, 'engineering')

    assert command_list[1].isclose(expected_args)


@pytest.mark.parametrize(
    ("commands_to_test"),
    [list(set(corr.command_dict.keys())
          - set(['take_data', 'update_config', 'restart']))])
def test_control_command_with_recent_status(mcsession, commands_to_test):
    test_session = mcsession
    # test things on & off with a recent status
    for command in commands_to_test:
        state_type = corr.command_state_map[command]['state_type']
        state = corr.command_state_map[command]['state']

        t1 = Time.now() - TimeDelta(30 + 60, format='sec')
        test_session.add_correlator_control_state(t1, state_type, state)

        command_list = test_session.correlator_control_command(
            command, testing=True)
        assert len(command_list) == 0

        t2 = Time.now() - TimeDelta(30, format='sec')
        test_session.add_correlator_control_state(t2, state_type, not(state))

        command_list = test_session.correlator_control_command(
            command, testing=True)

        assert len(command_list) == 1
        command_time = command_list[0].time
        assert Time.now().gps - command_time < 2.

        command_time_obj = Time(command_time, format='gps')
        expected = corr.CorrelatorControlCommand.create(command_time_obj,
                                                        command)
        assert command_list[0].isclose(expected)

        test_session.rollback()

        result = test_session.get_correlator_control_state(
            most_recent=True, state_type=state_type)
        assert len(result) == 0


def test_take_data_command_with_recent_status(mcsession):
    test_session = mcsession
    # test take_data command with recent status
    t1 = Time.now() - TimeDelta(60, format='sec')
    test_session.add_correlator_control_state(t1, 'taking_data', True)

    pytest.raises(RuntimeError, test_session.correlator_control_command,
                  'take_data',
                  starttime=Time.now() + TimeDelta(10, format='sec'),
                  duration=100, tag='engineering', testing=True)

    t2 = Time.now() - TimeDelta(30, format='sec')
    test_session.add_correlator_control_state(t2, 'taking_data', False)

    t3 = Time.now() + TimeDelta(10, format='sec')
    control_command_objs = test_session.correlator_control_command(
        'take_data', starttime=t3, duration=100, tag='engineering',
        testing=True)
    for obj in control_command_objs:
        test_session.add(obj)
        test_session.commit()

    time.sleep(1)

    starttime = Time.now() + TimeDelta(10, format='sec')
    pytest.raises(RuntimeError, test_session.correlator_control_command,
                  'take_data',
                  starttime=starttime + TimeDelta(30, format='sec'),
                  duration=100, tag='engineering', testing=True)

    command_list = checkWarnings(
        test_session.correlator_control_command, func_args=['take_data'],
        func_kwargs={'starttime': starttime, 'duration': 100,
                     'tag': 'engineering', 'testing': True,
                     'overwrite_take_data': True},
        message='Correlator was commanded to take data')

    command_time = command_list[0].time
    assert Time.now().gps - command_time < 2.

    command_time_obj = Time(command_time, format='gps')
    expected_comm = corr.CorrelatorControlCommand.create(
        command_time_obj, 'take_data')
    assert command_list[0].isclose(expected_comm)

    int_time = corr.DEFAULT_ACCLEN_SPECTRA * ((2.0 * 16384) / 500e6)
    expected_args = corr.CorrelatorTakeDataArguments.create(
        command_time_obj, starttime, 100, corr.DEFAULT_ACCLEN_SPECTRA,
        int_time, 'engineering')
    assert command_list[1].isclose(expected_args)

    for obj in command_list:
        test_session.add(obj)
        test_session.commit()

    result_args = test_session.get_correlator_take_data_arguments(
        most_recent=True, use_command_time=True)
    assert len(result_args) == 1
    assert result_args[0].isclose(expected_args)

    result_args = test_session.get_correlator_take_data_arguments(
        starttime=Time.now())
    assert len(result_args) == 1
    assert not result_args[0].isclose(expected_args)


@pytest.mark.parametrize(
    ("command", "kwargs"),
    [('foo', {}),
     ('take_data', {'starttime': Time.now() + TimeDelta(10, format='sec'),
                    'duration': 100}),
     ('take_data', {'starttime': Time.now() + TimeDelta(10, format='sec'),
                    'tag': 'engineering'}),
     ('take_data', {'duration': 100, 'tag': 'engineering'}),
     ('take_data', {'starttime': 'foo', 'duration': 100,
                    'tag': 'engineering'}),
     ('take_data', {'starttime': Time.now() + TimeDelta(10, format='sec'),
                    'duration': 100, 'tag': 'foo'}),
     ('take_data', {'starttime': Time.now() + TimeDelta(10, format='sec'),
                    'duration': 100, 'tag': 'foo', 'acclen_spectra': 2}),
     ('noise_diode_on',
      {'starttime': Time.now() + TimeDelta(10, format='sec')}),
     ('phase_switching_off', {'duration': 100}),
     ('restart', {'acclen_spectra': corr.DEFAULT_ACCLEN_SPECTRA}),
     ('noise_diode_off', {'tag': 'engineering'})])
def test_control_command_errors(mcsession, command, kwargs):
    test_session = mcsession
    pytest.raises(ValueError, test_session.correlator_control_command,
                  command, testing=True, **kwargs)


@pytest.mark.parametrize(
    ("command"), list(set(corr.command_dict.keys())
                      - set(['take_data', 'update_config',
                             'stop_taking_data'])))
def test_control_command_errors_taking_data(mcsession, command):
    test_session = mcsession
    # test bad commands while taking data
    t1 = Time.now() - TimeDelta(60, format='sec')
    test_session.add_correlator_control_state(t1, 'taking_data', True)

    pytest.raises(RuntimeError, test_session.correlator_control_command,
                  command, testing=True)


def test_control_command_errors_other():
    pytest.raises(ValueError, corr.CorrelatorControlCommand.create,
                  'foo', 'take_data')

    t1 = Time('2016-01-10 01:15:23', scale='utc')
    pytest.raises(ValueError, corr.CorrelatorTakeDataArguments.create,
                  'foo', t1, 100, 2, 2 * ((2.0 * 16384) / 500e6),
                  'engineering')


@onsite
def test_get_integration_time():
    n_spectra = 147456
    int_time = corr._get_integration_time(n_spectra)

    assert int_time > 0


@onsite
def test_get_next_start_time():
    corr._get_next_start_time()


def test_corr_config_command_no_recent_config(mcsession, config):
    test_session = mcsession
    # test commanding a config with no recent config status
    t1 = Time.now()

    with open(config[0], 'r') as fh:
        config_string = fh.read().encode('utf-8')
        config_hash = hashlib.md5(config_string).hexdigest()

    command_list = test_session.correlator_control_command(
        'update_config', config_file=config[0], testing=True)
    assert len(command_list) == 3

    # test adding the config obj(s) to the database and retrieving them
    for obj in command_list:
        test_session.add(obj)
        test_session.commit()

    file_expected = corr.CorrelatorConfigFile(
        config_hash=config_hash, filename=config[0])
    assert command_list[0].isclose(file_expected)

    file_result = test_session.get_correlator_config_file(config_hash)
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    command_time = command_list[1].time
    assert Time.now().gps - command_time < 2.

    command_time_obj = Time(command_time, format='gps')
    expected_comm = corr.CorrelatorControlCommand.create(
        command_time_obj, 'update_config')

    assert command_list[1].isclose(expected_comm)

    config_comm_expected = corr.CorrelatorConfigCommand.create(
        command_time_obj, config_hash)

    assert command_list[2].isclose(config_comm_expected)

    config_comm_result = test_session.get_correlator_config_command(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(config_comm_result) == 1
    config_comm_result = config_comm_result[0]
    assert config_comm_result.isclose(config_comm_expected)


def test_corr_config_command_with_recent_config(mcsession, config, corrconfig):
    test_session = mcsession
    # test commanding a config with a recent (different) config status
    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=corrconfig, testing=True)

    for obj in corr_config_list:
        test_session.add(obj)
        test_session.commit()

    t1 = Time.now()

    with open(config[0], 'r') as fh:
        config_string = fh.read().encode('utf-8')
        config_hash = hashlib.md5(config_string).hexdigest()

    command_list = test_session.correlator_control_command(
        'update_config', config_file=config[0], testing=True)
    assert len(command_list) == 3

    # test adding the config obj(s) to the database and retrieving them
    for obj in command_list:
        test_session.add(obj)
        test_session.commit()

    file_expected = corr.CorrelatorConfigFile(
        config_hash=config_hash, filename=config[0])
    assert command_list[0].isclose(file_expected)

    file_result = test_session.get_correlator_config_file(config_hash)
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    command_time = command_list[1].time
    assert Time.now().gps - command_time < 2.

    command_time_obj = Time(command_time, format='gps')
    expected_comm = corr.CorrelatorControlCommand.create(
        command_time_obj, 'update_config')

    assert command_list[1].isclose(expected_comm)

    assert Time.now().gps - command_time < 2.
    config_comm_expected = corr.CorrelatorConfigCommand.create(
        command_time_obj, config_hash)

    assert command_list[2].isclose(config_comm_expected)

    config_comm_result = test_session.get_correlator_config_command(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(config_comm_result) == 1
    config_comm_result = config_comm_result[0]
    assert config_comm_result.isclose(config_comm_expected)


def test_corr_config_command_with_recent_config_match_prior(mcsession,
                                                            config,
                                                            corrconfig):
    test_session = mcsession
    # test commanding a config with a recent (different) config status but a
    # matching prior one
    t1 = Time.now()
    t0 = Time(1512760942, format='unix')

    with open(config[0], 'r') as fh:
        config_string = fh.read().encode('utf-8')
        config_hash = hashlib.md5(config_string).hexdigest()

    # put in a previous matching config
    matching_corr_config_dict = {'time': t0, 'hash': config_hash,
                                 'config': config}
    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=matching_corr_config_dict, testing=True)

    for obj in corr_config_list:
        test_session.add(obj)
        test_session.commit()

    config_filename = 'correlator_config_' + str(int(floor(t0.gps))) + '.yaml'
    file_expected = corr.CorrelatorConfigFile(config_hash=config_hash,
                                              filename=config_filename)

    file_result = test_session.get_correlator_config_file(config_hash)
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    # make more recent one that doesn't match
    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=corrconfig, testing=True)

    for obj in corr_config_list:
        test_session.add(obj)
        test_session.commit()

    command_list = test_session.correlator_control_command(
        'update_config', config_file=config[0], testing=True)
    assert len(command_list) == 2

    # test adding the config obj(s) to the database and retrieving them
    for obj in command_list:
        test_session.add(obj)
        test_session.commit()

    command_time = command_list[0].time
    assert Time.now().gps - command_time < 2.

    command_time_obj = Time(command_time, format='gps')
    expected_comm = corr.CorrelatorControlCommand.create(
        command_time_obj, 'update_config')

    assert command_list[0].isclose(expected_comm)

    config_comm_expected = corr.CorrelatorConfigCommand.create(
        command_time_obj, config_hash)

    assert command_list[1].isclose(config_comm_expected)

    config_comm_result = test_session.get_correlator_config_command(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(config_comm_result) == 1
    config_comm_result = config_comm_result[0]
    assert config_comm_result.isclose(config_comm_expected)


def test_corr_config_command_same_recent_config(mcsession, config):
    test_session = mcsession
    # test commanding a config with the same recent config status
    t0 = Time(1512760942, format='unix')

    with open(config[0], 'r') as fh:
        config_string = fh.read().encode('utf-8')
        config_hash = hashlib.md5(config_string).hexdigest()

    # put in a previous matching config
    matching_corr_config_dict = {'time': t0, 'hash': config_hash,
                                 'config': config}
    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=matching_corr_config_dict, testing=True)

    for obj in corr_config_list:
        test_session.add(obj)
        test_session.commit()

    config_filename = 'correlator_config_' + str(int(floor(t0.gps))) + '.yaml'
    file_expected = corr.CorrelatorConfigFile(config_hash=config_hash,
                                              filename=config_filename)

    file_result = test_session.get_correlator_config_file(config_hash)
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    command_list = test_session.correlator_control_command(
        'update_config', config_file=config[0], testing=True)
    assert len(command_list) == 0


def test_config_command_errors(mcsession, config):
    test_session = mcsession
    pytest.raises(ValueError, corr.CorrelatorConfigCommand.create,
                  'foo', 'testhash')

    # not setting config_file with 'update_config' command
    pytest.raises(ValueError, test_session.correlator_control_command,
                  'update_config', testing=True)

    # setting config_file with other commands
    pytest.raises(ValueError, test_session.correlator_control_command,
                  'restart', config_file=config[0], testing=True)

    starttime = Time.now() + TimeDelta(10, format='sec')
    pytest.raises(ValueError, test_session.correlator_control_command,
                  'take_data', starttime=starttime, duration=100,
                  tag='engineering', config_file=config[0], testing=True)


def test_add_correlator_software_versions(mcsession):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    test_session.add_correlator_software_versions(
        t1, 'hera_corr_f', '0.0.1-3c7fdaf6')

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t1.gps)), package='hera_corr_f',
        version='0.0.1-3c7fdaf6')
    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_correlator_software_versions(
        t1, 'hera_corr_cm', '0.0.1-11a573c9')

    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format='sec'), package='hera_corr_f')
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_software_versions(
        package='hera_corr_f')
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t1.gps)), package='hera_corr_cm',
        version='0.0.1-11a573c9')

    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        package='hera_corr_cm')
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_software_versions(
        package='hera_corr_cm')
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 2

    result_most_recent = test_session.get_correlator_software_versions()
    assert len(result) == 2

    result = test_session.get_correlator_software_versions(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_software_version_errors(mcsession):
    test_session = mcsession
    pytest.raises(ValueError, test_session.add_correlator_software_versions,
                  'foo', 'hera_corr_cm', '0.0.1-11a573c9')


def test_add_snap_config_version(mcsession, config, init_args):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')

    test_session.add_correlator_config_file('testhash', config[0])
    test_session.commit()
    test_session.add_correlator_config_status(t1, 'testhash')
    test_session.commit()

    test_session.add_snap_config_version(
        t1, '0.0.1-3c7fdaf6', init_args, 'testhash')

    expected = corr.SNAPConfigVersion(
        init_time=int(floor(t1.gps)), version='0.0.1-3c7fdaf6',
        init_args=init_args, config_hash='testhash')

    result = test_session.get_snap_config_version(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_correlator_config_file('testhash2', config[0])
    test_session.commit()
    test_session.add_correlator_config_status(t2, 'testhash2')
    test_session.commit()

    test_session.add_snap_config_version(
        t2, '0.0.1-11a573c9', init_args, 'testhash2')

    expected = corr.SNAPConfigVersion(
        init_time=int(floor(t2.gps)), version='0.0.1-11a573c9',
        init_args=init_args, config_hash='testhash2')

    result = test_session.get_snap_config_version(
        starttime=t2 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_config_version()
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_snap_config_version(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t2)
    assert len(result) == 2

    result = test_session.get_snap_config_version(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_snap_config_version_errors(mcsession, init_args):
    test_session = mcsession
    pytest.raises(ValueError, test_session.add_snap_config_version,
                  'foo', '0.0.1-3c7fdaf6', init_args, 'testhash')


def test_add_corr_snap_versions_from_corrcm(mcsession, snapversion, init_args):
    test_session = mcsession
    # use testing to prevent call to hera_librarian to save new config file
    corr_snap_version_obj_list = \
        test_session.add_corr_snap_versions_from_corrcm(
            corr_snap_version_dict=snapversion, testing=True)

    for obj in corr_snap_version_obj_list:
        test_session.add(obj)
        test_session.commit()

    t1 = Time(datetime.datetime(2019, 4, 2, 19, 7, 14), format='datetime')
    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format='sec'))

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t1.gps)),
        package='hera_corr_f:hera_snap_redis_monitor.py',
        version='0.0.1-3c7fdaf6')
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_software_versions(
        package='hera_corr_f:hera_snap_redis_monitor.py')
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result_most_recent = test_session.get_correlator_software_versions()
    assert len(result_most_recent) == 3
    most_recent_packages = sorted([res.package for res in result_most_recent])
    expected_recent_packages = sorted(['udpSender:hera_node_keep_alive.py',
                                       'udpSender:hera_node_cmd_check.py',
                                       'hera_corr_cm'])
    assert most_recent_packages == expected_recent_packages

    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        stoptime=t1 + TimeDelta(10.0, format='sec'))
    assert len(result) == 5

    t2 = Time(datetime.datetime(2019, 3, 27, 8, 28, 25), format='datetime')
    result = test_session.get_snap_config_version(
        starttime=t2 - TimeDelta(3.0, format='sec'))

    expected = corr.SNAPConfigVersion(init_time=int(floor(t2.gps)),
                                      version='0.0.1-3c7fdaf6',
                                      init_args=init_args,
                                      config_hash='testhash')
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_config_version()
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    t3 = Time(datetime.datetime(2019, 2, 18, 5, 41, 29), format='datetime')
    result = test_session.get_correlator_config_status(
        starttime=t3 - TimeDelta(3.0, format='sec'))

    expected = corr.CorrelatorConfigStatus(time=int(floor(t3.gps)),
                                           config_hash='testhash')
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_config_status()
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    # test that a new hera_corr_cm timestamp with the same version doesn't make
    # a new row
    new_dict = copy.deepcopy(snapversion)
    new_dict['hera_corr_cm']['timestamp'] = (
        datetime.datetime(2019, 4, 2, 19, 8, 17, 644984))

    corr_snap_version_obj_list = \
        test_session.add_corr_snap_versions_from_corrcm(
            corr_snap_version_dict=new_dict)

    t4 = Time(datetime.datetime(2019, 4, 2, 19, 7, 17), format='datetime')
    t5 = Time(datetime.datetime(2019, 4, 2, 19, 8, 17), format='datetime')

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t4.gps)), package='hera_corr_cm',
        version='0.0.1-11a573c9')

    result = test_session.get_correlator_software_versions(
        starttime=t4 - TimeDelta(3.0, format='sec'),
        stoptime=t5 + TimeDelta(10.0, format='sec'),
        package='hera_corr_cm')

    assert len(result) == 1
    assert result[0].isclose(expected)

    # test that a new hera_corr_cm timestamp with a new version makes a new row
    new_dict = copy.deepcopy(snapversion)
    new_dict['hera_corr_cm']['timestamp'] = (
        datetime.datetime(2019, 4, 2, 19, 8, 17, 644984))
    new_dict['hera_corr_cm']['version'] = '0.0.1-b43b2b72'

    corr_snap_version_obj_list = \
        test_session.add_corr_snap_versions_from_corrcm(
            corr_snap_version_dict=new_dict)

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t5.gps)), package='hera_corr_cm',
        version='0.0.1-b43b2b72')

    result = test_session.get_correlator_software_versions(
        starttime=t4 - TimeDelta(3.0, format='sec'),
        stoptime=t5 + TimeDelta(10.0, format='sec'),
        package='hera_corr_cm')

    assert len(result) == 2
    assert result[1].isclose(expected)


@onsite
def test_onsite_add_corr_snap_versions_from_corrcm(mcsession):
    test_session = mcsession

    test_session.add_corr_snap_versions_from_corrcm()

    result = test_session.get_correlator_software_versions(
        package='hera_corr_cm', most_recent=True)
    assert len(result) == 1

    result = test_session.get_correlator_software_versions()
    assert len(result) >= 1

    result = test_session.get_snap_config_version()
    assert len(result) == 1


def test_add_snap_status(mcsession):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    t_prog = Time('2016-01-05 20:00:00', scale='utc')
    test_session.add_snap_status(t1, 'heraNode700Snap0', 'SNPA000700',
                                 False, 595687, 57.984954833984375,
                                 595686, t_prog)

    expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                               hostname='heraNode700Snap0',
                               serial_number='SNPA000700', node=700,
                               snap_loc_num=0,
                               psu_alert=False, pps_count=595687,
                               fpga_temp=57.984954833984375,
                               uptime_cycles=595686,
                               last_programmed_time=int(floor(t_prog.gps)))
    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_snap_status(t1, 'heraNode701Snap3', 'SNPD000703',
                                 True, 595699, 59.323028564453125,
                                 595699, t_prog)

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=700)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status(nodeID=700)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                               hostname='heraNode701Snap3',
                               serial_number='SNPD000703', node=701,
                               snap_loc_num=3,
                               psu_alert=True, pps_count=595699,
                               fpga_temp=59.323028564453125,
                               uptime_cycles=595699,
                               last_programmed_time=int(floor(t_prog.gps)))

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=701)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status(nodeID=701)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 2

    result_most_recent = test_session.get_snap_status()
    assert len(result) == 2

    result = test_session.get_snap_status(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_add_snap_status_from_corrcm(mcsession, snapstatus):
    test_session = mcsession
    test_session.add_snap_status_from_corrcm(
        snap_status_dict=snapstatus)

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
              format='datetime')
    t_prog = Time(datetime.datetime(2016, 1, 10, 23, 16, 3), format='datetime')
    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=700)

    expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                               hostname='heraNode700Snap0',
                               serial_number='SNPA000700', node=700,
                               snap_loc_num=0,
                               psu_alert=False, pps_count=595687,
                               fpga_temp=57.984954833984375,
                               uptime_cycles=595686,
                               last_programmed_time=int(floor(t_prog.gps)))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status(nodeID=700)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=701)

    expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                               hostname='heraNode701Snap3',
                               serial_number='SNPD000703', node=701,
                               snap_loc_num=3,
                               psu_alert=False, pps_count=595699,
                               fpga_temp=59.323028564453125,
                               uptime_cycles=595699,
                               last_programmed_time=int(floor(t_prog.gps)))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status()
    assert len(result_most_recent) == 2


def test_add_snap_status_from_corrcm_with_nones(mcsession, snapstatus_none):
    test_session = mcsession
    snap_status_obj_list = test_session.add_snap_status_from_corrcm(
        snap_status_dict=snapstatus_none, testing=True)

    for obj in snap_status_obj_list:
        test_session.add(obj)

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
              format='datetime')
    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))

    expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                               hostname='heraNode700Snap0',
                               serial_number=None, node=None,
                               snap_loc_num=None,
                               psu_alert=None, pps_count=None,
                               fpga_temp=None, uptime_cycles=None,
                               last_programmed_time=None)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


def test_snap_status_errors(mcsession):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    pytest.raises(ValueError, test_session.add_snap_status,
                  'foo', 'heraNode700Snap0', 'SNPA000700', False,
                  595687, 57.984954833984375, 595686, t1)

    pytest.raises(ValueError, test_session.add_snap_status,
                  t1, 'heraNode700Snap0', 'SNPA000700', False, 595687,
                  57.984954833984375, 595686, 'foo')


def test_get_node_snap_from_serial_nodossier(mcsession):
    node, snap_loc_num = checkWarnings(mcsession._get_node_snap_from_serial, ['foo'])

    assert node is None
    assert snap_loc_num is None


def test_get_node_snap_from_serial_multiple_locs(mcsession):
    """Test multiple snap location numbers."""
    connection = cm_partconnect.Connections()
    connection.upstream_part = 'SNPD000703'
    connection.up_part_rev = 'A'
    connection.downstream_part = 'N701'
    connection.down_part_rev = 'A'
    connection.upstream_output_port = 'rack'
    connection.downstream_input_port = 'loc2'
    connection.start_gpstime = 1230375618
    mcsession.add(connection)
    mcsession.commit()
    pytest.raises(ValueError, mcsession._get_node_snap_from_serial, ['SNPD000703'])


def test_get_node_snap_from_serial_multiple_locs(mcsession):
    """Test multiple snap location numbers."""
    # connection = cm_partconnect.Connections()
    # connection.upstream_part = 'SNPD000703'
    # connection.up_part_rev = 'A'
    # connection.downstream_part = 'N701'
    # connection.down_part_rev = 'A'
    # connection.upstream_output_port = 'rack'
    # connection.downstream_input_port = 'loc2'
    # connection.start_gpstime = 1230375618
    # mcsession.add(connection)
    # mcsession.commit()
    part = cm_partconnect.Parts()
    part.hpn = 'SNPD000703'
    part.hpn_rev = 'B'
    part.hptype = 'snap'
    part.manufacture_number = 'D000703'
    part.start_gpstime = 1230375618
    mcsession.add(part)
    mcsession.commit()
    connection = cm_partconnect.Connections()
    connection.upstream_part = 'SNPD000703'
    connection.up_part_rev = 'B'
    connection.downstream_part = 'N701'
    connection.down_part_rev = 'A'
    connection.upstream_output_port = 'rack'
    connection.downstream_input_port = 'loc2'
    connection.start_gpstime = 1230375618
    mcsession.add(connection)
    mcsession.commit()
    node, snap_loc_num = checkWarnings(mcsession._get_node_snap_from_serial, ['SNPD000703'])

    assert node is None
    assert snap_loc_num is None


def test_get_node_snap_from_serial_multiple_times_diffloc(mcsession):
    """Test multiple times with change in location."""
    # stop earlier connection
    conn_to_stop = [['SNPD000703', 'A', 'N701', 'A', 'rack', 'loc3',
                    1230375618]]
    cm_partconnect.stop_connections(mcsession, conn_to_stop,
                                    Time(1230375700, format='gps'))

    connection = cm_partconnect.Connections()
    connection.upstream_part = 'SNPD000703'
    connection.up_part_rev = 'A'
    connection.downstream_part = 'N701'
    connection.down_part_rev = 'A'
    connection.upstream_output_port = 'rack'
    connection.downstream_input_port = 'loc2'
    connection.start_gpstime = 1230375718
    mcsession.add(connection)
    mcsession.commit()
    node, snap_loc_num = checkWarnings(mcsession._get_node_snap_from_serial,
                                       ['SNPD000703'], nwarnings=0)
    assert node == 701
    assert snap_loc_num == 2


def test_get_snap_hostname_from_serial(mcsession, snapstatus):
    test_session = mcsession
    test_session.add_snap_status_from_corrcm(
        snap_status_dict=snapstatus)

    hostname = test_session.get_snap_hostname_from_serial('SNPA000700')
    assert hostname == 'heraNode700Snap0'

    hostname = test_session.get_snap_hostname_from_serial('blah')
    assert hostname is None


@onsite
def test_site_add_snap_status_from_corrcm(mcsession):
    test_session = mcsession

    # get the snap status dict from the correlator redis
    snap_status_dict = corr._get_snap_status()
    assert len(snap_status_dict) >= 1

    # use the real (not test) database to get the node & snap location number
    real_db = mc.connect_to_mc_db(None)
    real_session = real_db.sessionmaker()

    test_session.add_snap_status_from_corrcm(cm_session=real_session)
    result = test_session.get_snap_status(most_recent=True)
    assert len(result) >= 1


def test_add_antenna_status(mcsession):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')

    eq_coeffs = (np.zeros((5)) + 56.921875).tolist()
    histogram_bins = [-4, -3, -2, -1, 0, 1, 2, 3]
    histogram = [0, 3, 6, 10, 12, 8, 4, 0]
    pam_id_list = [112, 217, 32, 59, 1, 0, 0, 14]
    pam_id = ''.join([hex(i)[2:] for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ''.join([hex(i)[2:] for i in fem_id_list])
    test_session.add_antenna_status(t1, 4, 'e', 'heraNode700Snap0', 3,
                                    -0.5308380126953125, 3.0134560488579285,
                                    9.080917358398438, 0, -13.349140985640002,
                                    10.248, 0.6541, pam_id, 6.496,
                                    0.5627000000000001, fem_id,
                                    26.327341308593752, eq_coeffs,
                                    histogram_bins, histogram)

    eq_coeffs_string = '[56.921875,56.921875,56.921875,56.921875,56.921875]'
    histogram_bin_string = '[-4,-3,-2,-1,0,1,2,3]'
    histogram_string = '[0,3,6,10,12,8,4,0]'
    expected = corr.AntennaStatus(time=int(floor(t1.gps)), antenna_number=4,
                                  antenna_feed_pol='e',
                                  snap_hostname='heraNode700Snap0',
                                  snap_channel_number=3,
                                  adc_mean=-0.5308380126953125,
                                  adc_rms=3.0134560488579285,
                                  adc_power=9.080917358398438, pam_atten=0,
                                  pam_power=-13.349140985640002,
                                  pam_voltage=10.248,
                                  pam_current=0.6541,
                                  pam_id=pam_id,
                                  fem_voltage=6.496,
                                  fem_current=0.5627000000000001,
                                  fem_id=fem_id,
                                  fem_temp=26.327341308593752,
                                  eq_coeffs=eq_coeffs_string,
                                  histogram_bin_centers=histogram_bin_string,
                                  histogram=histogram_string)

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    eq_coeffs = (np.zeros((5)) + 73.46875).tolist()
    histogram_bins = [-4, -3, -2, -1, 0, 1, 2, 3]
    histogram = [0, 3, 6, 10, 12, 8, 4, 0]
    pam_id_list = [112, 84, 143, 59, 1, 0, 0, 242]
    pam_id = ''.join([hex(i)[2:] for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ''.join([hex(i)[2:] for i in fem_id_list])
    test_session.add_antenna_status(t2, 31, 'n', 'heraNode4Snap3', 7,
                                    -0.4805450439453125, 16.495319974304454,
                                    272.0955810546875, 0, -32.03119784856,
                                    10.268, 0.6695000000000001, pam_id,
                                    None, None, fem_id,
                                    27.828854980468755, eq_coeffs,
                                    histogram_bins, histogram)

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), antenna_number=4)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_antenna_status(antenna_number=4)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    eq_coeffs_string = '[73.46875,73.46875,73.46875,73.46875,73.46875]'
    histogram_bin_string = '[-4,-3,-2,-1,0,1,2,3]'
    histogram_string = '[0,3,6,10,12,8,4,0]'
    expected = corr.AntennaStatus(time=int(floor(t2.gps)), antenna_number=31,
                                  antenna_feed_pol='n',
                                  snap_hostname='heraNode4Snap3',
                                  snap_channel_number=7,
                                  adc_mean=-0.4805450439453125,
                                  adc_rms=16.495319974304454,
                                  adc_power=272.0955810546875, pam_atten=0,
                                  pam_power=-32.03119784856,
                                  pam_voltage=10.268,
                                  pam_current=0.6695000000000001,
                                  pam_id=pam_id,
                                  fem_voltage=None,
                                  fem_current=None,
                                  fem_id=fem_id,
                                  fem_temp=27.828854980468755,
                                  eq_coeffs=eq_coeffs_string,
                                  histogram_bin_centers=histogram_bin_string,
                                  histogram=histogram_string)

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), antenna_number=31)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_antenna_status(antenna_number=31)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 1

    result_most_recent = test_session.get_antenna_status()
    assert len(result) == 1

    result = test_session.get_antenna_status(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_add_antenna_status_from_corrcm(mcsession, antstatus):
    test_session = mcsession
    ant_status_obj_list = test_session.add_antenna_status_from_corrcm(
        ant_status_dict=antstatus, testing=True)

    for obj in ant_status_obj_list:
        test_session.add(obj)

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
              format='datetime')
    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), antenna_number=4)

    eq_coeffs_str = [str(val) for val
                     in (np.zeros((1024)) + 56.921875).tolist()]
    eq_coeffs_string = '[' + ','.join(eq_coeffs_str) + ']'

    histogram_bin_str = [str(val) for val
                         in np.arange(-128, 182, dtype=np.int).tolist()]
    histogram_bin_string = '[' + ','.join(histogram_bin_str) + ']'
    histogram_str = [str(val) for val in (np.zeros((256)) + 10).tolist()]
    histogram_string = '[' + ','.join(histogram_str) + ']'
    pam_id_list = [112, 217, 32, 59, 1, 0, 0, 14]
    pam_id = ''.join([hex(i)[2:] for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ''.join([hex(i)[2:] for i in fem_id_list])
    expected = corr.AntennaStatus(time=int(floor(t1.gps)), antenna_number=4,
                                  antenna_feed_pol='e',
                                  snap_hostname='heraNode700Snap0',
                                  snap_channel_number=3,
                                  adc_mean=-0.5308380126953125,
                                  adc_rms=3.0134560488579285,
                                  adc_power=9.080917358398438,
                                  pam_atten=0,
                                  pam_power=-13.349140985640002,
                                  pam_voltage=10.248,
                                  pam_current=0.6541,
                                  pam_id=pam_id,
                                  fem_voltage=6.496,
                                  fem_current=0.5627000000000001,
                                  fem_id=fem_id,
                                  fem_temp=26.327341308593752,
                                  eq_coeffs=eq_coeffs_string,
                                  histogram_bin_centers=histogram_bin_string,
                                  histogram=histogram_string)

    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_antenna_status(antenna_number=4)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), antenna_number=31)

    eq_coeffs_str = [str(val) for val in
                     (np.zeros((1024)) + 73.46875).tolist()]
    eq_coeffs_string = '[' + ','.join(eq_coeffs_str) + ']'
    histogram_bin_str = [str(val) for val
                         in np.arange(-128, 182, dtype=np.int).tolist()]
    histogram_bin_string = '[' + ','.join(histogram_bin_str) + ']'
    histogram_str = [str(val) for val in (np.zeros((256)) + 12).tolist()]
    histogram_string = '[' + ','.join(histogram_str) + ']'
    pam_id_list = [112, 84, 143, 59, 1, 0, 0, 242]
    pam_id = ''.join([hex(i)[2:] for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ''.join([hex(i)[2:] for i in fem_id_list])
    expected = corr.AntennaStatus(time=int(floor(t1.gps)), antenna_number=31,
                                  antenna_feed_pol='n',
                                  snap_hostname='heraNode4Snap3',
                                  snap_channel_number=7,
                                  adc_mean=-0.4805450439453125,
                                  adc_rms=16.495319974304454,
                                  adc_power=272.0955810546875, pam_atten=0,
                                  pam_power=-32.03119784856,
                                  pam_voltage=10.268,
                                  pam_current=0.6695000000000001,
                                  pam_id=pam_id,
                                  fem_voltage=None,
                                  fem_current=None,
                                  fem_id=fem_id,
                                  fem_temp=27.828854980468755,
                                  eq_coeffs=eq_coeffs_string,
                                  histogram_bin_centers=histogram_bin_string,
                                  histogram=histogram_string)

    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_antenna_status()
    assert len(result_most_recent) == 2


def test_add_antenna_status_from_corrcm_with_nones(mcsession, antstatus_none):
    test_session = mcsession
    test_session.add_antenna_status_from_corrcm(
        ant_status_dict=antstatus_none)

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
              format='datetime')
    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))

    expected = corr.AntennaStatus(time=int(floor(t1.gps)), antenna_number=4,
                                  antenna_feed_pol='e',
                                  snap_hostname=None, snap_channel_number=None,
                                  adc_mean=None, adc_rms=None,
                                  adc_power=None, pam_atten=None,
                                  pam_power=None, pam_voltage=None,
                                  pam_current=None, pam_id=None,
                                  fem_voltage=None, fem_current=None,
                                  fem_id=None, fem_temp=None, eq_coeffs=None,
                                  histogram_bin_centers=None, histogram=None)

    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


def test_antenna_status_errors(mcsession):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    eq_coeffs = (np.zeros((5)) + 56.921875).tolist()
    histogram_bins = [-4, -3, -2, -1, 0, 1, 2, 3]
    histogram = [0, 3, 6, 10, 12, 8, 4, 0]
    pam_id_list = [112, 217, 32, 59, 1, 0, 0, 14]
    pam_id = ''.join([hex(i)[2:] for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ''.join([hex(i)[2:] for i in fem_id_list])
    pytest.raises(ValueError, test_session.add_antenna_status,
                  'foo', 4, 'e', 'heraNode700Snap0', 3, -0.5308380126953125,
                  3.0134560488579285, 9.080917358398438, 0,
                  -13.349140985640002, 10.248, 0.6541, pam_id,
                  6.496, 0.5627000000000001, fem_id,
                  26.327341308593752, eq_coeffs,
                  histogram_bins, histogram)

    pytest.raises(ValueError, test_session.add_antenna_status,
                  t1, 4, 'x', 'heraNode700Snap0', 3, -0.5308380126953125,
                  3.0134560488579285, 9.080917358398438, 0,
                  -13.349140985640002, 10.248, 0.6541, pam_id,
                  6.496, 0.5627000000000001, fem_id,
                  26.327341308593752, eq_coeffs,
                  histogram_bins, histogram)


@onsite
def test_site_add_antenna_status_from_corrcm(mcsession):
    test_session = mcsession

    test_session.add_antenna_status_from_corrcm()
    result = test_session.get_antenna_status(most_recent=True)
    assert len(result) >= 1
