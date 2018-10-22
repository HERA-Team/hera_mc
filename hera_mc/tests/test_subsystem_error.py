# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Testing for `hera_mc.subsystem_error`.
"""
from __future__ import absolute_import, division, print_function

import unittest
from math import floor
import numpy as np
from astropy.time import Time, TimeDelta

from .. import mc
from ..subsystem_error import SubsystemError
from ..tests import TestHERAMC


class TestSubsystemError(TestHERAMC):

    def setUp(self):
        super(TestSubsystemError, self).setUp()

        time = Time.now()
        self.subsystem_error_names = ['id', 'time', 'subsystem', 'mc_time',
                                      'severity', 'log']
        self.subsystem_error_values = [1, time, 'librarian', time, 1, 'bad problem']
        self.subsystem_error_columns = dict(zip(self.subsystem_error_names,
                                                self.subsystem_error_values))

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()

    def test_add_subsystem_error(self):
        exp_columns = self.subsystem_error_columns.copy()
        exp_columns['time'] = int(floor(exp_columns['time'].gps))
        exp_columns['mc_time'] = int(floor(exp_columns['mc_time'].gps))
        expected = SubsystemError(**exp_columns)

        self.test_session.add_subsystem_error(self.subsystem_error_values[1],
                                              self.subsystem_error_values[2],
                                              *self.subsystem_error_values[4:])

        result = self.test_session.get_subsystem_error(starttime=self.subsystem_error_columns['time']
                                                       - TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]

        self.assertTrue(result.isclose(expected))

        self.test_session.add_subsystem_error(self.subsystem_error_values[1], 'rtp',
                                              *self.subsystem_error_values[4:])
        result_subsystem = \
            self.test_session.get_subsystem_error(starttime=self.subsystem_error_columns['time']
                                                  - TimeDelta(2, format='sec'),
                                                  subsystem=self.subsystem_error_columns['subsystem'],
                                                  stoptime=self.subsystem_error_columns['time']
                                                  + TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result_subsystem), 1)
        result_subsystem = result_subsystem[0]
        self.assertTrue(result_subsystem.isclose(expected))

        result_mult = self.test_session.get_subsystem_error(starttime=self.subsystem_error_columns['time']
                                                            - TimeDelta(2, format='sec'),
                                                            stoptime=self.subsystem_error_columns['time']
                                                            + TimeDelta(2 * 60, format='sec'))

        self.assertEqual(len(result_mult), 2)
        ids = [res.id for res in result_mult]
        self.assertEqual(ids, [1, 2])
        subsystems = [res.subsystem for res in result_mult]
        self.assertEqual(subsystems, ['librarian', 'rtp'])

        result2 = self.test_session.get_subsystem_error(starttime=self.subsystem_error_columns['time']
                                                        - TimeDelta(2, format='sec'),
                                                        subsystem='rtp')[0]

        self.assertFalse(result2.isclose(expected))

    def test_errors_subsystem_error(self):
        self.assertRaises(ValueError, self.test_session.add_subsystem_error,
                          'foo', self.subsystem_error_values[2],
                          *self.subsystem_error_values[4:])

        self.test_session.add_subsystem_error(self.subsystem_error_values[1],
                                              self.subsystem_error_values[2],
                                              *self.subsystem_error_values[4:])
        self.assertRaises(ValueError, self.test_session.get_subsystem_error,
                          starttime='foo')
        self.assertRaises(ValueError, self.test_session.get_subsystem_error,
                          starttime=self.subsystem_error_columns['time'], stoptime='foo')
