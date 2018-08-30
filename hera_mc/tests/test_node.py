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

node_example_list = [nodeID for nodeID in range(1, 4)]

node_sensor_example_dict = {
    '1': {'temp_top': 30., 'temp_mid': 31.98, 'temp_bot': 41,
          'temp_humid': 33.89, 'humid': 32.5,
          'timestamp': Time(1512770942.726777, format='unix').to_datetime()},
    '2': {'temp_top': None, 'temp_mid': None, 'temp_bot': None,
          'temp_humid': 33, 'humid': 40.,
          'timestamp': Time(1512770942.995268, format='unix').to_datetime()},
    '3': {'temp_top': 29.1, 'temp_mid': 33.8, 'temp_bot': 41.6,
          'temp_humid': None, 'humid': None,
          'timestamp': Time(1512770942.861526, format='unix').to_datetime()}
}

node_power_example_dict = {
    '1': {'power_snap_relay': True, 'power_snap_0': False, 'power_snap_1': True,
          'power_snap_2': False, 'power_snap_3': False, 'power_pam': True, 'power_fem': True,
          'timestamp': Time(1512770942.726777, format='unix').to_datetime()},
    '2': {'power_snap_relay': False, 'power_snap_0': True, 'power_snap_1': False,
          'power_snap_2': True, 'power_snap_3': True, 'power_pam': False, 'power_fem': False,
          'timestamp': Time(1512770942.995268, format='unix').to_datetime()},
    '3': {'power_snap_relay': False, 'power_snap_0': False, 'power_snap_1': False,
          'power_snap_2': False, 'power_snap_3': False, 'power_pam': False, 'power_fem': False,
          'timestamp': Time(1512770942.861526, format='unix').to_datetime()}
}


