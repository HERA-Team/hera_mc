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


if __name__ == '__main__':
    unittest.main()
