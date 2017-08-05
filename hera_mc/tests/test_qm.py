# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.qm`.

"""
import unittest

import numpy as np
from math import floor
from astropy.time import Time, TimeDelta
import os

from hera_mc import mc, cm_transfer
from hera_mc.qm import ant_metrics, array_metrics, metric_list
from hera_mc import utils, geo_location
from hera_mc.tests import TestHERAMC, checkWarnings


class TestQM(TestHERAMC):

    def setUp(self):
        super(TestQM, self).setUp()
        stn = 'cofa'
        prefix = 'COFA'
        st = geo_location.StationType()
        st.station_type_name = stn
        st.prefix = prefix
        self.test_session.add(st)
        self.test_session.commit()
        gl = geo_location.GeoLocation()
        gl.station_name = prefix + '_null'
        gl.station_type_name = stn
        gl.datum = 'WGS84'
        gl.tile = '34J'
        gl.northing = 6601181.0
        gl.easting = 541007.0
        gl.elevation = 1051.69
        gl.created_gpstime = 1172530000
        self.test_session.add(gl)
        self.test_session.commit()

    def test_ant_metrics(self):
        # Initialize
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')
        self.obsid = utils.calculate_obsid(t1)
        # Create obs to satifsy foreign key constraints
        self.test_session.add_obs(t1, t2, self.obsid)
        self.test_session.add_obs(t1 - TimeDelta(10.0, format='sec'), t2,
                                  self.obsid - 10)
        self.test_session.add_obs(t1 + TimeDelta(10.0, format='sec'), t2,
                                  self.obsid + 10)
        # Same for metric description
        self.test_session.add_metric_desc('test', 'Test metric')
        self.test_session.commit()

        # now the tests
        self.test_session.add_ant_metric(self.obsid, 0, 'x', 'test', 4.5)
        r = self.test_session.get_ant_metric(metric='test')
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].antpol, (0, 'x'))
        self.assertEqual(r[0].metric, 'test')
        self.assertEqual(r[0].val, 4.5)

        # Test more exciting queries
        self.test_session.add_ant_metric(self.obsid, 0, 'y', 'test', 2.5)
        self.test_session.add_ant_metric(self.obsid, 3, 'x', 'test', 2.5)
        self.test_session.add_ant_metric(self.obsid, 3, 'y', 'test', 2.5)
        r = self.test_session.get_ant_metric()
        self.assertEqual(len(r), 4)
        r = self.test_session.get_ant_metric(ant=0)
        self.assertEqual(len(r), 2)
        for ri in r:
            self.assertEqual(ri.ant, 0)
        r = self.test_session.get_ant_metric(pol='x')
        self.assertEqual(len(r), 2)
        for ri in r:
            self.assertEqual(ri.pol, 'x')
        r = self.test_session.get_ant_metric(starttime=self.obsid - 10,
                                             stoptime=self.obsid + 4)
        self.assertEqual(len(r), 4)
        t1 = Time(self.obsid - 10, format='gps')
        t2 = Time(self.obsid + 4, format='gps')
        r = self.test_session.get_ant_metric(starttime=t1, stoptime=t2)
        self.assertEqual(len(r), 4)
        r = self.test_session.get_ant_metric(ant=[0, 3], pol=['x', 'y'])
        self.assertEqual(len(r), 4)

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
        # Initialize
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')
        self.obsid = utils.calculate_obsid(t1)
        # Create obs to satifsy foreign key constraints
        self.test_session.add_obs(t1, t2, self.obsid)
        self.test_session.add_obs(t1 - TimeDelta(10.0, format='sec'), t2,
                                  self.obsid - 10)
        self.test_session.add_obs(t1 + TimeDelta(10.0, format='sec'), t2,
                                  self.obsid + 10)
        # Same for metric description
        self.test_session.add_metric_desc('test', 'Test metric')
        self.test_session.commit()

        # now the tests
        self.test_session.add_array_metric(self.obsid, 'test', 6.2)
        r = self.test_session.get_array_metric()
        self.assertEqual(r[0].metric, 'test')
        self.assertEqual(r[0].val, 6.2)

        # Test more exciting queries
        self.test_session.add_array_metric(self.obsid + 10, 'test', 2.5)
        self.test_session.add_array_metric(self.obsid - 10, 'test', 2.5)
        r = self.test_session.get_array_metric(metric='test')
        self.assertEqual(len(r), 3)
        r = self.test_session.get_array_metric(starttime=self.obsid)
        self.assertEqual(len(r), 2)
        r = self.test_session.get_array_metric(stoptime=self.obsid)
        self.assertEqual(len(r), 2)
        t1 = Time(self.obsid - 20, format='gps')
        t2 = Time(self.obsid + 20, format='gps')
        r = self.test_session.get_array_metric(starttime=t1, stoptime=t2)
        self.assertEqual(len(r), 3)

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
        # Initialize
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')
        self.obsid = utils.calculate_obsid(t1)
        # Create obs to satifsy foreign key constraints
        self.test_session.add_obs(t1, t2, self.obsid)
        self.test_session.add_obs(t1 - TimeDelta(10.0, format='sec'), t2,
                                  self.obsid - 10)
        self.test_session.add_obs(t1 + TimeDelta(10.0, format='sec'), t2,
                                  self.obsid + 10)

        # now the tests
        self.test_session.add_metric_desc('test', 'test desc')
        r = self.test_session.get_metric_desc(metric='test')
        self.assertEqual(r[0].metric, 'test')
        self.assertEqual(r[0].desc, 'test desc')

        self.test_session.update_metric_desc('test', 'new desc')
        r = self.test_session.get_metric_desc(metric='test')
        self.assertEqual(r[0].desc, 'new desc')

        # Test exceptions
        self.assertRaises(ValueError, self.test_session.add_metric_desc,
                          4, 'desc')
        self.assertRaises(ValueError, self.test_session.add_metric_desc,
                          'test', 5)

        # Test check_metric_desc function to auto-fill descriptions
        self.test_session.check_metric_desc('test')
        r = self.test_session.get_metric_desc(metric='test')
        self.assertEqual(r[0].desc, 'new desc')
        checkWarnings(self.test_session.check_metric_desc, ['test2'],
                      message='Metric test2 not found in db')
        r = self.test_session.get_metric_desc(metric='test2')
        self.assertTrue('Auto-generated description.' in r[0].desc)

    def test_add_metrics_file(self):
        # Initialize
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')
        self.obsid = utils.calculate_obsid(t1)
        # Create obs to satifsy foreign key constraints
        self.test_session.add_obs(t1, t2, self.obsid)
        self.test_session.commit()
        filename = os.path.join(mc.test_data_path, 'ant_metrics_output.json')
        filebase = os.path.basename(filename)
        self.assertRaises(ValueError, self.test_session.add_metrics_file,
                          filename, 'ant')
        self.test_session.add_lib_file(filebase, self.obsid, t2, 0.1)
        self.test_session.commit()
        self.test_session.update_qm_list()
        self.test_session.add_metrics_file(filename, 'ant')

if __name__ == '__main__':
    unittest.main()
