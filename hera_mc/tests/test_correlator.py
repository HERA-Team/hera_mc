# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.correlator`.

"""
from __future__ import absolute_import, division, print_function

import unittest
import os
import copy
import time
import datetime
import hashlib
import yaml
import nose.tools as nt
import numpy as np
from math import floor
from astropy.time import Time, TimeDelta

from hera_mc import mc
import hera_mc.correlator as corr
from hera_mc.tests import TestHERAMC, is_onsite, checkWarnings
from hera_mc.data import DATA_PATH


corr_command_example_dict = {
    'taking_data': {'state': True, 'timestamp': Time(1512770942, format='unix')},
    'phase_switching': {'state': False, 'timestamp': Time(1512770944, format='unix')},
    'noise_diode': {'state': True, 'timestamp': Time(1512770946, format='unix')},
}
corr_state_dict_nonetime = {'taking_data': {'state': False, 'timestamp': None}}

config_file = os.path.join(DATA_PATH, 'test_data', 'hera_feng_config_example.yaml')
with open(config_file, 'r') as stream:
    config = yaml.safe_load(stream)

corr_config_example_dict = {'time': Time(1512770942, format='unix'),
                            'hash': 'testhash', 'config': config}

init_args = ("Namespace(config_file=None, eth=True, initialize=True, "
             + "mansync=False, noise=False, program=False, "
             + "redishost='redishost', sync=True, tvg=False)")

corr_snap_version_example_dict = {
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
    'snap': {'config': config,
             'config_md5': 'testhash',
             'config_timestamp': datetime.datetime(2019, 2, 18, 5, 41, 29, 376363),
             'init_args': init_args,
             'timestamp': datetime.datetime(2019, 3, 27, 8, 28, 25, 806626),
             'version': '0.0.1-3c7fdaf6'}}

snap_status_example_dict = {
    'heraNode23Snap1': {'last_programmed': datetime.datetime(2016, 1, 10, 23, 16, 3),
                        'pmb_alert': False,
                        'pps_count': 595687,
                        'serial': 'SNPA000222',
                        'temp': 57.984954833984375,
                        'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
                        'uptime': 595686},
    'heraNode4Snap0': {'last_programmed': datetime.datetime(2016, 1, 10, 23, 16, 3),
                       'pmb_alert': False,
                       'pps_count': 595699,
                       'serial': 'SNPA000224',
                       'temp': 59.323028564453125,
                       'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
                       'uptime': 595699}}

snap_status_none_example_dict = {
    'heraNode23Snap1': {'last_programmed': 'None',
                        'pmb_alert': 'None',
                        'pps_count': 'None',
                        'serial': 'None',
                        'temp': 'None',
                        'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
                        'uptime': 'None'},
    'heraNode23Snap2': {'last_programmed': datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
                        'pmb_alert': False,
                        'pps_count': 595699,
                        'serial': 'SNPA000224',
                        'temp': 59.323028564453125,
                        'timestamp': 'None',
                        'uptime': 595699}}

ant_status_example_dict = {
    '4:e': {'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            'f_host': 'heraNode23Snap1',
            'host_ant_id': 3,
            'adc_mean': -0.5308380126953125,
            'adc_rms': 3.0134560488579285,
            'adc_power': 9.080917358398438,
            'pam_atten': 0,
            'pam_power': -13.349140985640002,
            'eq_coeffs': (np.zeros((1024)) + 56.921875).tolist()},
    '31:n': {'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
             'f_host': 'heraNode4Snap3',
             'host_ant_id': 7,
             'adc_mean': -0.4805450439453125,
             'adc_rms': 16.495319974304454,
             'adc_power': 272.0955810546875,
             'pam_atten': 0,
             'pam_power': -32.03119784856,
             'eq_coeffs': (np.zeros((1024)) + 73.46875).tolist()}}

ant_status_nones_example_dict = {
    '4:e': {'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            'f_host': 'None',
            'host_ant_id': 'None',
            'adc_mean': 'None',
            'adc_rms': 'None',
            'adc_power': 'None',
            'pam_atten': 'None',
            'pam_power': 'None',
            'eq_coeffs': 'None'}}


def test_py3_hashing():
    # make sure I get the same answer as with python 2.7 & no explicit encoding (like the correlator)
    py27_hash = '3b03414da0abe738aae071cccb911377'

    with open(config_file, 'r') as fh:
        config_string = fh.read().encode('utf-8')
        config_hash = hashlib.md5(config_string).hexdigest()

    nt.assert_equal(py27_hash, config_hash)


class TestCorrelatorCommandState(TestHERAMC):

    def test_add_corr_command_state(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        self.test_session.add_correlator_control_state(t1, 'taking_data', True)

        expected = corr.CorrelatorControlState(time=int(floor(t1.gps)),
                                               state_type='taking_data', state=True)
        result = self.test_session.get_correlator_control_state(starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        self.test_session.add_correlator_control_state(t1, 'phase_switching', False)

        result = self.test_session.get_correlator_control_state(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                                state_type='taking_data')
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_correlator_control_state(state_type='taking_data')
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        expected = corr.CorrelatorControlState(time=int(floor(t1.gps)),
                                               state_type='phase_switching', state=False)

        result = self.test_session.get_correlator_control_state(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                                state_type='phase_switching')
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_correlator_control_state(state_type='phase_switching')
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result = self.test_session.get_correlator_control_state(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                                stoptime=t1)
        self.assertEqual(len(result), 2)

        result_most_recent = self.test_session.get_correlator_control_state()
        self.assertEqual(len(result), 2)

        result = self.test_session.get_correlator_control_state(starttime=t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_add_correlator_control_state_from_corrcm(self):
        corr_state_obj_list = self.test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=corr_command_example_dict, testing=True)

        for obj in corr_state_obj_list:
            self.test_session.add(obj)

        t1 = Time(1512770942.726777, format='unix')
        result = self.test_session.get_correlator_control_state(
            starttime=t1 - TimeDelta(3.0, format='sec'))

        expected = corr.CorrelatorControlState(time=int(floor(t1.gps)),
                                               state_type='taking_data', state=True)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_correlator_control_state(state_type='taking_data')
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result_most_recent = self.test_session.get_correlator_control_state()
        self.assertEqual(len(result_most_recent), 1)
        self.assertEqual(result_most_recent[0].state_type, 'noise_diode')

        result = self.test_session.get_correlator_control_state(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                                stoptime=t1 + TimeDelta(5.0, format='sec'))
        self.assertEqual(len(result), 3)

    def test_add_correlator_control_state_from_corrcm_nonetime_noprior(self):
        corr_state_obj_list = self.test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=corr_state_dict_nonetime)

        result = self.test_session.get_correlator_control_state(most_recent=True)
        res_time = result[0].time
        self.assertTrue(Time.now().gps - res_time < 2.)

        expected = corr.CorrelatorControlState(time=res_time,
                                               state_type='taking_data', state=False)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

    def test_add_correlator_control_state_from_corrcm_nonetime_priortrue(self):
        corr_state_obj_list = self.test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=corr_command_example_dict)

        corr_state_obj_list = self.test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=corr_state_dict_nonetime)

        result = self.test_session.get_correlator_control_state(most_recent=True)
        res_time = result[0].time
        self.assertTrue(Time.now().gps - res_time < 2.)

        expected = corr.CorrelatorControlState(time=res_time,
                                               state_type='taking_data', state=False)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

    def test_add_correlator_control_state_from_corrcm_nonetime_priorfalse(self):
        not_taking_data_state_dict = {'taking_data': {'state': False,
                                                      'timestamp': Time(1512770942, format='unix')}}
        corr_state_obj_list = self.test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=not_taking_data_state_dict)

        corr_state_obj_list = self.test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=corr_state_dict_nonetime, testing=True)
        self.test_session._insert_ignoring_duplicates(corr.CorrelatorControlState,
                                                      corr_state_obj_list)

        result = self.test_session.get_correlator_control_state(most_recent=True)

        expected = corr.CorrelatorControlState(time=Time(1512770942, format='unix').gps,
                                               state_type='taking_data', state=False)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

    def test_control_state_errors(self):
        self.assertRaises(ValueError, self.test_session.add_correlator_control_state,
                          'foo', 'taking_data', True)

        t1 = Time('2016-01-10 01:15:23', scale='utc')
        self.assertRaises(ValueError, self.test_session.add_correlator_control_state,
                          t1, 'foo', True)

        bad_corr_state_dict = {'taking_data': {'state': True, 'timestamp': None}}
        self.assertRaises(ValueError, self.test_session.add_correlator_control_state_from_corrcm,
                          corr_state_dict=bad_corr_state_dict, testing=True)

        bad_corr_state_dict = {'phase_switching': {'state': False, 'timestamp': None}}
        self.assertRaises(ValueError, self.test_session.add_correlator_control_state_from_corrcm,
                          corr_state_dict=bad_corr_state_dict, testing=True)

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_add_corr_command_state_from_corrcm(self):

        self.test_session.add_correlator_control_state_from_corrcm()
        result = self.test_session.get_correlator_control_state(
            state_type='taking_data', most_recent=True)
        self.assertEqual(len(result), 1)
        result = self.test_session.get_correlator_control_state(
            state_type='phase_switching', most_recent=True)
        self.assertEqual(len(result), 1)
        result = self.test_session.get_correlator_control_state(
            state_type='noise_diode', most_recent=True)
        self.assertEqual(len(result), 1)


class TestCorrelatorConfigStatus(TestHERAMC):

    def test_add_corr_config(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        config_hash = 'testhash'

        self.test_session.add_correlator_config_file(config_hash, config_file)
        self.test_session.commit()
        self.test_session.add_correlator_config_status(t1, config_hash)
        self.test_session.commit()

        file_expected = corr.CorrelatorConfigFile(config_hash=config_hash,
                                                  filename=config_file)
        status_expected = corr.CorrelatorConfigStatus(time=int(floor(t1.gps)),
                                                      config_hash=config_hash)

        file_result = self.test_session.get_correlator_config_file(config_hash)
        self.assertEqual(len(file_result), 1)
        file_result = file_result[0]
        self.assertTrue(file_result.isclose(file_expected))

        status_result = self.test_session.get_correlator_config_status(
            starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(status_result), 1)
        status_result = status_result[0]
        self.assertTrue(status_result.isclose(status_expected))

        config_hash2 = 'testhash2'
        self.test_session.add_correlator_config_file(config_hash2, config_file)
        self.test_session.commit()
        self.test_session.add_correlator_config_status(t2, config_hash2)
        self.test_session.commit()

        result = self.test_session.get_correlator_config_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), config_hash=config_hash)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(status_expected))

        result_most_recent = self.test_session.get_correlator_config_status(config_hash=config_hash)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(status_expected))

        status_expected = corr.CorrelatorConfigStatus(time=int(floor(t2.gps)),
                                                      config_hash=config_hash2)

        result = self.test_session.get_correlator_config_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), config_hash=config_hash2)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(status_expected))

        result_most_recent = self.test_session.get_correlator_config_status(
            config_hash=config_hash2)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(status_expected))

        result = self.test_session.get_correlator_config_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t2)
        self.assertEqual(len(result), 2)

        result_most_recent = self.test_session.get_correlator_config_status()
        self.assertEqual(len(result_most_recent), 1)

        result = self.test_session.get_correlator_config_status(
            starttime=t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_add_correlator_config_from_corrcm(self):
        corr_config_list = self.test_session.add_correlator_config_from_corrcm(
            config_state_dict=corr_config_example_dict, testing=True)

        for obj in corr_config_list:
            self.test_session.add(obj)
            self.test_session.commit()

        t1 = Time(1512770942.726777, format='unix')
        status_result = self.test_session.get_correlator_config_status(
            starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(status_result), 1)
        file_result = self.test_session.get_correlator_config_file(
            status_result[0].config_hash)

        config_filename = 'correlator_config_' + str(int(floor(t1.gps))) + '.yaml'

        file_expected = corr.CorrelatorConfigFile(config_hash='testhash',
                                                  filename=config_filename)
        status_expected = corr.CorrelatorConfigStatus(time=int(floor(t1.gps)),
                                                      config_hash='testhash')

        self.assertEqual(len(file_result), 1)
        file_result = file_result[0]
        self.assertTrue(file_result.isclose(file_expected))

        self.assertEqual(len(status_result), 1)
        status_result = status_result[0]
        self.assertTrue(status_result.isclose(status_expected))

    def test_add_correlator_config_from_corrcm_match_prior(self):
        # test behavior when matching config exists at an earlier time
        t1 = Time(1512770942.726777, format='unix')
        t0 = t1 - TimeDelta(30, format='sec')
        config_hash = 'testhash'
        config_filename = 'correlator_config_' + str(int(floor(t1.gps))) + '.yaml'
        self.test_session.add_correlator_config_file(config_hash, config_filename)
        self.test_session.commit()
        self.test_session.add_correlator_config_status(t0, config_hash)
        self.test_session.commit()

        corr_config_list = self.test_session.add_correlator_config_from_corrcm(
            config_state_dict=corr_config_example_dict, testing=True)

        status_expected = corr.CorrelatorConfigStatus(time=int(floor(t1.gps)),
                                                      config_hash='testhash')

        self.assertTrue(corr_config_list[0].isclose(status_expected))

    def test_add_correlator_config_from_corrcm_duplicate(self):
        # test behavior when duplicate config exists
        t1 = Time(1512770942.726777, format='unix')
        config_hash = 'testhash'
        config_filename = 'correlator_config_' + str(int(floor(t1.gps))) + '.yaml'
        self.test_session.add_correlator_config_file(config_hash, config_filename)
        self.test_session.commit()
        self.test_session.add_correlator_config_status(t1, config_hash)
        self.test_session.commit()

        corr_config_list = self.test_session.add_correlator_config_from_corrcm(
            config_state_dict=corr_config_example_dict, testing=True)

        self.assertEqual(len(corr_config_list), 0)

    def test_config_errors(self):
        self.assertRaises(ValueError, self.test_session.add_correlator_config_status,
                          'foo', 'testhash')

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_add_correlator_config_from_corrcm_onsite(self):

        result = self.test_session.add_correlator_config_from_corrcm(testing=True)

        self.assertTrue(len(result) > 0)
        if len(result) == 2:
            self.assertEqual(result[0].__class__, corr.CorrelatorConfigFile)
            self.assertEqual(result[1].__class__, corr.CorrelatorConfigStatus)
        else:
            self.assertEqual(result[0].__class__, corr.CorrelatorConfigStatus)


class TestCorrelatorControlCommand(TestHERAMC):

    def test_control_command_no_recent_status(self):
        # test things on & off with no recent status
        commands_to_test = list(corr.command_dict.keys())
        commands_to_test.remove('take_data')
        commands_to_test.remove('update_config')
        for command in commands_to_test:
            command_list = self.test_session.correlator_control_command(
                command, testing=True)

            self.assertEqual(len(command_list), 1)
            command_time = command_list[0].time
            self.assertTrue(Time.now().gps - command_time < 2.)

            command_time_obj = Time(command_time, format='gps')
            expected = corr.CorrelatorControlCommand.create(command_time_obj,
                                                            command)

            self.assertTrue(command_list[0].isclose(expected))

            # test adding the command(s) to the database and retrieving them
            for cmd in command_list:
                self.test_session.add(cmd)
            result_list = self.test_session.get_correlator_control_command(
                starttime=Time.now() - TimeDelta(10, format='sec'),
                stoptime=Time.now() + TimeDelta(10, format='sec'), command=command)
            self.assertEqual(len(result_list), 1)
            self.assertTrue(command_list[0].isclose(result_list[0]))

    def test_take_data_command_no_recent_status(self):
        # test take_data command with no recent status
        starttime = Time.now() + TimeDelta(10, format='sec')
        starttime_sec = floor(starttime.gps)
        starttime_ms_offset = floor((starttime.gps - floor(starttime.gps)) * 1000)

        command_list = self.test_session.correlator_control_command(
            'take_data', starttime=starttime, duration=100, tag='engineering',
            testing=True)

        self.assertEqual(len(command_list), 2)
        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        command_time_obj = Time(command_time, format='gps')
        expected_comm = corr.CorrelatorControlCommand.create(command_time_obj,
                                                             'take_data')

        self.assertTrue(command_list[0].isclose(expected_comm))

        int_time = corr.DEFAULT_ACCLEN_SPECTRA * ((2.0 * 16384) / 500e6)
        expected_args = corr.CorrelatorTakeDataArguments.create(
            command_time_obj, starttime, 100, corr.DEFAULT_ACCLEN_SPECTRA,
            int_time, 'engineering')

        self.assertTrue(command_list[1].isclose(expected_args))

        # check warning with non-standard acclen_spectra
        command_list = checkWarnings(self.test_session.correlator_control_command,
                                     ['take_data'],
                                     {'starttime': starttime, 'duration': 100,
                                      'acclen_spectra': 2048, 'tag': 'engineering',
                                      'testing': True, 'overwrite_take_data': True},
                                     message='Using a non-standard acclen_spectra')

        self.assertEqual(len(command_list), 2)
        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        command_time_obj = Time(command_time, format='gps')
        expected_comm = corr.CorrelatorControlCommand.create(command_time_obj,
                                                             'take_data')
        self.assertTrue(command_list[0].isclose(expected_comm))

        int_time = 2048 * ((2.0 * 16384) / 500e6)
        expected_args = corr.CorrelatorTakeDataArguments.create(
            command_time_obj, starttime, 100, 2048,
            int_time, 'engineering')

        self.assertTrue(command_list[1].isclose(expected_args))

    def test_control_command_with_recent_status(self):
        # test things on & off with a recent status
        commands_to_test = list(corr.command_dict.keys())
        commands_to_test.remove('take_data')
        commands_to_test.remove('update_config')
        commands_to_test.remove('restart')
        for command in commands_to_test:
            state_type = corr.command_state_map[command]['state_type']
            state = corr.command_state_map[command]['state']

            t1 = Time.now() - TimeDelta(30 + 60, format='sec')
            self.test_session.add_correlator_control_state(t1, state_type, state)

            command_list = self.test_session.correlator_control_command(
                command, testing=True)
            self.assertEqual(len(command_list), 0)

            t2 = Time.now() - TimeDelta(30, format='sec')
            self.test_session.add_correlator_control_state(t2, state_type, not(state))

            command_list = self.test_session.correlator_control_command(
                command, testing=True)

            self.assertEqual(len(command_list), 1)
            command_time = command_list[0].time
            self.assertTrue(Time.now().gps - command_time < 2.)

            command_time_obj = Time(command_time, format='gps')
            expected = corr.CorrelatorControlCommand.create(command_time_obj,
                                                            command)
            self.assertTrue(command_list[0].isclose(expected))

            self.test_session.rollback()

            result = self.test_session.get_correlator_control_state(most_recent=True,
                                                                    state_type=state_type)
            self.assertEqual(len(result), 0)

    def test_take_data_command_with_recent_status(self):
        # test take_data command with recent status
        t1 = Time.now() - TimeDelta(60, format='sec')
        self.test_session.add_correlator_control_state(t1, 'taking_data', True)

        self.assertRaises(RuntimeError, self.test_session.correlator_control_command,
                          'take_data', starttime=Time.now() + TimeDelta(10, format='sec'),
                          duration=100, tag='engineering', testing=True)

        t2 = Time.now() - TimeDelta(30, format='sec')
        self.test_session.add_correlator_control_state(t2, 'taking_data', False)

        t3 = Time.now() + TimeDelta(10, format='sec')
        control_command_objs = self.test_session.correlator_control_command(
            'take_data', starttime=t3, duration=100, tag='engineering', testing=True)
        for obj in control_command_objs:
            self.test_session.add(obj)
            self.test_session.commit()

        time.sleep(1)

        starttime = Time.now() + TimeDelta(10, format='sec')
        self.assertRaises(RuntimeError, self.test_session.correlator_control_command,
                          'take_data', starttime=starttime + TimeDelta(30, format='sec'),
                          duration=100, tag='engineering', testing=True)

        starttime_ms_offset = floor((starttime.gps - floor(starttime.gps)) * 1000)

        command_list = checkWarnings(self.test_session.correlator_control_command,
                                     ['take_data'],
                                     {'starttime': starttime, 'duration': 100,
                                      'tag': 'engineering', 'testing': True,
                                      'overwrite_take_data': True},
                                     message='Correlator was commanded to take data')

        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        command_time_obj = Time(command_time, format='gps')
        expected_comm = corr.CorrelatorControlCommand.create(command_time_obj,
                                                             'take_data')
        self.assertTrue(command_list[0].isclose(expected_comm))

        int_time = corr.DEFAULT_ACCLEN_SPECTRA * ((2.0 * 16384) / 500e6)
        expected_args = corr.CorrelatorTakeDataArguments.create(
            command_time_obj, starttime, 100, corr.DEFAULT_ACCLEN_SPECTRA,
            int_time, 'engineering')
        self.assertTrue(command_list[1].isclose(expected_args))

        for obj in command_list:
            self.test_session.add(obj)
            self.test_session.commit()

        result_args = self.test_session.get_correlator_take_data_arguments(most_recent=True,
                                                                           use_command_time=True)
        self.assertEqual(len(result_args), 1)
        self.assertTrue(result_args[0].isclose(expected_args))

        result_args = self.test_session.get_correlator_take_data_arguments(starttime=Time.now())
        self.assertEqual(len(result_args), 1)
        self.assertFalse(result_args[0].isclose(expected_args))

    def test_control_command_errors(self):
        # test bad command
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'foo', testing=True)

        # test not setting required values for 'take_data'
        starttime = Time.now() + TimeDelta(10, format='sec')
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime=starttime, duration=100,
                          testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime=starttime, tag='engineering',
                          testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', duration=100, tag='engineering', testing=True)

        # test bad values for 'take_data'
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime='foo', duration=100,
                          tag='engineering', testing=True)

        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime=starttime, duration=100,
                          tag='foo', testing=True)

        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime=starttime, duration=100,
                          tag='engineering', acclen_spectra=2, testing=True)

        # test setting values for 'take_data' with other commands
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'noise_diode_on', starttime=starttime,
                          testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'phase_switching_off', duration=100, testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'restart', acclen_spectra=corr.DEFAULT_ACCLEN_SPECTRA,
                          testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'noise_diode_off', tag='engineering', testing=True)

        # test bad commands while taking data
        t1 = Time.now() - TimeDelta(60, format='sec')
        self.test_session.add_correlator_control_state(t1, 'taking_data', True)

        commands_to_test = list(corr.command_dict.keys())
        commands_to_test.remove('stop_taking_data')
        commands_to_test.remove('take_data')
        commands_to_test.remove('update_config')
        for command in commands_to_test:
            self.assertRaises(RuntimeError, self.test_session.correlator_control_command,
                              command, testing=True)

        self.assertRaises(ValueError, corr.CorrelatorControlCommand.create,
                          'foo', 'take_data')

        t1 = Time('2016-01-10 01:15:23', scale='utc')
        self.assertRaises(ValueError, corr.CorrelatorTakeDataArguments.create,
                          'foo', t1, 100, 2, 2 * ((2.0 * 16384) / 500e6), 'engineering')

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_get_integration_time(self):

        n_spectra = 147456
        int_time = corr._get_integration_time(n_spectra)

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_get_next_start_time(self):
        next_starttime = corr._get_next_start_time()


class TestCorrelatorConfigCommand(TestHERAMC):

    def test_corr_config_command_no_recent_config(self):
        # test commanding a config with no recent config status
        t1 = Time.now()

        with open(config_file, 'r') as fh:
            config_string = fh.read().encode('utf-8')
            config_hash = hashlib.md5(config_string).hexdigest()

        command_list = self.test_session.correlator_control_command('update_config',
                                                                    config_file=config_file,
                                                                    testing=True)
        self.assertEqual(len(command_list), 3)

        # test adding the config obj(s) to the database and retrieving them
        for obj in command_list:
            self.test_session.add(obj)
            self.test_session.commit()

        file_expected = corr.CorrelatorConfigFile(config_hash=config_hash,
                                                  filename=config_file)
        self.assertTrue(command_list[0].isclose(file_expected))

        file_result = self.test_session.get_correlator_config_file(config_hash)
        self.assertEqual(len(file_result), 1)
        file_result = file_result[0]
        self.assertTrue(file_result.isclose(file_expected))

        command_time = command_list[1].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        command_time_obj = Time(command_time, format='gps')
        expected_comm = corr.CorrelatorControlCommand.create(command_time_obj,
                                                             'update_config')

        self.assertTrue(command_list[1].isclose(expected_comm))

        config_comm_expected = corr.CorrelatorConfigCommand.create(command_time_obj,
                                                                   config_hash)

        self.assertTrue(command_list[2].isclose(config_comm_expected))

        config_comm_result = self.test_session.get_correlator_config_command(
            starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(config_comm_result), 1)
        config_comm_result = config_comm_result[0]
        self.assertTrue(config_comm_result.isclose(config_comm_expected))

    def test_corr_config_command_with_recent_config(self):
        # test commanding a config with a recent (different) config status
        corr_config_list = self.test_session.add_correlator_config_from_corrcm(
            config_state_dict=corr_config_example_dict, testing=True)

        for obj in corr_config_list:
            self.test_session.add(obj)
            self.test_session.commit()

        t1 = Time.now()

        with open(config_file, 'r') as fh:
            config_string = fh.read().encode('utf-8')
            config_hash = hashlib.md5(config_string).hexdigest()

        command_list = self.test_session.correlator_control_command('update_config',
                                                                    config_file=config_file,
                                                                    testing=True)
        self.assertEqual(len(command_list), 3)

        # test adding the config obj(s) to the database and retrieving them
        for obj in command_list:
            self.test_session.add(obj)
            self.test_session.commit()

        file_expected = corr.CorrelatorConfigFile(config_hash=config_hash,
                                                  filename=config_file)
        self.assertTrue(command_list[0].isclose(file_expected))

        file_result = self.test_session.get_correlator_config_file(config_hash)
        self.assertEqual(len(file_result), 1)
        file_result = file_result[0]
        self.assertTrue(file_result.isclose(file_expected))

        command_time = command_list[1].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        command_time_obj = Time(command_time, format='gps')
        expected_comm = corr.CorrelatorControlCommand.create(command_time_obj,
                                                             'update_config')

        self.assertTrue(command_list[1].isclose(expected_comm))

        self.assertTrue(Time.now().gps - command_time < 2.)
        config_comm_expected = corr.CorrelatorConfigCommand.create(command_time_obj,
                                                                   config_hash)

        self.assertTrue(command_list[2].isclose(config_comm_expected))

        config_comm_result = self.test_session.get_correlator_config_command(
            starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(config_comm_result), 1)
        config_comm_result = config_comm_result[0]
        self.assertTrue(config_comm_result.isclose(config_comm_expected))

    def test_corr_config_command_with_recent_config_match_prior(self):
        # test commanding a config with a recent (different) config status but a matching prior one
        t1 = Time.now()
        t0 = Time(1512760942, format='unix')

        with open(config_file, 'r') as fh:
            config_string = fh.read().encode('utf-8')
            config_hash = hashlib.md5(config_string).hexdigest()

        # put in a previous matching config
        matching_corr_config_dict = {'time': t0, 'hash': config_hash,
                                     'config': config}
        corr_config_list = self.test_session.add_correlator_config_from_corrcm(
            config_state_dict=matching_corr_config_dict, testing=True)

        for obj in corr_config_list:
            self.test_session.add(obj)
            self.test_session.commit()

        config_filename = 'correlator_config_' + str(int(floor(t0.gps))) + '.yaml'
        file_expected = corr.CorrelatorConfigFile(config_hash=config_hash,
                                                  filename=config_filename)

        file_result = self.test_session.get_correlator_config_file(config_hash)
        self.assertEqual(len(file_result), 1)
        file_result = file_result[0]
        self.assertTrue(file_result.isclose(file_expected))

        # make more recent one that doesn't match
        corr_config_list = self.test_session.add_correlator_config_from_corrcm(
            config_state_dict=corr_config_example_dict, testing=True)

        for obj in corr_config_list:
            self.test_session.add(obj)
            self.test_session.commit()

        command_list = self.test_session.correlator_control_command('update_config',
                                                                    config_file=config_file,
                                                                    testing=True)
        self.assertEqual(len(command_list), 2)

        # test adding the config obj(s) to the database and retrieving them
        for obj in command_list:
            self.test_session.add(obj)
            self.test_session.commit()

        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        command_time_obj = Time(command_time, format='gps')
        expected_comm = corr.CorrelatorControlCommand.create(command_time_obj,
                                                             'update_config')

        self.assertTrue(command_list[0].isclose(expected_comm))

        config_comm_expected = corr.CorrelatorConfigCommand.create(command_time_obj,
                                                                   config_hash)

        self.assertTrue(command_list[1].isclose(config_comm_expected))

        config_comm_result = self.test_session.get_correlator_config_command(
            starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(config_comm_result), 1)
        config_comm_result = config_comm_result[0]
        self.assertTrue(config_comm_result.isclose(config_comm_expected))

    def test_corr_config_command_same_recent_config(self):
        # test commanding a config with the same recent config status
        t1 = Time.now()
        t0 = Time(1512760942, format='unix')

        with open(config_file, 'r') as fh:
            config_string = fh.read().encode('utf-8')
            config_hash = hashlib.md5(config_string).hexdigest()

        # put in a previous matching config
        matching_corr_config_dict = {'time': t0, 'hash': config_hash,
                                     'config': config}
        corr_config_list = self.test_session.add_correlator_config_from_corrcm(
            config_state_dict=matching_corr_config_dict, testing=True)

        for obj in corr_config_list:
            self.test_session.add(obj)
            self.test_session.commit()

        config_filename = 'correlator_config_' + str(int(floor(t0.gps))) + '.yaml'
        file_expected = corr.CorrelatorConfigFile(config_hash=config_hash,
                                                  filename=config_filename)

        file_result = self.test_session.get_correlator_config_file(config_hash)
        self.assertEqual(len(file_result), 1)
        file_result = file_result[0]
        self.assertTrue(file_result.isclose(file_expected))

        command_list = self.test_session.correlator_control_command('update_config',
                                                                    config_file=config_file,
                                                                    testing=True)
        self.assertEqual(len(command_list), 0)

    def test_config_command_errors(self):
        self.assertRaises(ValueError, corr.CorrelatorConfigCommand.create,
                          'foo', 'testhash')

        # not setting config_file with 'update_config' command
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'update_config', testing=True)

        # setting config_file with other commands
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'restart', config_file=config_file, testing=True)

        starttime = Time.now() + TimeDelta(10, format='sec')
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime=starttime, duration=100,
                          tag='engineering', config_file=config_file, testing=True)


class TestCorrelatorSoftwareVersions(TestHERAMC):

    def test_add_correlator_software_versions(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        self.test_session.add_correlator_software_versions(t1, 'hera_corr_f',
                                                           '0.0.1-3c7fdaf6')

        expected = corr.CorrelatorSoftwareVersions(time=int(floor(t1.gps)),
                                                   package='hera_corr_f',
                                                   version='0.0.1-3c7fdaf6')
        result = self.test_session.get_correlator_software_versions(
            starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        self.test_session.add_correlator_software_versions(t1, 'hera_corr_cm',
                                                           '0.0.1-11a573c9')

        result = self.test_session.get_correlator_software_versions(
            starttime=t1 - TimeDelta(3.0, format='sec'), package='hera_corr_f')
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_correlator_software_versions(
            package='hera_corr_f')
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        expected = corr.CorrelatorSoftwareVersions(time=int(floor(t1.gps)),
                                                   package='hera_corr_cm',
                                                   version='0.0.1-11a573c9')

        result = self.test_session.get_correlator_software_versions(
            starttime=t1 - TimeDelta(3.0, format='sec'),
            package='hera_corr_cm')
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_correlator_software_versions(
            package='hera_corr_cm')
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result = self.test_session.get_correlator_software_versions(
            starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
        self.assertEqual(len(result), 2)

        result_most_recent = self.test_session.get_correlator_software_versions()
        self.assertEqual(len(result), 2)

        result = self.test_session.get_correlator_software_versions(
            starttime=t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_software_version_errors(self):
        self.assertRaises(ValueError,
                          self.test_session.add_correlator_software_versions,
                          'foo', 'hera_corr_cm', '0.0.1-11a573c9')


class TestSNAPConfigVersion(TestHERAMC):

    def test_add_snap_config_version(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        self.test_session.add_correlator_config_file('testhash', config_file)
        self.test_session.commit()
        self.test_session.add_correlator_config_status(t1, 'testhash')
        self.test_session.commit()

        self.test_session.add_snap_config_version(t1, '0.0.1-3c7fdaf6',
                                                  init_args, 'testhash')

        expected = corr.SNAPConfigVersion(init_time=int(floor(t1.gps)),
                                          version='0.0.1-3c7fdaf6',
                                          init_args=init_args,
                                          config_hash='testhash')

        result = self.test_session.get_snap_config_version(
            starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        self.test_session.add_correlator_config_file('testhash2', config_file)
        self.test_session.commit()
        self.test_session.add_correlator_config_status(t2, 'testhash2')
        self.test_session.commit()

        self.test_session.add_snap_config_version(t2, '0.0.1-11a573c9',
                                                  init_args, 'testhash2')

        expected = corr.SNAPConfigVersion(init_time=int(floor(t2.gps)),
                                          version='0.0.1-11a573c9',
                                          init_args=init_args,
                                          config_hash='testhash2')

        result = self.test_session.get_snap_config_version(
            starttime=t2 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_config_version()
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result = self.test_session.get_snap_config_version(
            starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t2)
        self.assertEqual(len(result), 2)

        result = self.test_session.get_snap_config_version(
            starttime=t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_software_version_errors(self):
        self.assertRaises(ValueError,
                          self.test_session.add_snap_config_version,
                          'foo', '0.0.1-3c7fdaf6', init_args, 'testhash')


class TestCorrelatorSNAPVersions(TestHERAMC):

    def test_add_corr_snap_versions_from_corrcm(self):
        # use testing to prevent call to hera_librarian to save new config file
        corr_snap_version_obj_list = self.test_session.add_corr_snap_versions_from_corrcm(
            corr_snap_version_dict=corr_snap_version_example_dict, testing=True)

        for obj in corr_snap_version_obj_list:
            self.test_session.add(obj)
            self.test_session.commit()

        t1 = Time(datetime.datetime(2019, 4, 2, 19, 7, 14), format='datetime')
        result = self.test_session.get_correlator_software_versions(
            starttime=t1 - TimeDelta(3.0, format='sec'))

        expected = corr.CorrelatorSoftwareVersions(time=int(floor(t1.gps)),
                                                   package='hera_corr_f:hera_snap_redis_monitor.py',
                                                   version='0.0.1-3c7fdaf6')
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_correlator_software_versions(
            package='hera_corr_f:hera_snap_redis_monitor.py')
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result_most_recent = self.test_session.get_correlator_software_versions()
        self.assertEqual(len(result_most_recent), 3)
        most_recent_packages = sorted([res.package for res in result_most_recent])
        expected_recent_packages = sorted(['udpSender:hera_node_keep_alive.py',
                                           'udpSender:hera_node_cmd_check.py',
                                           'hera_corr_cm'])
        self.assertEqual(most_recent_packages, expected_recent_packages)

        result = self.test_session.get_correlator_software_versions(
            starttime=t1 - TimeDelta(3.0, format='sec'),
            stoptime=t1 + TimeDelta(10.0, format='sec'))
        self.assertEqual(len(result), 5)

        t2 = Time(datetime.datetime(2019, 3, 27, 8, 28, 25), format='datetime')
        result = self.test_session.get_snap_config_version(
            starttime=t2 - TimeDelta(3.0, format='sec'))

        expected = corr.SNAPConfigVersion(init_time=int(floor(t2.gps)),
                                          version='0.0.1-3c7fdaf6',
                                          init_args=init_args,
                                          config_hash='testhash')
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_config_version()
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        t3 = Time(datetime.datetime(2019, 2, 18, 5, 41, 29), format='datetime')
        result = self.test_session.get_correlator_config_status(
            starttime=t3 - TimeDelta(3.0, format='sec'))

        expected = corr.CorrelatorConfigStatus(time=int(floor(t3.gps)),
                                               config_hash='testhash')
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_correlator_config_status()
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        # test that a new hera_corr_cm timestamp with the same version doesn't make a new row
        new_dict = copy.deepcopy(corr_snap_version_example_dict)
        new_dict['hera_corr_cm']['timestamp'] = (
            datetime.datetime(2019, 4, 2, 19, 8, 17, 644984))

        corr_snap_version_obj_list = self.test_session.add_corr_snap_versions_from_corrcm(
            corr_snap_version_dict=new_dict)

        t4 = Time(datetime.datetime(2019, 4, 2, 19, 7, 17), format='datetime')
        t5 = Time(datetime.datetime(2019, 4, 2, 19, 8, 17), format='datetime')

        expected = corr.CorrelatorSoftwareVersions(time=int(floor(t4.gps)),
                                                   package='hera_corr_cm',
                                                   version='0.0.1-11a573c9')

        result = self.test_session.get_correlator_software_versions(
            starttime=t4 - TimeDelta(3.0, format='sec'),
            stoptime=t5 + TimeDelta(10.0, format='sec'),
            package='hera_corr_cm')

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].isclose(expected))

        # test that a new hera_corr_cm timestamp with a new version makes a new row
        new_dict = copy.deepcopy(corr_snap_version_example_dict)
        new_dict['hera_corr_cm']['timestamp'] = (
            datetime.datetime(2019, 4, 2, 19, 8, 17, 644984))
        new_dict['hera_corr_cm']['version'] = '0.0.1-b43b2b72'

        corr_snap_version_obj_list = self.test_session.add_corr_snap_versions_from_corrcm(
            corr_snap_version_dict=new_dict)

        expected = corr.CorrelatorSoftwareVersions(time=int(floor(t5.gps)),
                                                   package='hera_corr_cm',
                                                   version='0.0.1-b43b2b72')

        result = self.test_session.get_correlator_software_versions(
            starttime=t4 - TimeDelta(3.0, format='sec'),
            stoptime=t5 + TimeDelta(10.0, format='sec'),
            package='hera_corr_cm')

        self.assertEqual(len(result), 2)
        self.assertTrue(result[1].isclose(expected))

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_add_corr_command_state_from_corrcm(self):

        self.test_session.add_corr_snap_versions_from_corrcm()

        result = self.test_session.get_correlator_software_versions(
            package='hera_corr_cm', most_recent=True)
        self.assertEqual(len(result), 1)

        result = self.test_session.get_correlator_software_versions()
        self.assertTrue(len(result) >= 1)

        result = self.test_session.get_snap_config_version()
        self.assertEqual(len(result), 1)


class TestSNAPStatus(TestHERAMC):

    def test_add_snap_status(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        t_prog = Time('2016-01-05 20:00:00', scale='utc')
        self.test_session.add_snap_status(t1, 'heraNode23Snap1', 'SNPA000222',
                                          False, 595687, 57.984954833984375,
                                          595686, t_prog)

        expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                                   hostname='heraNode23Snap1',
                                   serial_number='SNPA000222', node=23, snap_loc_num=1,
                                   psu_alert=False, pps_count=595687,
                                   fpga_temp=57.984954833984375, uptime_cycles=595686,
                                   last_programmed_time=int(floor(t_prog.gps)))
        result = self.test_session.get_snap_status(starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        self.test_session.add_snap_status(t1, 'heraNode4Snap0', 'SNPA000224',
                                          True, 595699, 59.323028564453125,
                                          595699, t_prog)

        result = self.test_session.get_snap_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                   nodeID=23)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_status(nodeID=23)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                                   hostname='heraNode4Snap0',
                                   serial_number='SNPA000224', node=4, snap_loc_num=0,
                                   psu_alert=True, pps_count=595699,
                                   fpga_temp=59.323028564453125, uptime_cycles=595699,
                                   last_programmed_time=int(floor(t_prog.gps)))

        result = self.test_session.get_snap_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                   nodeID=4)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_status(nodeID=4)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result = self.test_session.get_snap_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                   stoptime=t1)
        self.assertEqual(len(result), 2)

        result_most_recent = self.test_session.get_snap_status()
        self.assertEqual(len(result), 2)

        result = self.test_session.get_snap_status(starttime=t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_add_snap_status_from_corrcm(self):
        self.test_session.add_snap_status_from_corrcm(
            snap_status_dict=snap_status_example_dict)

        t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format='datetime')
        t_prog = Time(datetime.datetime(2016, 1, 10, 23, 16, 3), format='datetime')
        result = self.test_session.get_snap_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=23)

        expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                                   hostname='heraNode23Snap1',
                                   serial_number='SNPA000222', node=23, snap_loc_num=1,
                                   psu_alert=False, pps_count=595687,
                                   fpga_temp=57.984954833984375, uptime_cycles=595686,
                                   last_programmed_time=int(floor(t_prog.gps)))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_status(nodeID=23)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result = self.test_session.get_snap_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=4)

        expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                                   hostname='heraNode4Snap0',
                                   serial_number='SNPA000224', node=4, snap_loc_num=0,
                                   psu_alert=False, pps_count=595699,
                                   fpga_temp=59.323028564453125, uptime_cycles=595699,
                                   last_programmed_time=int(floor(t_prog.gps)))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_status()
        self.assertEqual(len(result_most_recent), 2)

    def test_add_snap_status_from_corrcm_with_nones(self):
        snap_status_obj_list = self.test_session.add_snap_status_from_corrcm(
            snap_status_dict=snap_status_none_example_dict, testing=True)

        for obj in snap_status_obj_list:
            self.test_session.add(obj)

        t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format='datetime')
        result = self.test_session.get_snap_status(
            starttime=t1 - TimeDelta(3.0, format='sec'))

        expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                                   hostname='heraNode23Snap1',
                                   serial_number=None, node=None, snap_loc_num=None,
                                   psu_alert=None, pps_count=None,
                                   fpga_temp=None, uptime_cycles=None,
                                   last_programmed_time=None)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

    def test_snap_status_errors(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')

        self.assertRaises(ValueError, self.test_session.add_snap_status,
                          'foo', 'heraNode23Snap1', 'SNPA000222', False,
                          595687, 57.984954833984375, 595686, t1)

        self.assertRaises(ValueError, self.test_session.add_snap_status,
                          t1, 'heraNode23Snap1', 'SNPA000222', False, 595687,
                          57.984954833984375, 595686, 'foo')

    def test_get_node_snap_from_serial_errors(self):
        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['foo'],
                                           message='No active dossiers')

        self.assertTrue(node is None)
        self.assertTrue(snap_loc_num is None)

        # test multiple snap location numbers
        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['SNPC000017'],
                                           message='Multiple snap location numbers returned')
        self.assertEqual(node, 0)
        self.assertTrue(snap_loc_num is None)

        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['SNPC000018'],
                                           message='Multiple node connections returned')
        self.assertTrue(node is None)
        self.assertTrue(snap_loc_num is None)

        # test multiple node numbers
        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['SNPC000018'],
                                           message='Multiple node connections returned')
        self.assertTrue(node is None)
        self.assertTrue(snap_loc_num is None)

        # test multiple node revisions
        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['SNPC000019'],
                                           message='Multiple node connections returned')
        self.assertTrue(node is None)
        self.assertTrue(snap_loc_num is None)

        # test multiple times
        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['SNPC000020'], nwarnings=0)
        self.assertEqual(node, 4)
        self.assertEqual(snap_loc_num, 3)

        # test multiple times with change in location
        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['SNPC000021'], nwarnings=0)
        self.assertEqual(node, 5)
        self.assertEqual(snap_loc_num, 0)

        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['SNPB000005'],
                                           message='Multiple active dossiers returned')
        self.assertTrue(node is None)
        self.assertTrue(snap_loc_num is None)

        node, snap_loc_num = self.test_session._get_node_snap_from_serial('SNPA000312')
        self.assertTrue(snap_loc_num is None)

        node, snap_loc_num = self.test_session._get_node_snap_from_serial('SNPA000313')
        self.assertTrue(snap_loc_num is None)

        node, snap_loc_num = self.test_session._get_node_snap_from_serial('SNPA000314')
        self.assertTrue(node is None)

        node, snap_loc_num = self.test_session._get_node_snap_from_serial('SNPA000315')
        self.assertTrue(node is None)

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_site_add_snap_status_from_corrcm(self):

        # get the snap status dict from the correlator redis
        snap_status_dict = corr._get_snap_status()

        # use the real (not test) database to get the node & snap location number
        real_db = mc.connect_to_mc_db(None)
        real_session = real_db.sessionmaker()

        self.test_session.add_snap_status_from_corrcm(cm_session=real_session)
        result = self.test_session.get_snap_status(most_recent=True)
        self.assertTrue(len(result) >= 1)


class TestAntennaStatus(TestHERAMC):

    def test_add_antenna_status(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        t_prog = Time('2016-01-05 20:00:00', scale='utc')
        eq_coeffs = (np.zeros((5)) + 56.921875).tolist()
        self.test_session.add_antenna_status(t1, 4, 'e', 'heraNode23Snap1', 3,
                                             -0.5308380126953125, 3.0134560488579285,
                                             9.080917358398438, 0, -13.349140985640002,
                                             eq_coeffs)

        eq_coeffs_string = '[56.921875,56.921875,56.921875,56.921875,56.921875]'
        expected = corr.AntennaStatus(time=int(floor(t1.gps)), antenna_number=4,
                                      antenna_feed_pol='e',
                                      snap_hostname='heraNode23Snap1',
                                      snap_channel_number=3,
                                      adc_mean=-0.5308380126953125,
                                      adc_rms=3.0134560488579285,
                                      adc_power=9.080917358398438, pam_atten=0,
                                      pam_power=-13.349140985640002,
                                      eq_coeffs=eq_coeffs_string)

        result = self.test_session.get_antenna_status(starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        eq_coeffs = (np.zeros((5)) + 73.46875).tolist()
        self.test_session.add_antenna_status(t2, 31, 'n', 'heraNode4Snap3', 7,
                                             -0.4805450439453125, 16.495319974304454,
                                             272.0955810546875, 0, -32.03119784856,
                                             eq_coeffs)

        result = self.test_session.get_antenna_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                      antenna_number=4)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_antenna_status(antenna_number=4)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        eq_coeffs_string = '[73.46875,73.46875,73.46875,73.46875,73.46875]'
        expected = corr.AntennaStatus(time=int(floor(t2.gps)), antenna_number=31,
                                      antenna_feed_pol='n',
                                      snap_hostname='heraNode4Snap3',
                                      snap_channel_number=7,
                                      adc_mean=-0.4805450439453125,
                                      adc_rms=16.495319974304454,
                                      adc_power=272.0955810546875, pam_atten=0,
                                      pam_power=-32.03119784856,
                                      eq_coeffs=eq_coeffs_string)

        result = self.test_session.get_antenna_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                      antenna_number=31)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_antenna_status(antenna_number=31)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result = self.test_session.get_antenna_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                      stoptime=t1)
        self.assertEqual(len(result), 1)

        result_most_recent = self.test_session.get_antenna_status()
        self.assertEqual(len(result), 1)

        result = self.test_session.get_antenna_status(starttime=t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_add_antenna_status_from_corrcm(self):
        ant_status_obj_list = self.test_session.add_antenna_status_from_corrcm(
            ant_status_dict=ant_status_example_dict, testing=True)

        for obj in ant_status_obj_list:
            self.test_session.add(obj)

        t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format='datetime')
        result = self.test_session.get_antenna_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), antenna_number=4)

        eq_coeffs_str = [str(val) for val in (np.zeros((1024)) + 56.921875).tolist()]
        eq_coeffs_string = '[' + ','.join(eq_coeffs_str) + ']'
        expected = corr.AntennaStatus(time=int(floor(t1.gps)), antenna_number=4,
                                      antenna_feed_pol='e',
                                      snap_hostname='heraNode23Snap1',
                                      snap_channel_number=3,
                                      adc_mean=-0.5308380126953125,
                                      adc_rms=3.0134560488579285,
                                      adc_power=9.080917358398438, pam_atten=0,
                                      pam_power=-13.349140985640002,
                                      eq_coeffs=eq_coeffs_string)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_antenna_status(antenna_number=4)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result = self.test_session.get_antenna_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), antenna_number=31)

        eq_coeffs_str = [str(val) for val in (np.zeros((1024)) + 73.46875).tolist()]
        eq_coeffs_string = '[' + ','.join(eq_coeffs_str) + ']'
        expected = corr.AntennaStatus(time=int(floor(t1.gps)), antenna_number=31,
                                      antenna_feed_pol='n',
                                      snap_hostname='heraNode4Snap3',
                                      snap_channel_number=7,
                                      adc_mean=-0.4805450439453125,
                                      adc_rms=16.495319974304454,
                                      adc_power=272.0955810546875, pam_atten=0,
                                      pam_power=-32.03119784856,
                                      eq_coeffs=eq_coeffs_string)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_antenna_status()
        self.assertEqual(len(result_most_recent), 2)

    def test_add_antenna_status_from_corrcm_with_nones(self):
        self.test_session.add_antenna_status_from_corrcm(
            ant_status_dict=ant_status_nones_example_dict)

        t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format='datetime')
        result = self.test_session.get_antenna_status(
            starttime=t1 - TimeDelta(3.0, format='sec'))

        expected = corr.AntennaStatus(time=int(floor(t1.gps)), antenna_number=4,
                                      antenna_feed_pol='e',
                                      snap_hostname=None, snap_channel_number=None,
                                      adc_mean=None, adc_rms=None,
                                      adc_power=None, pam_atten=None,
                                      pam_power=None, eq_coeffs=None)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

    def test_snap_status_errors(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')

        eq_coeffs = (np.zeros((5)) + 56.921875).tolist()
        self.assertRaises(ValueError, self.test_session.add_antenna_status,
                          'foo', 4, 'e', 'heraNode23Snap1', 3, -0.5308380126953125,
                          3.0134560488579285, 9.080917358398438, 0,
                          -13.349140985640002, eq_coeffs)

        self.assertRaises(ValueError, self.test_session.add_antenna_status,
                          t1, 4, 'x', 'heraNode23Snap1', 3, -0.5308380126953125,
                          3.0134560488579285, 9.080917358398438, 0,
                          -13.349140985640002, eq_coeffs)

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_site_add_antenna_status_from_corrcm(self):

        self.test_session.add_antenna_status_from_corrcm()
        result = self.test_session.get_antenna_status(most_recent=True)
        self.assertTrue(len(result) >= 1)


if __name__ == '__main__':
    unittest.main()