class TestNodeSensor(TestHERAMC):

    def test_add_node_sensor_readings(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        top_sensor_temp = node_sensor_example_dict['1']['temp_top']
        middle_sensor_temp = node_sensor_example_dict['1']['temp_mid']
        bottom_sensor_temp = node_sensor_example_dict['1']['temp_bot']
        humidity_sensor_temp = node_sensor_example_dict['1']['temp_humid']
        humidity = node_sensor_example_dict['1']['humid']
        self.test_session.add_node_sensor_readings(t1, 1, top_sensor_temp,
                                                   middle_sensor_temp,
                                                   bottom_sensor_temp,
                                                   humidity_sensor_temp,
                                                   humidity)

        expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                                   top_sensor_temp=30., middle_sensor_temp=31.98,
                                   bottom_sensor_temp=41., humidity_sensor_temp=33.89,
                                   humidity=32.5)
        result = self.test_session.get_node_sensor_readings(t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        top_sensor_temp = node_sensor_example_dict['2']['temp_top']
        middle_sensor_temp = node_sensor_example_dict['2']['temp_mid']
        bottom_sensor_temp = node_sensor_example_dict['2']['temp_bot']
        humidity_sensor_temp = node_sensor_example_dict['2']['temp_humid']
        humidity = node_sensor_example_dict['2']['humid']
        self.test_session.add_node_sensor_readings(t1, 2, top_sensor_temp,
                                                   middle_sensor_temp,
                                                   bottom_sensor_temp,
                                                   humidity_sensor_temp,
                                                   humidity)

        result = self.test_session.get_node_sensor_readings(t1 - TimeDelta(3.0, format='sec'),
                                                            node=1)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_sensor_readings(t1 - TimeDelta(3.0, format='sec'),
                                                            stoptime=t1)
        self.assertEqual(len(result), 2)

        result = self.test_session.get_node_sensor_readings(t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_create_sensor_readings(self):
        sensor_obj_list = node.create_sensor_readings(node_list=node_example_list,
                                                      sensor_dict=node_sensor_example_dict)

        for obj in sensor_obj_list:
            self.test_session.add(obj)

        t1 = Time(1512770942.726777, format='unix')
        result = self.test_session.get_node_sensor_readings(t1 - TimeDelta(3.0, format='sec'),
                                                            node=1)

        expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                                   top_sensor_temp=30., middle_sensor_temp=31.98,
                                   bottom_sensor_temp=41., humidity_sensor_temp=33.89,
                                   humidity=32.5)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_sensor_readings(t1 - TimeDelta(3.0, format='sec'),
                                                            stoptime=t1 + TimeDelta(5.0, format='sec'))
        self.assertEqual(len(result), 3)

    def test_add_node_sensor_readings_from_nodecontrol(self):

        if is_onsite():
            node_list = node._get_node_list()

            self.test_session.add_node_sensor_readings_from_nodecontrol()
            result = self.test_session.get_node_sensor_readings(
                Time.now() - TimeDelta(120.0, format='sec'),
                stoptime=Time.now() + TimeDelta(120.0, format='sec'))
            self.assertEqual(len(result), len(node_list))


class TestNodePowerStatus(TestHERAMC):

    def test_add_node_power_status(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        snap_relay_powered = node_power_example_dict['1']['power_snap_relay']
        snap0_powered = node_power_example_dict['1']['power_snap_0']
        snap1_powered = node_power_example_dict['1']['power_snap_1']
        snap2_powered = node_power_example_dict['1']['power_snap_2']
        snap3_powered = node_power_example_dict['1']['power_snap_3']
        pam_powered = node_power_example_dict['1']['power_pam']
        fem_powered = node_power_example_dict['1']['power_fem']
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

        snap_relay_powered = node_power_example_dict['1']['power_snap_relay']
        snap0_powered = node_power_example_dict['1']['power_snap_0']
        snap1_powered = node_power_example_dict['1']['power_snap_1']
        snap2_powered = node_power_example_dict['1']['power_snap_2']
        snap3_powered = node_power_example_dict['1']['power_snap_3']
        pam_powered = node_power_example_dict['1']['power_pam']
        fem_powered = node_power_example_dict['1']['power_fem']
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

    def test_create_power_status(self):
        sensor_obj_list = node.create_power_status(node_list=node_example_list,
                                                   power_dict=node_power_example_dict)

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
            node_list = node._get_node_list()

            self.test_session.add_node_power_status_from_nodecontrol()
            result = self.test_session.get_node_power_status(Time.now() - TimeDelta(120.0, format='sec'),
                                                             stoptime=Time.now() + TimeDelta(120.0, format='sec'))
            self.assertEqual(len(result), len(node_list))


class TestNodePowerCommand(TestHERAMC):

    def test_node_power_command(self):
        command_list = self.test_session.node_power_command(1, 'fem', 'on',
                                                            dryrun=True, testing=True)
        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)

        expected = node.NodePowerCommand(time=command_time, node=1,
                                         part='fem', command='on')
        self.assertTrue(command_list[0].isclose(expected))

        command_list = self.test_session.node_power_command(1, 'all', 'on',
                                                            dryrun=True, testing=True)
        command_times = [cmd.time for cmd in command_list]
        part_list = list(node.power_command_part_dict.keys())
        part_list.remove('snap_relay')
        part_list.insert(0, 'snap_relay')
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='on')
            self.assertTrue(command_list[pi].isclose(expected))

        command_list = self.test_session.node_power_command(1, 'all', 'off',
                                                            dryrun=True, testing=True)
        command_times = [cmd.time for cmd in command_list]
        part_list = list(node.power_command_part_dict.keys())
        part_list.remove('snap_relay')
        part_list.append('snap_relay')
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='off')
            self.assertTrue(command_list[pi].isclose(expected))

        command_list = self.test_session.node_power_command(1, 'snap0', 'on',
                                                            dryrun=True, testing=True)
        self.assertEqual(len(command_list), 2)
        command_times = [cmd.time for cmd in command_list]
        part_list = ['snap_relay', 'snap0']
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='on')
            self.assertTrue(command_list[pi].isclose(expected))

        command_list = self.test_session.node_power_command(1, 'snap0', 'off',
                                                            dryrun=True, testing=True)
        self.assertEqual(len(command_list), 1)
        command_time = command_list[0].time
        expected = node.NodePowerCommand(time=command_time, node=1,
                                         part='snap0', command='off')
        self.assertTrue(command_list[0].isclose(expected))

        self.assertRaises(ValueError, self.test_session.node_power_command,
                          31, 'fem', 'on', dryrun=True, testing=True)
        self.assertRaises(ValueError, self.test_session.node_power_command,
                          1, 'foo', 'on', dryrun=True, testing=True)
        self.assertRaises(ValueError, self.test_session.node_power_command,
                          1, 'fem', 'foo', dryrun=True, testing=True)
        self.assertRaises(ValueError, node.NodePowerCommand.create,
                          command_time, 1, 'fem', 'on')


if __name__ == '__main__':
    unittest.main()
