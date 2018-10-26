# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.correlator`.

"""
from __future__ import absolute_import, division, print_function

import unittest
import nose.tools as nt
from math import floor
from astropy.time import Time, TimeDelta

from hera_mc import mc
import hera_mc.correlator as corr
from ..tests import TestHERAMC, is_onsite


corr_command_example_dict = {
    'taking_data': {'state': True, 'timestamp': Time(1512770942, format='unix').to_datetime()},
    'phase_switching': {'state': False, 'timestamp': Time(1512770944, format='unix').to_datetime()},
    'noise_diode': {'state': True, 'timestamp': Time(1512770946, format='unix').to_datetime()},
}


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

    def test_create_control_state(self):
        corr_state_obj_list = corr.create_control_state(corr_state_dict=corr_command_example_dict)

        for obj in corr_state_obj_list:
            self.test_session.add(obj)

        t1 = Time(1512770942.726777, format='unix')
        result = self.test_session.get_correlator_control_state(starttime=t1 - TimeDelta(3.0, format='sec'))

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

    def test_add_corr_command_state_from_corrcm(self):

        if is_onsite():
            self.test_session.add_correlator_control_state_from_corrcm()
            result = self.test_session.get_correlator_control_state(state_type='taking_data', most_recent=True)
            self.assertEqual(len(result), 1)
            result = self.test_session.get_correlator_control_state(state_type='phase_switching', most_recent=True)
            self.assertEqual(len(result), 1)
            result = self.test_session.get_correlator_control_state(state_type='noise_diode', most_recent=True)
            self.assertEqual(len(result), 1)


class TestCorrelatorControlCommand(TestHERAMC):

    def test_control_command_no_recent_status(self):
        # test things on & off with no recent status
        commands_to_test = list(corr.command_dict.keys())
        commands_to_test.remove('take_data')
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
        starttime_ms_offset = floor((starttime.gps - floor(starttime.gps)) * 1000)

        command_list = self.test_session.correlator_control_command(
            'take_data', starttime=starttime,
            duration=100, acclen_spectra=2, tag='engineering', testing=True)

        self.assertEqual(len(command_list), 2)
        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        expected_comm = corr.CorrelatorControlCommand(time=command_time, command='take_data')
        self.assertTrue(command_list[0].isclose(expected_comm))

        int_time = 2 * 200e6 / 8192
        expected_args = corr.CorrelatorTakeDataArguments(time=command_time,
                                                         command='take_data',
                                                         starttime_sec=command_time + 10,
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
        commands_to_test.remove('restart')
        for command in commands_to_test:
            state_type = corr.command_state_map[command]['state_type']
            state = corr.command_state_map[command]['state']

            if state is True:
                tdelta = 60
            else:
                tdelta = 30
            t1 = Time.now() - TimeDelta(tdelta + 60, format='sec')
            self.test_session.add_correlator_control_state(t1, state_type, state)

            command_list = self.test_session.correlator_control_command(
                command, testing=True)
            self.assertEqual(len(command_list), 0)

            t2 = Time.now() - TimeDelta(tdelta, format='sec')
            self.test_session.add_correlator_control_state(t2, state_type, not(state))

            command_list = self.test_session.correlator_control_command(
                command, testing=True)

            self.assertEqual(len(command_list), 1)
            command_time = command_list[0].time
            self.assertTrue(Time.now().gps - command_time < 2.)

            expected = corr.CorrelatorControlCommand(time=command_time, command=command)
            self.assertTrue(command_list[0].isclose(expected))

    def test_take_data_command_with_recent_status(self):
        # test take_data command with recent status
        t1 = Time.now() - TimeDelta(60, format='sec')
        self.test_session.add_correlator_control_state(t1, 'taking_data', True)

        self.assertRaises(RuntimeError, self.test_session.correlator_control_command,
                          'take_data', starttime=Time.now() + TimeDelta(10, format='sec'),
                          duration=100, acclen_spectra=2, tag='engineering', testing=True)

    def test_control_command_errors(self):
        # test bad command
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'foo', testing=True)

        # test not setting required values for 'take_data'
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime=Time.now() + TimeDelta(10, format='sec'),
                          duration=100, acclen_spectra=2, testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime=Time.now() + TimeDelta(10, format='sec'),
                          duration=100, tag='engineering', testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', starttime=Time.now() + TimeDelta(10, format='sec'),
                          acclen_spectra=2, tag='engineering', testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'take_data', duration=100, acclen_spectra=2, tag='engineering',
                          testing=True)

        # test setting values for 'take_data' with other commands
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'noise_diode_on', starttime=Time.now() + TimeDelta(10, format='sec'),
                          testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'phase_switching_off', duration=100, testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'restart', acclen_spectra=2, testing=True)
        self.assertRaises(ValueError, self.test_session.correlator_control_command,
                          'noise_diode_off', tag='engineering', testing=True)


if __name__ == '__main__':
    unittest.main()
