# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.correlator`.

"""
from __future__ import absolute_import, division, print_function

import unittest
import os
import time
import datetime
import hashlib
import yaml
import nose.tools as nt
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
config = yaml.load(config_file)

corr_config_example_dict = {'timestamp': Time(1512770942, format='unix'),
                            'hash': 'testhash', 'config': config}

snap_status_example_dict = {
    'heraNode23Snap1': {'last_programmed': datetime.datetime(2016, 1, 10, 23, 16, 3),
                        'pmb_alert': False,
                        'pps_count': 595687,
                        'serial': 'SNPA000222',
                        'temp': 57.984954833984375,
                        'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
                        'uptime': 595686},
    'heraNode4Snap0': {'last_programmed': None,
                       'pmb_alert': False,
                       'pps_count': 595699,
                       'serial': 'SNPA000224',
                       'temp': 59.323028564453125,
                       'timestamp': datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
                       'uptime': 595699}}


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
            corr_state_dict=corr_state_dict_nonetime, testing=True)
        for obj in corr_state_obj_list:
            self.test_session.add(obj)

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
            corr_state_dict=corr_command_example_dict, testing=True)
        for obj in corr_state_obj_list:
            self.test_session.add(obj)

        corr_state_obj_list = self.test_session.add_correlator_control_state_from_corrcm(
            corr_state_dict=corr_state_dict_nonetime, testing=True)
        for obj in corr_state_obj_list:
            self.test_session.add(obj)

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
            corr_state_dict=not_taking_data_state_dict, testing=True)
        for obj in corr_state_obj_list:
            self.test_session.add(obj)

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

            expected = corr.CorrelatorControlCommand(time=command_time, command=command)
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

        expected_comm = corr.CorrelatorControlCommand(time=command_time, command='take_data')
        self.assertTrue(command_list[0].isclose(expected_comm))

        int_time = corr.DEFAULT_ACCLEN_SPECTRA * ((2.0 * 16384) / 500e6)
        expected_args = corr.CorrelatorTakeDataArguments(time=command_time,
                                                         command='take_data',
                                                         starttime_sec=starttime_sec,
                                                         starttime_ms=starttime_ms_offset,
                                                         duration=100,
                                                         acclen_spectra=corr.DEFAULT_ACCLEN_SPECTRA,
                                                         integration_time=int_time,
                                                         tag='engineering')
        self.assertTrue(command_list[1].isclose(expected_args))

        # check warning with non-standard acclen_spectra
        command_list = checkWarnings(self.test_session.correlator_control_command,
                                     ['take_data'],
                                     {'starttime': starttime, 'duration': 100,
                                      'acclen_spectra': 2, 'tag': 'engineering',
                                      'testing': True, 'overwrite_take_data': True},
                                     message='Using a non-standard acclen_spectra')

        self.assertEqual(len(command_list), 2)
        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        expected_comm = corr.CorrelatorControlCommand(time=command_time, command='take_data')
        self.assertTrue(command_list[0].isclose(expected_comm))

        int_time = 2 * ((2.0 * 16384) / 500e6)
        expected_args = corr.CorrelatorTakeDataArguments(time=command_time,
                                                         command='take_data',
                                                         starttime_sec=starttime_sec,
                                                         starttime_ms=starttime_ms_offset,
                                                         duration=100,
                                                         acclen_spectra=2,
                                                         integration_time=int_time,
                                                         tag='engineering')
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

            expected = corr.CorrelatorControlCommand(time=command_time, command=command)
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

        expected_comm = corr.CorrelatorControlCommand(time=command_time, command='take_data')
        self.assertTrue(command_list[0].isclose(expected_comm))

        int_time = corr.DEFAULT_ACCLEN_SPECTRA * ((2.0 * 16384) / 500e6)
        expected_args = corr.CorrelatorTakeDataArguments(time=command_time,
                                                         command='take_data',
                                                         starttime_sec=command_time + 10,
                                                         starttime_ms=starttime_ms_offset,
                                                         duration=100,
                                                         acclen_spectra=corr.DEFAULT_ACCLEN_SPECTRA,
                                                         integration_time=int_time,
                                                         tag='engineering')
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

        expected_comm = corr.CorrelatorControlCommand(time=command_time, command='update_config')
        self.assertTrue(command_list[1].isclose(expected_comm))

        config_comm_expected = corr.CorrelatorConfigCommand(time=command_time,
                                                            command='update_config',
                                                            config_hash=config_hash)

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

        expected_comm = corr.CorrelatorControlCommand(time=command_time, command='update_config')
        self.assertTrue(command_list[1].isclose(expected_comm))

        self.assertTrue(Time.now().gps - command_time < 2.)
        config_comm_expected = corr.CorrelatorConfigCommand(time=command_time,
                                                            command='update_config',
                                                            config_hash=config_hash)

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
        matching_corr_config_dict = {'timestamp': t0, 'hash': config_hash,
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

        expected_comm = corr.CorrelatorControlCommand(time=command_time, command='update_config')
        self.assertTrue(command_list[0].isclose(expected_comm))

        config_comm_expected = corr.CorrelatorConfigCommand(time=command_time,
                                                            command='update_config',
                                                            config_hash=config_hash)

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
        matching_corr_config_dict = {'timestamp': t0, 'hash': config_hash,
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
                                                   node=23)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_status(node=23)
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
                                                   node=4)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_status(node=4)
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
        snap_status_obj_list = self.test_session.add_snap_status_from_corrcm(
            snap_status_dict=snap_status_example_dict, testing=True)

        for obj in snap_status_obj_list:
            self.test_session.add(obj)

        t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format='datetime')
        t_prog = Time(datetime.datetime(2016, 1, 10, 23, 16, 3), format='datetime')
        result = self.test_session.get_snap_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), node=23)

        expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                                   hostname='heraNode23Snap1',
                                   serial_number='SNPA000222', node=23, snap_loc_num=1,
                                   psu_alert=False, pps_count=595687,
                                   fpga_temp=57.984954833984375, uptime_cycles=595686,
                                   last_programmed_time=int(floor(t_prog.gps)))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_status(node=23)
        self.assertEqual(len(result_most_recent), 1)
        result_most_recent = result_most_recent[0]
        self.assertTrue(result_most_recent.isclose(expected))

        result = self.test_session.get_snap_status(
            starttime=t1 - TimeDelta(3.0, format='sec'), node=4)

        expected = corr.SNAPStatus(time=int(floor(t1.gps)),
                                   hostname='heraNode4Snap0',
                                   serial_number='SNPA000224', node=4, snap_loc_num=0,
                                   psu_alert=False, pps_count=595699,
                                   fpga_temp=59.323028564453125, uptime_cycles=595699,
                                   last_programmed_time=None)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result_most_recent = self.test_session.get_snap_status()
        self.assertEqual(len(result_most_recent), 2)

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

        node, snap_loc_num = checkWarnings(self.test_session._get_node_snap_from_serial,
                                           ['SNPC000017'],
                                           message='Multiple downstream (i.e. node) connections')
        self.assertTrue(node is None)
        self.assertTrue(snap_loc_num is None)

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


if __name__ == '__main__':
    unittest.main()
