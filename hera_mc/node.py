# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Node M&C info from the node's Redis database

"""
from __future__ import absolute_import, division, print_function

from astropy.time import Time
from math import floor
from sqlalchemy import Column, BigInteger, Integer, Float, Boolean, String

from . import MCDeclarativeBase

# the address of a redis database being used as a clearing house for meta-data
# and message passing which the node server has access to and watches
defaultServerAddress = 'redishost'

sensor_key_dict = {'top_sensor_temp': 'temp_top', 'middle_sensor_temp': 'temp_mid',
                   'bottom_sensor_temp': 'temp_bot', 'humidity_sensor_temp': 'temp_humid',
                   'humidity': 'humid'}

power_status_key_dict = {'snap_relay_powered': 'power_snap_relay', 'snap0_powered': 'power_snap_0',
                         'snap1_powered': 'power_snap_1', 'snap2_powered': 'power_snap_2',
                         'snap3_powered': 'power_snap_3', 'pam_powered': 'power_pam',
                         'fem_powered': 'power_fem'}

# key is part to command, value is function name in hera_node_mc
power_command_part_dict = {'snap_relay': 'power_snap_relay',
                           'snap0': 'power_snap_0', 'snap1': 'power_snap_1',
                           'snap2': 'power_snap_2', 'snap3': 'power_snap_3',
                           'pam': 'power_pam', 'fem': 'power_fem'}


def get_node_list(nodeServerAddress=defaultServerAddress):
    import nodeControl

    if nodeServerAddress is None:
        nodeServerAddress = defaultServerAddress

    return nodeControl.get_valid_nodes(serverAddress=nodeServerAddress)


class NodeSensor(MCDeclarativeBase):
    """
    Definition of node sensor table.

    time: gps time of the node data, floored (BigInteger, part of primary_key).
    node: node number (Integer, part of primary_key)
    top_sensor_temp: temperature of top sensor reported by node in Celsius
    middle_sensor_temp: temperature of middle sensor reported by node in Celsius
    bottom_sensor_temp: temperature of bottom sensor reported by node in Celsius
    humidity_sensor_temp: temperature of the humidity sensor reported by node in Celsius
    humidity: percent humidity measurement reported by node
    """
    __tablename__ = 'node_sensor'
    time = Column(BigInteger, primary_key=True)
    node = Column(Integer, primary_key=True)
    top_sensor_temp = Column(Float)
    middle_sensor_temp = Column(Float)
    bottom_sensor_temp = Column(Float)
    humidity_sensor_temp = Column(Float)
    humidity = Column(Float)

    @classmethod
    def create(cls, time, node, top_sensor_temp, middle_sensor_temp,
               bottom_sensor_temp, humidity_sensor_temp, humidity):
        """
        Create a new node sensor object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by node
        node: integer
            node number (integer running from 1 to 30)
        top_sensor_temp: float
            temperature of top sensor reported by node in Celsius
        middle_sensor_temp: float
            temperature of middle sensor reported by node in Celsius
        bottom_sensor_temp: float
            temperature of bottom sensor reported by node in Celsius
        humidity_sensor_temp: float
            temperature of the humidity sensor reported by node in Celsius
        humidity: float
            percent humidity measurement reported by node
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        node_time = floor(time.gps)

        return cls(time=node_time, node=node, top_sensor_temp=top_sensor_temp,
                   middle_sensor_temp=middle_sensor_temp,
                   bottom_sensor_temp=bottom_sensor_temp,
                   humidity_sensor_temp=humidity_sensor_temp,
                   humidity=humidity)


def _get_sensor_dict(node, nodeServerAddress=defaultServerAddress):
    import nodeControl

    node_controller = nodeControl.NodeControl(node, serverAddress=nodeServerAddress)

    # Get the sensor data for this node, returned as a dict
    return node_controller.get_sensors()


def create_sensor_readings(nodeServerAddress=defaultServerAddress, node_list=None,
                           sensor_dict=None):
    """
    Return a list of node sensor objects with data from the nodes.

    Parameters:
    ------------
    nodeServerAddress: Address of server where the node redis database can be accessed.
    node_list: A list of integers specifying which nodes to get data for,
        primarily for testing purposes. If None, get_node_list() is called. Default: None.
    sensor_dict: A dict spoofing the return dict from _get_sensor_dict for testing
        purposes. Default: None

    Returns:
    -----------
    A list of NodeSensor objects
    """

    if node_list is None:
        node_list = get_node_list(nodeServerAddress=nodeServerAddress)
    node_sensor_list = []
    for node in node_list:

        if sensor_dict is None:
            timestamp, sensor_data = _get_sensor_dict(node, nodeServerAddress=nodeServerAddress)
        else:
            sensor_data = sensor_dict[str(node)]
            timestamp = sensor_data.pop('timestamp')

        time = Time(timestamp, format='datetime', scale='utc')

        top_sensor_temp = sensor_data.get(sensor_key_dict['top_sensor_temp'], None)
        middle_sensor_temp = sensor_data.get(sensor_key_dict['middle_sensor_temp'], None)
        bottom_sensor_temp = sensor_data.get(sensor_key_dict['bottom_sensor_temp'], None)
        humidity_sensor_temp = sensor_data.get(sensor_key_dict['humidity_sensor_temp'], None)
        humidity = sensor_data.get(sensor_key_dict['humidity'], None)

        node_sensor_list.append(NodeSensor.create(time, node, top_sensor_temp,
                                                  middle_sensor_temp,
                                                  bottom_sensor_temp,
                                                  humidity_sensor_temp, humidity))

    return node_sensor_list


