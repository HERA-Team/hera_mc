# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Node M&C info from the node's Redis database

"""
from __future__ import absolute_import, division, print_function

from astropy.time import Time
from math import floor
from sqlalchemy import Column, BigInteger, Integer, Float, String, Boolean

from . import MCDeclarativeBase

node_list = [nodeID for nodeID in range(1, 31)]

sensor_key_dict = {'top_sensor_temp': 'temp_top', 'middle_sensor_temp': 'temp_mid',
                   'bottom_sensor_temp': 'temp_bot', 'humidity_sensor_temp': 'temp_humid',
                   'humidty': 'humid'}

power_status_key_dict = {'snap_relay_powered': 'power_snap_relay', 'snap0_powered': 'power_snap_0',
                         'snap1_powered': 'power_snap_1', 'snap2_powered': 'power_snap_2',
                         'snap3_powered': 'power_snap_3', 'pam_powered': 'power_pam',
                         'fem_powered': 'power_fem'}


class NodeSensor(MCDeclarativeBase):
    """
    Definition of node sensor table.

    time: gps time of the node data, floored (BigInteger, part of primary_key).
    node: node number (Integer, part of primary_key)
    top_sensor_temp: temperature of top sensor reported by node in Celcius
    middle_sensor_temp: temperature of middle sensor reported by node in Celcius
    bottom_sensor_temp: temperature of bottom sensor reported by node in Celcius
    humidity_sensor_temp: temperature of the humidity sensor reported by node in Celcius
    humidty: humidity measurement reported by node
    """
    __tablename__ = 'node_sensor'
    time = Column(BigInteger, primary_key=True)
    node = Column(Integer, primary_key=True)
    top_sensor_temp = Column(Float)
    middle_sensor_temp = Column(Float)
    bottom_sensor_temp = Column(Float)
    humidity_sensor_temp = Column(Float)
    humidty = Column(Float)

    @classmethod
    def create(cls, time, node, top_sensor_temp, middle_sensor_temp,
               bottom_sensor_temp, humidity_sensor_temp, humidty):
        """
        Create a new node sensor object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp reported by node
        node: integer
            node number (integer running from 1 to 30)
        top_sensor_temp: float
            temperature of top sensor reported by node in Celcius
        middle_sensor_temp: float
            temperature of middle sensor reported by node in Celcius
        bottom_sensor_temp: float
            temperature of bottom sensor reported by node in Celcius
        humidity_sensor_temp: float
            temperature of the humidity sensor reported by node in Celcius
        humidty: float
            humidity measurement reported by node
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        node_time = floor(time.gps)

        return cls(time=node_time, node=node, top_sensor_temp=top_sensor_temp,
                   middle_sensor_temp=middle_sensor_temp,
                   bottom_sensor_temp=bottom_sensor_temp,
                   humidity_sensor_temp=humidity_sensor_temp,
                   humidty=humidty)


def _get_sensor_dict(node, redisServerHostName=None):
    import nodeControl

    node_controller = nodeControl.NodeControl(nodeID, serverAddress=redisServerHostName)

    # Get the sensor data for this node, returned as a dict
    return node_controller.get_sensors()


def create_sensor(sensor_dict=None):
    """
    Return a list of node sensor objects with data from the nodes.

    Parameters:
    ------------
    sensor_dict: A dict spoofing the return dict from _get_sensor_dict for testing
        purposes. Default: None

    Returns:
    -----------
    A list of NodeSensor objects
    """

    node_sensor_list = []
    for node in node_list:

        if sensor_dict is None:
            # All items in this dictionary are strings.
            sensor_data = _get_sensor_dict(node)
        else:
            sensor_data = sensor_dict[node]

        time = Time(float(sensor_data['timestamp']), format='unix')

        top_sensor_temp = float(sensor_data[sensor_key_dict['top_sensor_temp']])
        middle_sensor_temp = float(sensor_data[sensor_key_dict['middle_sensor_temp']])
        bottom_sensor_temp = float(sensor_data[sensor_key_dict['bottom_sensor_temp']])
        humidity_sensor_temp = float(sensor_data[sensor_key_dict['humidity_sensor_temp']])
        humidty = float(sensor_data[sensor_key_dict['humidty']])

        node_sensor_list.append(NodeSensor.create(time, node, top_sensor_temp,
                                                  middle_sensor_temp,
                                                  bottom_sensor_temp,
                                                  humidity_sensor_temp, humidty))

    return node_sensor_list


class NodePowerStatus(MCDeclarativeBase):
    """
    Definition of node status table.

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
    snap_relay_powered = Column(Boolean)
    snap0_powered = Column(Boolean)
    snap1_powered = Column(Boolean)
    snap2_powered = Column(Boolean)
    snap3_powered = Column(Boolean)
    fem_powered = Column(Boolean)
    pam_powered = Column(Boolean)

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


def _get_power_dict(node, redisServerHostName=None):
    import nodeControl

    node_controller = nodeControl.NodeControl(nodeID, serverAddress=redisServerHostName)

    # Get the sensor data for this node, returned as a dict
    return node_controller.get_power_status()


def create_power_status(power_dict=None):
    """
    Return a list of node power status objects with data from the nodes.

    Parameters:
    ------------
    power_dict: A dict spoofing the return dict from _get_power_dict for testing
        purposes. Default: None

    Returns:
    -----------
    A list of NodePowerStatus objects
    """

    node_power_list = []
    for node in node_list:

        if power_dict is None:
            # All items in this dictionary are strings.
            power_data = _get_power_dict(node)
        else:
            power_data = power_dict[node]

        time = Time(float(power_data['timestamp']), format='unix')

        snap_relay_powered = bool(power_data[sensor_key_dict['snap_relay_powered']])
        snap0_powered = bool(power_data[sensor_key_dict['snap0_powered']])
        snap1_powered = bool(power_data[sensor_key_dict['snap1_powered']])
        snap2_powered = bool(power_data[sensor_key_dict['snap2_powered']])
        snap3_powered = bool(power_data[sensor_key_dict['snap3_powered']])
        pam_powered = bool(power_data[sensor_key_dict['pam_powered']])
        fem_powered = bool(power_data[sensor_key_dict['fem_powered']])

        node_power_list.append(NodePowerStatus.create(time, node, snap_relay_powered,
                                                      snap0_powered, snap1_powered,
                                                      snap2_powered, snap3_powered,
                                                      fem_powered, pam_powered))

    return node_sensor_list
