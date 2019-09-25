# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.node`."""
from __future__ import absolute_import, division, print_function

import os
from math import floor
import pytest

from astropy.time import Time, TimeDelta

from .. import node
from ..tests import onsite
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
          'power_snap_2': False, 'power_snap_3': False, 'power_pam': True,
          'power_fem': True,
          'timestamp': Time(1512770942.726777, format='unix').to_datetime()},
    '2': {'power_snap_relay': False, 'power_snap_0': True,
          'power_snap_1': False,
          'power_snap_2': True, 'power_snap_3': True, 'power_pam': False,
          'power_fem': False,
          'timestamp': Time(1512770942.995268, format='unix').to_datetime()},
    '3': {'power_snap_relay': False, 'power_snap_0': False,
          'power_snap_1': False,
          'power_snap_2': False, 'power_snap_3': False, 'power_pam': False,
          'power_fem': False,
          'timestamp': Time(1512770942.861526, format='unix').to_datetime()}
}


def test_add_node_sensor_readings(mcsession):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    top_sensor_temp = node_sensor_example_dict['1']['temp_top']
    middle_sensor_temp = node_sensor_example_dict['1']['temp_mid']
    bottom_sensor_temp = node_sensor_example_dict['1']['temp_bot']
    humidity_sensor_temp = node_sensor_example_dict['1']['temp_humid']
    humidity = node_sensor_example_dict['1']['humid']
    test_session.add_node_sensor_readings(t1, 1, top_sensor_temp,
                                          middle_sensor_temp,
                                          bottom_sensor_temp,
                                          humidity_sensor_temp, humidity)

    expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                               top_sensor_temp=30., middle_sensor_temp=31.98,
                               bottom_sensor_temp=41.,
                               humidity_sensor_temp=33.89, humidity=32.5)
    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    top_sensor_temp = node_sensor_example_dict['2']['temp_top']
    middle_sensor_temp = node_sensor_example_dict['2']['temp_mid']
    bottom_sensor_temp = node_sensor_example_dict['2']['temp_bot']
    humidity_sensor_temp = node_sensor_example_dict['2']['temp_humid']
    humidity = node_sensor_example_dict['2']['humid']
    test_session.add_node_sensor_readings(t1, 2, top_sensor_temp,
                                          middle_sensor_temp,
                                          bottom_sensor_temp,
                                          humidity_sensor_temp,
                                          humidity)

    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 2

    result_most_recent = test_session.get_node_sensor_readings()
    assert len(result) == 2
    assert result_most_recent == result

    filename = os.path.join(DATA_PATH, 'test_node_sensor_file.csv')
    test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1,
        write_to_file=True, filename=filename)
    os.remove(filename)

    test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1,
        write_to_file=True)
    default_filename = 'node_sensor.csv'
    os.remove(default_filename)

    result = test_session.get_node_sensor_readings(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_create_sensor_readings(mcsession):
    test_session = mcsession
    sensor_obj_list = node.create_sensor_readings(
        node_list=node_example_list, sensor_dict=node_sensor_example_dict)

    for obj in sensor_obj_list:
        test_session.add(obj)

    t1 = Time(1512770942.726777, format='unix')
    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)

    expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                               top_sensor_temp=30., middle_sensor_temp=31.98,
                               bottom_sensor_temp=41.,
                               humidity_sensor_temp=33.89,
                               humidity=32.5)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        stoptime=t1 + TimeDelta(5.0, format='sec'))
    assert len(result) == 3

    result_most_recent = test_session.get_node_sensor_readings(
        most_recent=True)
    assert result_most_recent == result


def test_sensor_reading_errors(mcsession):
    test_session = mcsession
    top_sensor_temp = node_sensor_example_dict['1']['temp_top']
    middle_sensor_temp = node_sensor_example_dict['1']['temp_mid']
    bottom_sensor_temp = node_sensor_example_dict['1']['temp_bot']
    humidity_sensor_temp = node_sensor_example_dict['1']['temp_humid']
    humidity = node_sensor_example_dict['1']['humid']
    pytest.raises(ValueError, test_session.add_node_sensor_readings,
                  'foo', 1, top_sensor_temp, middle_sensor_temp,
                  bottom_sensor_temp, humidity_sensor_temp, humidity)


@onsite
def test_add_node_sensor_readings_from_nodecontrol(mcsession):
    test_session = mcsession

    node_list = node.get_node_list()

    test_session.add_node_sensor_readings_from_nodecontrol()
    result = test_session.get_node_sensor_readings(
        starttime=Time.now() - TimeDelta(120.0, format='sec'),
        stoptime=Time.now() + TimeDelta(120.0, format='sec'))
    assert len(result) == len(node_list)


