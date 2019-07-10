# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.daemon_status`.

"""
from __future__ import absolute_import, division, print_function

import unittest
from math import floor
import numpy as np
from astropy.time import Time, TimeDelta

from .. import mc
from ..daemon_status import DaemonStatus
from ..tests import TestHERAMC


class TestDaemonStatus(TestHERAMC):

    def setUp(self):
        super(TestDaemonStatus, self).setUp()

        self.column_names = ['name', 'hostname', 'time', 'status']
        self.column_values = ['test_daemon', 'test_host', Time.now(), 'good']
        self.columns = dict(zip(self.column_names, self.column_values))

    def test_add_daemon_status(self):
        exp_columns = self.columns.copy()
        exp_columns['jd'] = int(floor(exp_columns['time'].jd))
        exp_columns['time'] = int(floor(exp_columns['time'].gps))

        expected = DaemonStatus(**exp_columns)

        result = self.test_session.add_daemon_status(*self.column_values, testing=True)
        self.assertTrue(result.isclose(expected))

        self.test_session.add_daemon_status(*self.column_values)
        result = self.test_session.get_daemon_status(starttime=self.columns['time']
                                                     - TimeDelta(2, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]

        self.assertTrue(result.isclose(expected))

        # update the existing record to a new time & status
        expected.time = int(floor(Time.now().gps))
        expected.status = 'errored'

        # have to commit to get the updates to work
        self.test_session.commit()
        self.test_session.add_daemon_status(*self.column_values[0:2],
                                            Time.now(), 'errored')
        self.test_session.commit()
        result = self.test_session.get_daemon_status(starttime=self.columns['time']
                                                     - TimeDelta(2, format='sec'))

        self.assertEqual(len(result), 1)
        result = result[0]

        self.assertTrue(result.isclose(expected))

        self.test_session.add_daemon_status('test_daemon2', *self.column_values[1:])
        result_host = self.test_session.get_daemon_status(starttime=self.columns['time']
                                                          - TimeDelta(2, format='sec'),
                                                          daemon_name=self.columns['name'],
                                                          stoptime=self.columns['time']
                                                          + TimeDelta(2 * 60, format='sec'))
        self.assertEqual(len(result_host), 1)
        result_host = result_host[0]
        self.assertTrue(result_host.isclose(expected))

        result_mult = self.test_session.get_daemon_status(starttime=self.columns['time']
                                                          - TimeDelta(2, format='sec'),
                                                          stoptime=self.columns['time']
                                                          + TimeDelta(2 * 60, format='sec'))

        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_daemon_status(starttime=self.columns['time']
                                                      - TimeDelta(2, format='sec'),
                                                      daemon_name='test_daemon2')[0]

        self.assertFalse(result2.isclose(expected))

    def test_errors_daemon_status(self):
        self.assertRaises(ValueError, self.test_session.add_daemon_status,
                          self.column_values[0], self.column_values[1],
                          'foo', self.column_values[3])

        self.assertRaises(ValueError, self.test_session.add_daemon_status,
                          *self.column_values[0:3], 'foo')

        self.test_session.add_daemon_status(*self.column_values)
        self.assertRaises(ValueError, self.test_session.get_daemon_status,
                          starttime='test_host')
        self.assertRaises(ValueError, self.test_session.get_daemon_status,
                          starttime=self.columns['time'],
                          stoptime='test_host')


if __name__ == '__main__':
    unittest.main()