class NodePowerStatus(MCDeclarativeBase):
    """
    Definition of node power status table.

    time: gps time of the node data, floored (BigInteger, part of primary_key).
    node: node number (Integer, part of primary_key)
    snap_relay_powered: power status of the snap relay, True=powered
    snap0_powered: power status of the SNAP 0 board, True=powered
    snap1_powered: power status of the SNAP 1 board, True=powered
    snap2_powered: power status of the SNAP 2 board, True=powered
    snap3_powered: power status of the SNAP 3 board, True=powered
    fem_powered: power status of the FEM, True=powered
    pam_powered: power status of the PAM, True=powered
    """
    __tablename__ = 'node_power_status'
    time = Column(BigInteger, primary_key=True)
    node = Column(Integer, primary_key=True)
    snap_relay_powered = Column(Boolean, nullable=False)
    snap0_powered = Column(Boolean, nullable=False)
    snap1_powered = Column(Boolean, nullable=False)
    snap2_powered = Column(Boolean, nullable=False)
    snap3_powered = Column(Boolean, nullable=False)
    fem_powered = Column(Boolean, nullable=False)
    pam_powered = Column(Boolean, nullable=False)

    @classmethod
    def create(cls, time, node, snap_relay_powered, snap0_powered, snap1_powered,
               snap2_powered, snap3_powered, fem_powered, pam_powered):
        """
        Create a new node power status object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by node
        node: integer
            node number (integer running from 1 to 30)
        snap_relay_powered: boolean
            power status of the snap relay, True=powered
        snap0_powered: boolean
            power status of the SNAP 0 board, True=powered
        snap1_powered: boolean
            power status of the SNAP 1 board, True=powered
        snap2_powered: boolean
            power status of the SNAP 2 board, True=powered
        snap3_powered: boolean
            power status of the SNAP 3 board, True=powered
        fem_powered: boolean
            power status of the FEM, True=powered
        pam_powered: boolean
            power status of the PAM, True=powered
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        node_time = floor(time.gps)

        return cls(time=node_time, node=node, snap_relay_powered=snap_relay_powered,
                   snap0_powered=snap0_powered, snap1_powered=snap1_powered,
                   snap2_powered=snap2_powered, snap3_powered=snap3_powered,
                   fem_powered=fem_powered, pam_powered=pam_powered)


def _get_power_dict(node, nodeServerAddress=defaultServerAddress):
    import nodeControl

    node_controller = nodeControl.NodeControl(node, serverAddress=nodeServerAddress)

    # Get the sensor data for this node, returned as a dict
    return node_controller.get_power_status()


def create_power_status(nodeServerAddress=defaultServerAddress, node_list=None,
                        power_dict=None):
    """
    Return a list of node power status objects with data from the nodes.

    Parameters:
    ------------
    nodeServerAddress: Address of server where the node redis database can be accessed.
    node_list: A list of integers specifying which nodes to get data for,
        primarily for testing purposes. If None, get_node_list() is called. Default: None.
    power_dict: A dict containing info as in the return dict from _get_power_dict()
        for testing purposes. If None, _get_power_dict() is called. Default: None

    Returns:
    -----------
    A list of NodePowerStatus objects
    """

    if node_list is None:
        node_list = get_node_list(nodeServerAddress=nodeServerAddress)
    node_power_list = []
    for node in node_list:

        if power_dict is None:
            timestamp, power_data = _get_power_dict(node, nodeServerAddress=nodeServerAddress)
        else:
            power_data = power_dict[str(node)]
            timestamp = power_data.pop('timestamp')

        time = Time(timestamp, format='datetime', scale='utc')

        # All items in this dictionary are strings.
        snap_relay_powered = power_data[power_status_key_dict['snap_relay_powered']]
        snap0_powered = power_data[power_status_key_dict['snap0_powered']]
        snap1_powered = power_data[power_status_key_dict['snap1_powered']]
        snap2_powered = power_data[power_status_key_dict['snap2_powered']]
        snap3_powered = power_data[power_status_key_dict['snap3_powered']]
        pam_powered = power_data[power_status_key_dict['pam_powered']]
        fem_powered = power_data[power_status_key_dict['fem_powered']]

        node_power_list.append(NodePowerStatus.create(time, node, snap_relay_powered,
                                                      snap0_powered, snap1_powered,
                                                      snap2_powered, snap3_powered,
                                                      fem_powered, pam_powered))

    return node_power_list


class NodePowerCommand(MCDeclarativeBase):
    """
    Definition of node power command table.

    time: gps time of the command, floored (BigInteger, part of primary_key).
    node: node number (Integer, part of primary_key)
    part: part to be powered on/off (String, part of primary_key)
    command: on/off
    """
    __tablename__ = 'node_power_command'
    time = Column(BigInteger, primary_key=True)
    node = Column(Integer, primary_key=True)
    part = Column(String, primary_key=True)
    command = Column(String, nullable=False)

    @classmethod
    def create(cls, time, node, part, command):
        """
        Create a new node power command object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object for time command was sent.
        node: integer
            node number (integer running from 1 to 30)
        part: string
            one of the keys in power_command_part_dict
        command: string
            'on' or 'off'
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        node_time = floor(time.gps)

        if part not in list(power_command_part_dict.keys()):
            raise ValueError('part must be one of: ' + ', '.join(list(power_command_part_dict.keys()))
                             + '. part is actually {}'.format(part))

        if command not in ['on', 'off']:
            raise ValueError('command must be one of: on, off')

        return cls(time=node_time, node=node, part=part, command=command)
