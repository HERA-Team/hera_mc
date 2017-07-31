# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.qm`.

"""
import unittest

import numpy as np
from math import floor
from astropy.time import Time, TimeDelta

from hera_mc import mc, cm_transfer
from hera_mc.qm import ant_metrics, array_metrics, metric_list
from hera_mc import utils
from hera_mc.tests import TestHERAMC


class TestQM(TestHERAMC):

    def setUp(self):
        super(TestQM, self).setUp()
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')
        self.obsid = utils.calculate_obsid(t1)
        # Create obs to satifsy foreign key constraints
        self.test_session.add_obs(t1, t2, self.obsid)
        # Same for metric description
        self.test_session.add_metric_desc('test', 'Test metric')
        self.test_session.commit()

    def test_ant_metrics(self):
        self.test_session.add_ant_metric(self.obsid, 0, 'x', 'test', 4.5)
        r = self.test_session.get_ant_metric()
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].antpol, (0, 'x'))
        self.assertEqual(r[0].metric, 'test')
        self.assertEqual(r[0].val, 4.5)

        # Test exceptions
        self.assertRaises(ValueError, self.test_session.add_ant_metric, 'obs',
                          0, 'x', 'test', 4.5)
        self.assertRaises(ValueError, self.test_session.add_ant_metric, self.obsid,
                          '0', 'x', 'test', 4.5)
        self.assertRaises(ValueError, self.test_session.add_ant_metric, self.obsid,
                          0, 'N', 'test', 4.5)
        self.assertRaises(ValueError, self.test_session.add_ant_metric, self.obsid,
                          0, -1, 'test', 4.5)
        self.assertRaises(ValueError, self.test_session.add_ant_metric, self.obsid,
                          0, 'x', 4, 4.5)
        self.assertRaises(ValueError, self.test_session.add_ant_metric, self.obsid,
                          0, 'x', 'test', 'value')
        self.assertRaises(ValueError, ant_metrics.create, self.obsid, 0, 'x',
                          'test', self.obsid, 4.5)

    def test_array_metrics(self):
        self.test_session.add_array_metric(self.obsid, 'test', 6.2)
        r = self.test_session.get_array_metric()
        self.assertEqual(r[0].metric, 'test')
        self.assertEqual(r[0].val, 6.2)

        # Test exceptions
        self.assertRaises(ValueError, self.test_session.add_array_metric, 'obs',
                          'test', 4.5)
        self.assertRaises(ValueError, self.test_session.add_array_metric, self.obsid,
                          4, 4.5)
        self.assertRaises(ValueError, self.test_session.add_array_metric, self.obsid,
                          'test', 'value')
        self.assertRaises(ValueError, array_metrics.create, self.obsid,
                          'test', self.obsid, 4.5)

    def test_metric_list(self):
        self.test_session.add_metric_desc('test2', 'Second test')
        r = self.test_session.get_metric_desc(metric='test2')
        self.assertEqual(r[0].metric, 'test2')
        self.assertEqual(r[0].desc, 'Second test')

        # Test exceptions
        self.assertRaises(ValueError, self.test_session.add_metric_desc,
                          4, 'desc')
        self.assertRaises(ValueError, self.test_session.add_metric_desc,
                          'test2', 5)

if __name__ == '__main__':
    unittest.main()