def test_add_node_power_status(mcsession):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    snap_relay_powered = node_power_example_dict['1']['power_snap_relay']
    snap0_powered = node_power_example_dict['1']['power_snap_0']
    snap1_powered = node_power_example_dict['1']['power_snap_1']
    snap2_powered = node_power_example_dict['1']['power_snap_2']
    snap3_powered = node_power_example_dict['1']['power_snap_3']
    pam_powered = node_power_example_dict['1']['power_pam']
    fem_powered = node_power_example_dict['1']['power_fem']
    test_session.add_node_power_status(t1, 1, snap_relay_powered,
                                       snap0_powered, snap1_powered,
                                       snap2_powered, snap3_powered,
                                       fem_powered, pam_powered)

    expected = node.NodePowerStatus(time=int(floor(t1.gps)), node=1,
                                    snap_relay_powered=True,
                                    snap0_powered=False,
                                    snap1_powered=True, snap2_powered=False,
                                    snap3_powered=False, pam_powered=True,
                                    fem_powered=True)
    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    snap_relay_powered = node_power_example_dict['2']['power_snap_relay']
    snap0_powered = node_power_example_dict['2']['power_snap_0']
    snap1_powered = node_power_example_dict['2']['power_snap_1']
    snap2_powered = node_power_example_dict['2']['power_snap_2']
    snap3_powered = node_power_example_dict['2']['power_snap_3']
    pam_powered = node_power_example_dict['2']['power_pam']
    fem_powered = node_power_example_dict['2']['power_fem']
    test_session.add_node_power_status(
        t1, 2, snap_relay_powered, snap0_powered, snap1_powered, snap2_powered,
        snap3_powered, fem_powered, pam_powered)

    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 2

    result_most_recent = test_session.get_node_power_status()
    assert len(result_most_recent) == 2
    assert result_most_recent == result

    result = test_session.get_node_power_status(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_create_power_status(mcsession):
    test_session = mcsession
    sensor_obj_list = node.create_power_status(
        node_list=node_example_list, power_dict=node_power_example_dict)

    for obj in sensor_obj_list:
        test_session.add(obj)

    t1 = Time(1512770942.726777, format='unix')
    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)

    expected = node.NodePowerStatus(time=int(floor(t1.gps)), node=1,
                                    snap_relay_powered=True,
                                    snap0_powered=False,
                                    snap1_powered=True, snap2_powered=False,
                                    snap3_powered=False, pam_powered=True,
                                    fem_powered=True)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        stoptime=t1 + TimeDelta(5.0, format='sec'))
    assert len(result) == 3

    result_most_recent = test_session.get_node_power_status()
    assert result_most_recent == result


def test_node_power_status_errors(mcsession):
    test_session = mcsession
    snap_relay_powered = node_power_example_dict['1']['power_snap_relay']
    snap0_powered = node_power_example_dict['1']['power_snap_0']
    snap1_powered = node_power_example_dict['1']['power_snap_1']
    snap2_powered = node_power_example_dict['1']['power_snap_2']
    snap3_powered = node_power_example_dict['1']['power_snap_3']
    pam_powered = node_power_example_dict['1']['power_pam']
    fem_powered = node_power_example_dict['1']['power_fem']
    pytest.raises(ValueError, test_session.add_node_power_status,
                  'foo', 1, snap_relay_powered, snap0_powered, snap1_powered,
                  snap2_powered, snap3_powered, fem_powered, pam_powered)


@onsite
def test_add_node_power_status_from_nodecontrol(mcsession):
    test_session = mcsession

    node_list = node.get_node_list()

    test_session.add_node_power_status_from_nodecontrol()
    result = test_session.get_node_power_status(
        starttime=Time.now() - TimeDelta(120.0, format='sec'),
        stoptime=Time.now() + TimeDelta(120.0, format='sec'))
    assert len(result) == len(node_list)


