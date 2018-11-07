# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.node`.

"""
from __future__ import absolute_import, division, print_function

import os
import unittest
import nose.tools as nt
from math import floor
from astropy.time import Time, TimeDelta

from .. import mc, node
from ..tests import TestHERAMC, is_onsite
from hera_mc.data import DATA_PATH

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
        result = self.test_session.get_node_sensor_readings(starttime=t1 - TimeDelta(3.0, format='sec'))
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

        result = self.test_session.get_node_sensor_readings(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                            nodeID=1)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_sensor_readings(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                            stoptime=t1)
        self.assertEqual(len(result), 2)

        result_most_recent = self.test_session.get_node_sensor_readings()
        self.assertEqual(len(result), 2)
        self.assertEqual(result_most_recent, result)

        filename = os.path.join(DATA_PATH, 'test_node_sensor_file.csv')
        self.test_session.get_node_sensor_readings(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                   stoptime=t1, write_to_file=True,
                                                   filename=filename)
        os.remove(filename)

        self.test_session.get_node_sensor_readings(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                   stoptime=t1, write_to_file=True)
        default_filename = 'node_sensor.csv'
        os.remove(default_filename)

        result = self.test_session.get_node_sensor_readings(starttime=t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_create_sensor_readings(self):
        sensor_obj_list = node.create_sensor_readings(node_list=node_example_list,
                                                      sensor_dict=node_sensor_example_dict)

        for obj in sensor_obj_list:
            self.test_session.add(obj)

        t1 = Time(1512770942.726777, format='unix')
        result = self.test_session.get_node_sensor_readings(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                            nodeID=1)

        expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                                   top_sensor_temp=30., middle_sensor_temp=31.98,
                                   bottom_sensor_temp=41., humidity_sensor_temp=33.89,
                                   humidity=32.5)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_sensor_readings(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                            stoptime=t1 + TimeDelta(5.0, format='sec'))
        self.assertEqual(len(result), 3)

        result_most_recent = self.test_session.get_node_sensor_readings(most_recent=True)
        self.assertEqual(result_most_recent, result)

    def test_sensor_reading_errors(self):
        top_sensor_temp = node_sensor_example_dict['1']['temp_top']
        middle_sensor_temp = node_sensor_example_dict['1']['temp_mid']
        bottom_sensor_temp = node_sensor_example_dict['1']['temp_bot']
        humidity_sensor_temp = node_sensor_example_dict['1']['temp_humid']
        humidity = node_sensor_example_dict['1']['humid']
        self.assertRaises(ValueError, self.test_session.add_node_sensor_readings,
                          'foo', 1, top_sensor_temp, middle_sensor_temp,
                          bottom_sensor_temp, humidity_sensor_temp, humidity)

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_add_node_sensor_readings_from_nodecontrol(self):

        node_list = node.get_node_list()

        self.test_session.add_node_sensor_readings_from_nodecontrol()
        result = self.test_session.get_node_sensor_readings(
            starttime=Time.now() - TimeDelta(120.0, format='sec'),
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
        result = self.test_session.get_node_power_status(starttime=t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        snap_relay_powered = node_power_example_dict['2']['power_snap_relay']
        snap0_powered = node_power_example_dict['2']['power_snap_0']
        snap1_powered = node_power_example_dict['2']['power_snap_1']
        snap2_powered = node_power_example_dict['2']['power_snap_2']
        snap3_powered = node_power_example_dict['2']['power_snap_3']
        pam_powered = node_power_example_dict['2']['power_pam']
        fem_powered = node_power_example_dict['2']['power_fem']
        self.test_session.add_node_power_status(t1, 2, snap_relay_powered,
                                                snap0_powered, snap1_powered,
                                                snap2_powered, snap3_powered,
                                                fem_powered, pam_powered)

        result = self.test_session.get_node_power_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                         nodeID=1)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_power_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                         stoptime=t1)
        self.assertEqual(len(result), 2)

        result_most_recent = self.test_session.get_node_power_status()
        self.assertEqual(len(result_most_recent), 2)
        self.assertEqual(result_most_recent, result)

        result = self.test_session.get_node_power_status(starttime=t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_create_power_status(self):
        sensor_obj_list = node.create_power_status(node_list=node_example_list,
                                                   power_dict=node_power_example_dict)

        for obj in sensor_obj_list:
            self.test_session.add(obj)

        t1 = Time(1512770942.726777, format='unix')
        result = self.test_session.get_node_power_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                         nodeID=1)

        expected = node.NodePowerStatus(time=int(floor(t1.gps)), node=1,
                                        snap_relay_powered=True, snap0_powered=False,
                                        snap1_powered=True, snap2_powered=False,
                                        snap3_powered=False, pam_powered=True,
                                        fem_powered=True)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_node_power_status(starttime=t1 - TimeDelta(3.0, format='sec'),
                                                         stoptime=t1 + TimeDelta(5.0, format='sec'))
        self.assertEqual(len(result), 3)

        result_most_recent = self.test_session.get_node_power_status()
        self.assertEqual(result_most_recent, result)

    def test_node_power_status_errors(self):
        snap_relay_powered = node_power_example_dict['1']['power_snap_relay']
        snap0_powered = node_power_example_dict['1']['power_snap_0']
        snap1_powered = node_power_example_dict['1']['power_snap_1']
        snap2_powered = node_power_example_dict['1']['power_snap_2']
        snap3_powered = node_power_example_dict['1']['power_snap_3']
        pam_powered = node_power_example_dict['1']['power_pam']
        fem_powered = node_power_example_dict['1']['power_fem']
        self.assertRaises(ValueError, self.test_session.add_node_power_status,
                          'foo', 1, snap_relay_powered, snap0_powered, snap1_powered,
                          snap2_powered, snap3_powered, fem_powered, pam_powered)

    @unittest.skipIf(not is_onsite(), 'This test only works on site')
    def test_add_node_power_status_from_nodecontrol(self):

        node_list = node.get_node_list()

        self.test_session.add_node_power_status_from_nodecontrol()
        result = self.test_session.get_node_power_status(starttime=Time.now() - TimeDelta(120.0, format='sec'),
                                                         stoptime=Time.now() + TimeDelta(120.0, format='sec'))
        self.assertEqual(len(result), len(node_list))


class TestNodePowerCommand(TestHERAMC):

    def test_node_power_command(self):
        # test things on & off with no recent status
        command_list = self.test_session.node_power_command(1, 'fem', 'on',
                                                            testing=True)
        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)
        expected = node.NodePowerCommand(time=command_time, node=1,
                                         part='fem', command='on')
        self.assertTrue(command_list[0].isclose(expected))

        # test list with duplicates
        command_list = self.test_session.node_power_command(1, ['fem', 'fem'], 'on',
                                                            testing=True)
        command_time = command_list[0].time
        self.assertTrue(Time.now().gps - command_time < 2.)
        expected = node.NodePowerCommand(time=command_time, node=1,
                                         part='fem', command='on')
        self.assertTrue(command_list[0].isclose(expected))

        # test turning on all
        command_list = self.test_session.node_power_command(1, 'all', 'on',
                                                            testing=True)
        command_times = [cmd.time for cmd in command_list]
        part_list = list(node.power_command_part_dict.keys())
        part_list.remove('snap_relay')
        part_list.insert(0, 'snap_relay')
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='on')
            self.assertTrue(command_list[pi].isclose(expected))

        # test adding the commands to the database and retrieving them
        for cmd in command_list:
            self.test_session.add(cmd)
        result_list = self.test_session.get_node_power_command(
            starttime=Time.now() - TimeDelta(10, format='sec'),
            stoptime=Time.now() + TimeDelta(10, format='sec'))
        self.assertEqual(len(command_list), len(result_list))
        result_parts = [cmd.part for cmd in result_list]
        for pi, part in enumerate(part_list):
            index = result_parts.index(part)
            self.assertTrue(command_list[pi].isclose(result_list[index]))

        # test turning off all
        command_list = self.test_session.node_power_command(1, 'all', 'off',
                                                            testing=True)
        command_times = [cmd.time for cmd in command_list]
        part_list = list(node.power_command_part_dict.keys())
        part_list.remove('snap_relay')
        part_list.append('snap_relay')
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='off')
            self.assertTrue(command_list[pi].isclose(expected))

        # test that turning a snap on also turns on the relay
        command_list = self.test_session.node_power_command(1, 'snap0', 'on',
                                                            testing=True)
        self.assertEqual(len(command_list), 2)
        command_times = [cmd.time for cmd in command_list]
        part_list = ['snap_relay', 'snap0']
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='on')
            self.assertTrue(command_list[pi].isclose(expected))

        # test that turning off snap_relay also turns off snaps
        command_list = self.test_session.node_power_command(1, 'snap_relay', 'off',
                                                            testing=True)
        self.assertEqual(len(command_list), 5)
        command_times = [cmd.time for cmd in command_list]
        part_list = []
        for partname in reversed(list(node.power_command_part_dict.keys())):
            if partname.startswith('snap') and partname is not 'snap_relay':
                part_list.append(partname)
        part_list.append('snap_relay')
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='off')
            self.assertTrue(command_list[pi].isclose(expected))

        # test erroneous part name
        self.assertRaises(ValueError, self.test_session.node_power_command,
                          1, 'foo', 'on', testing=True)

        # Now test with recent statuses
        # test that turning a snap on also turns on the relay (with recent status of off)
        t1 = Time.now() - TimeDelta(30, format='sec')
        self.test_session.add_node_power_status(t1, 1, False, False, False,
                                                False, False, False, False)
        command_list = self.test_session.node_power_command(1, 'snap0', 'on',
                                                            testing=True)
        self.assertEqual(len(command_list), 2)
        command_times = [cmd.time for cmd in command_list]
        part_list = ['snap_relay', 'snap0']
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='on')
            self.assertTrue(command_list[pi].isclose(expected))

        # test that turning a snap doesn't add relay (with recent status of on)
        t1 = Time.now() - TimeDelta(20, format='sec')
        self.test_session.add_node_power_status(t1, 1, True, False, False,
                                                False, False, False, False)
        command_list = self.test_session.node_power_command(1, 'snap0', 'on',
                                                            testing=True)
        self.assertEqual(len(command_list), 1)
        command_time = command_list[0].time
        expected = node.NodePowerCommand(time=command_time, node=1,
                                         part='snap0', command='on')
        self.assertTrue(command_list[0].isclose(expected))

        # test that turning off snap_relay also turns off snaps that are on
        t1 = Time.now() - TimeDelta(10, format='sec')
        self.test_session.add_node_power_status(t1, 1, True, True, True,
                                                False, False, False, False)
        command_list = self.test_session.node_power_command(1, 'snap_relay', 'off',
                                                            testing=True)
        self.assertEqual(len(command_list), 3)
        command_times = [cmd.time for cmd in command_list]
        part_list = []
        for partname in reversed(list(node.power_command_part_dict.keys())):
            if partname == 'snap0' or partname == 'snap1':
                part_list.append(partname)
        part_list.append('snap_relay')
        for pi, part in enumerate(part_list):
            expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                             part=part, command='off')
            self.assertTrue(command_list[pi].isclose(expected))

        # test turning off snap that is on
        command_list = self.test_session.node_power_command(1, 'snap0', 'off',
                                                            testing=True)
        self.assertEqual(len(command_list), 1)
        command_time = command_list[0].time
        expected = node.NodePowerCommand(time=command_time, node=1,
                                         part='snap0', command='off')
        self.assertTrue(command_list[0].isclose(expected))

        # test turning off fem that is off
        command_list = self.test_session.node_power_command(1, 'fem', 'off',
                                                            testing=True)
        self.assertEqual(len(command_list), 0)

        # test erroneous part name with a recent status
        self.assertRaises(ValueError, self.test_session.node_power_command,
                          1, 'foo', 'on', testing=True)

        # test various errors
        self.assertRaises(ValueError, self.test_session.node_power_command,
                          31, 'fem', 'on', testing=True)
        self.assertRaises(ValueError, self.test_session.node_power_command,
                          2, 'fem', 'foo', testing=True)
        self.assertRaises(ValueError, node.NodePowerCommand.create,
                          command_time, 1, 'fem', 'on')


if __name__ == '__main__':
    unittest.main()
