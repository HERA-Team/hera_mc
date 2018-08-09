# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.node`.

"""
from __future__ import absolute_import, division, print_function

import unittest
import nose.tools as nt
from math import floor
from astropy.time import Time, TimeDelta

from .. import mc, node
from ..tests import TestHERAMC, is_onsite


node_sensor_example_dict = {
    '1': {'temp_top': '30', 'temp_mid': '31.98', 'temp_bot': '41',
          'temp_humid': '33.89', 'humid': '32.5', 'timestamp': '1512770942.726777'},
    '2': {'temp_top': '32', 'temp_mid': '32', 'temp_bot': '39.2',
          'temp_humid': '33', 'humid': '40', 'timestamp': '1512770942.995268'},
    '3': {'temp_top': '29.1', 'temp_mid': '33.8', 'temp_bot': '41.6',
          'temp_humid': '34', 'humid': '25.8', 'timestamp': '1512770942.861526'}
}

node_power_example_dict = {
    '1': {'power_snap_relay': '1', 'power_snap_0': '0', 'power_snap_1': '1',
          'power_snap_2': '0', 'power_snap_3': '0', 'power_pam': '1', 'power_fem': '1',
          'timestamp': '1512770942.726777'},
    '2': {'power_snap_relay': '0', 'power_snap_0': '1', 'power_snap_1': '0',
          'power_snap_2': '1', 'power_snap_3': '1', 'power_pam': '0', 'power_fem': '0',
          'timestamp': '1512770942.995268'},
    '3': {'power_snap_relay': '0', 'power_snap_0': '0', 'power_snap_1': '0',
          'power_snap_2': '0', 'power_snap_3': '0', 'power_pam': '0', 'power_fem': '0',
          'timestamp': '1512770942.861526'}
}


class TestNodeSensor(TestHERAMC):

    def test_add_node_sensor(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        top_sensor_temp = float(node_sensor_example_dict['1']['temp_top'])
        middle_sensor_temp = float(node_sensor_example_dict['1']['temp_mid'])
        bottom_sensor_temp = float(node_sensor_example_dict['1']['temp_bot'])
        humidity_sensor_temp = float(node_sensor_example_dict['1']['temp_humid'])
        humidity = float(node_sensor_example_dict['1']['humid'])
        self.test_session.add_node_sensor(t1, 1, top_sensor_temp, middle_sensor_temp,
                                          bottom_sensor_temp, humidity_sensor_temp,
                                          humidity)

        expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                                   top_sensor_temp=30., middle_sensor_temp=31.98,
                                   bottom_sensor_temp=41., humidity_sensor_temp=33.89,
                                   humidity=32.5)
        result = self.test_session.get_node_sensor(t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        top_sensor_temp = float(node_sensor_example_dict['2']['temp_top'])
        middle_sensor_temp = float(node_sensor_example_dict['2']['temp_mid'])
        bottom_sensor_temp = float(node_sensor_example_dict['2']['temp_bot'])
        humidity_sensor_temp = float(node_sensor_example_dict['2']['temp_humid'])
        humidity = float(node_sensor_example_dict['2']['humid'])
        self.test_session.add_node_sensor(t1, 2, top_sensor_temp, middle_sensor_temp,
                                          bottom_sensor_temp, humidity_sensor_temp,
                                          humidity)

        result = self.test_session.get_node_sensor(t1 - TimeDelta(3.0, format='sec'),
                                                   node=1)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_sensor(t1 - TimeDelta(3.0, format='sec'),
                                                   stoptime=t1)
        self.assertEqual(len(result), 2)

        result = self.test_session.get_node_sensor(t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_create_sensor(self):
        sensor_obj_list = node.create_sensor(node_sensor_example_dict)

        for obj in sensor_obj_list:
            self.test_session.add(obj)

        t1 = Time(1512770942.726777, format='unix')
        result = self.test_session.get_node_sensor(t1 - TimeDelta(3.0, format='sec'),
                                                   node=1)

        expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                                   top_sensor_temp=30., middle_sensor_temp=31.98,
                                   bottom_sensor_temp=41., humidity_sensor_temp=33.89,
                                   humidity=32.5)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_sensor(t1 - TimeDelta(3.0, format='sec'),
                                                   stoptime=t1 + TimeDelta(5.0, format='sec'))
        self.assertEqual(len(result), 3)

    def test_add_node_sensor_from_nodecontrol(self):

        if is_onsite():
            self.test_session.add_node_sensor_from_nodecontrol()
            result = self.test_session.get_node_sensor(Time.now() - TimeDelta(120.0, format='sec'),
                                                       stoptime=Time.now() + TimeDelta(120.0, format='sec'))
            self.assertEqual(len(result), 30)


class TestNodePowerStatus(TestHERAMC):

    def test_add_node_power_status(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        snap_relay_powered = bool(int(node_power_example_dict['1']['power_snap_relay']))
        snap0_powered = bool(int(node_power_example_dict['1']['power_snap_0']))
        snap1_powered = bool(int(node_power_example_dict['1']['power_snap_1']))
        snap2_powered = bool(int(node_power_example_dict['1']['power_snap_2']))
        snap3_powered = bool(int(node_power_example_dict['1']['power_snap_3']))
        pam_powered = bool(int(node_power_example_dict['1']['power_pam']))
        fem_powered = bool(int(node_power_example_dict['1']['power_fem']))
        self.test_session.add_node_power_status(t1, 1, snap_relay_powered,
                                                snap0_powered, snap1_powered,
                                                snap2_powered, snap3_powered,
                                                fem_powered, pam_powered)

        expected = node.NodePowerStatus(time=int(floor(t1.gps)), node=1,
                                        snap_relay_powered=True, snap0_powered=False,
                                        snap1_powered=True, snap2_powered=False,
                                        snap3_powered=False, pam_powered=True,
                                        fem_powered=True)
        result = self.test_session.get_node_power_status(t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        snap_relay_powered = bool(int(node_power_example_dict['1']['power_snap_relay']))
        snap0_powered = bool(int(node_power_example_dict['1']['power_snap_0']))
        snap1_powered = bool(int(node_power_example_dict['1']['power_snap_1']))
        snap2_powered = bool(int(node_power_example_dict['1']['power_snap_2']))
        snap3_powered = bool(int(node_power_example_dict['1']['power_snap_3']))
        pam_powered = bool(int(node_power_example_dict['1']['power_pam']))
        fem_powered = bool(int(node_power_example_dict['1']['power_fem']))
        self.test_session.add_node_power_status(t1, 2, snap_relay_powered,
                                                snap0_powered, snap1_powered,
                                                snap2_powered, snap3_powered,
                                                fem_powered, pam_powered)

        result = self.test_session.get_node_power_status(t1 - TimeDelta(3.0, format='sec'),
                                                         node=1)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_power_status(t1 - TimeDelta(3.0, format='sec'),
                                                         stoptime=t1)
        self.assertEqual(len(result), 2)

        result = self.test_session.get_node_power_status(t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_create_sensor(self):
        sensor_obj_list = node.create_power_status(node_power_example_dict)

        for obj in sensor_obj_list:
            self.test_session.add(obj)

        t1 = Time(1512770942.726777, format='unix')
        result = self.test_session.get_node_power_status(t1 - TimeDelta(3.0, format='sec'),
                                                         node=1)

        expected = node.NodePowerStatus(time=int(floor(t1.gps)), node=1,
                                        snap_relay_powered=True, snap0_powered=False,
                                        snap1_powered=True, snap2_powered=False,
                                        snap3_powered=False, pam_powered=True,
                                        fem_powered=True)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_power_status(t1 - TimeDelta(3.0, format='sec'),
                                                         stoptime=t1 + TimeDelta(5.0, format='sec'))
        self.assertEqual(len(result), 3)

    def test_add_node_power_status_from_nodecontrol(self):

        if is_onsite():
            self.test_session.add_node_power_status_from_nodecontrol()
            result = self.test_session.get_node_power_status(Time.now() - TimeDelta(120.0, format='sec'),
                                                             stoptime=Time.now() + TimeDelta(120.0, format='sec'))
            self.assertEqual(len(result), 30)


if __name__ == '__main__':
    unittest.main()