def test_node_power_command(mcsession):
    test_session = mcsession
    # test things on & off with no recent status
    command_list = test_session.node_power_command(
        1, 'fem', 'on', testing=True)
    command_time = command_list[0].time
    assert Time.now().gps - command_time < 2.
    expected = node.NodePowerCommand(time=command_time, node=1,
                                     part='fem', command='on')
    assert command_list[0].isclose(expected)

    # test list with duplicates
    command_list = test_session.node_power_command(
        1, ['fem', 'fem'], 'on', testing=True)
    command_time = command_list[0].time
    assert Time.now().gps - command_time < 2.
    expected = node.NodePowerCommand(time=command_time, node=1,
                                     part='fem', command='on')
    assert command_list[0].isclose(expected)

    # test turning on all
    command_list = test_session.node_power_command(
        1, 'all', 'on', testing=True)
    command_times = [cmd.time for cmd in command_list]
    part_list = list(node.power_command_part_dict.keys())
    part_list.remove('snap_relay')
    part_list.insert(0, 'snap_relay')
    for pi, part in enumerate(part_list):
        expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                         part=part, command='on')
        assert command_list[pi].isclose(expected)

    # test adding the commands to the database and retrieving them
    for cmd in command_list:
        test_session.add(cmd)
    result_list = test_session.get_node_power_command(
        starttime=Time.now() - TimeDelta(10, format='sec'),
        stoptime=Time.now() + TimeDelta(10, format='sec'))
    assert len(command_list) == len(result_list)
    result_parts = [cmd.part for cmd in result_list]
    for pi, part in enumerate(part_list):
        index = result_parts.index(part)
        assert command_list[pi].isclose(result_list[index])

    # test turning off all
    command_list = test_session.node_power_command(
        1, 'all', 'off', testing=True)
    command_times = [cmd.time for cmd in command_list]
    part_list = list(node.power_command_part_dict.keys())
    part_list.remove('snap_relay')
    part_list.append('snap_relay')
    for pi, part in enumerate(part_list):
        expected = node.NodePowerCommand(
            time=command_times[pi], node=1, part=part, command='off')
        assert command_list[pi].isclose(expected)

    # test that turning a snap on also turns on the relay
    command_list = test_session.node_power_command(
        1, 'snap0', 'on', testing=True)
    assert len(command_list) == 2
    command_times = [cmd.time for cmd in command_list]
    part_list = ['snap_relay', 'snap0']
    for pi, part in enumerate(part_list):
        expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                         part=part, command='on')
        assert command_list[pi].isclose(expected)

    # test that turning off snap_relay also turns off snaps
    command_list = test_session.node_power_command(
        1, 'snap_relay', 'off', testing=True)
    assert len(command_list) == 5
    command_times = [cmd.time for cmd in command_list]
    part_list = []
    for partname in reversed(list(node.power_command_part_dict.keys())):
        if partname.startswith('snap') and partname != 'snap_relay':
            part_list.append(partname)
    part_list.append('snap_relay')
    for pi, part in enumerate(part_list):
        expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                         part=part, command='off')
        assert command_list[pi].isclose(expected)

    # test erroneous part name
    pytest.raises(ValueError, test_session.node_power_command,
                  1, 'foo', 'on', testing=True)

    # Now test with recent statuses
    # test that turning a snap on also turns on the relay
    # (with recent status of off)
    t1 = Time.now() - TimeDelta(30, format='sec')
    test_session.add_node_power_status(
        t1, 1, False, False, False, False, False, False, False)
    command_list = test_session.node_power_command(
        1, 'snap0', 'on', testing=True)
    assert len(command_list) == 2
    command_times = [cmd.time for cmd in command_list]
    part_list = ['snap_relay', 'snap0']
    for pi, part in enumerate(part_list):
        expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                         part=part, command='on')
        assert command_list[pi].isclose(expected)

    # test that turning a snap doesn't add relay (with recent status of on)
    t1 = Time.now() - TimeDelta(20, format='sec')
    test_session.add_node_power_status(
        t1, 1, True, False, False, False, False, False, False)
    command_list = test_session.node_power_command(
        1, 'snap0', 'on', testing=True)
    assert len(command_list) == 1
    command_time = command_list[0].time
    expected = node.NodePowerCommand(time=command_time, node=1,
                                     part='snap0', command='on')
    assert command_list[0].isclose(expected)

    # test that turning off snap_relay also turns off snaps that are on
    t1 = Time.now() - TimeDelta(10, format='sec')
    test_session.add_node_power_status(
        t1, 1, True, True, True, False, False, False, False)
    command_list = test_session.node_power_command(
        1, 'snap_relay', 'off', testing=True)
    assert len(command_list) == 3
    command_times = [cmd.time for cmd in command_list]
    part_list = []
    for partname in reversed(list(node.power_command_part_dict.keys())):
        if partname == 'snap0' or partname == 'snap1':
            part_list.append(partname)
    part_list.append('snap_relay')
    for pi, part in enumerate(part_list):
        expected = node.NodePowerCommand(time=command_times[pi], node=1,
                                         part=part, command='off')
        assert command_list[pi].isclose(expected)

    # test turning off snap that is on
    command_list = test_session.node_power_command(
        1, 'snap0', 'off', testing=True)
    assert len(command_list) == 1
    command_time = command_list[0].time
    expected = node.NodePowerCommand(time=command_time, node=1,
                                     part='snap0', command='off')
    assert command_list[0].isclose(expected)

    # test turning off fem that is off
    command_list = test_session.node_power_command(
        1, 'fem', 'off', testing=True)
    assert len(command_list) == 0

    # test erroneous part name with a recent status
    pytest.raises(ValueError, test_session.node_power_command,
                  1, 'foo', 'on', testing=True)

    # test various errors
    pytest.raises(ValueError, test_session.node_power_command,
                  31, 'fem', 'on', testing=True)
    pytest.raises(ValueError, test_session.node_power_command,
                  2, 'fem', 'foo', testing=True)
    pytest.raises(ValueError, node.NodePowerCommand.create,
                  command_time, 1, 'fem', 'on')
