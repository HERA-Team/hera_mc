# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Handling quality metrics of HERA data.

"""
from __future__ import absolute_import, division, print_function

import numpy as np
from astropy.time import Time
from math import floor
from sqlalchemy import Column, BigInteger, Float, String

import tornado.gen

from . import MCDeclarativeBase

weather_sensor_dict = {'wind_speed': {'sensor_name': 'anc_wind_wind_speed', 'units': 'm/s'},
                       'wind_direction': {'sensor_name': 'anc_wind_wind_direction', 'units': 'degrees'},
                       'temperature': {'sensor_name': 'anc_weather_temperature', 'units': 'deg. Celsius'}}


class WeatherData(MCDeclarativeBase):
    """
    Definition of weather table.

    time: gps time of KAT weather sensor data, floored (BigInteger, part of primary_key).
    variable: name of weather variable. One of the keys in weather_sensor_dict (String, part of primary_key)
    value: measured value (Float)
    """
    __tablename__ = 'weather_data'
    time = Column(BigInteger, primary_key=True)
    variable = Column(String, nullable=False, primary_key=True)
    value = Column(Float, nullable=False)

    @classmethod
    def create(cls, time, variable, value):
        """
        Create a new weather object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp from the katportal sensor.
        variable: string
            must be a key in weather_sensor_dict
        value: float
            value from the sensor associated with the variable
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        if variable not in weather_sensor_dict.keys():
            raise ValueError('variable must be a key in weather_sensor_dict.')
        if not isinstance(value, float):
            raise ValueError('value must be a float.')
        weather_time = floor(time.gps)

        return cls(time=weather_time, variable=variable, value=value)


@tornado.gen.coroutine
def _helper_create_from_sensors(starttime, stoptime, variables=None):
    """
    Create a list of weather objects from sensor data using tornado server.

    Parameters:
    ------------
    starttime: astropy time object
        time to start getting history.
    stoptime: astropy time object
        time to stop getting history.
    variable: string
        variable to get history for. Must be a key in weather_sensor_dict,
        defaults to all keys in weather_sensor_dict

    Returns:
    -----------
    A list of WeatherData objects (only accessible via a yield call)
    """
    from katportalclient import KATPortalClient

    if not isinstance(starttime, Time):
        raise ValueError('starttime must be an astropy Time object')

    if not isinstance(stoptime, Time):
        raise ValueError('stoptime must be an astropy Time object')

    if variables is None:
        variables = weather_sensor_dict.keys()
    elif not isinstance(variables, (list, tuple)):
        variables = [variables]

    sensor_names = []
    sensor_var_dict = {}
    for var in variables:
        if var not in weather_sensor_dict.keys():
            raise ValueError('variable must be a key in weather_sensor_dict')
        sensor_names.append(weather_sensor_dict[var]['sensor_name'])
        sensor_var_dict[weather_sensor_dict[var]['sensor_name']] = var

    portal_client = KATPortalClient('http://portal.mkat.karoo.kat.ac.za/api/client',
                                    on_update_callback=None)

    histories = yield portal_client.sensors_histories(sensor_names, starttime.unix,
                                                      stoptime.unix, timeout_sec=60)

    weather_obj_list = []
    for sensor_name, history in histories.items():
        for item in history:
            # status is usually nominal, but can indicate sensor errors.
            # Since we can't do anything about those and the data might be bad, ignore them
            if item.status != 'nominal':
                continue

            # the value_timestamp is the sensor timestamp, while the other is
            # when the recording system got it. The value_timestamp isn't always
            # present, so test for it
            if 'value_timestamp' in item._fields:
                timestamp = item.value_timestamp
            else:
                timestamp = item.timestamp
            time_use = Time(timestamp, format='unix')
            value = float(item.value)
            weather_obj_list.append(WeatherData.create(time_use,
                                                       sensor_var_dict[sensor_name],
                                                       value))
    raise tornado.gen.Return(weather_obj_list)


def create_from_sensors(starttime, stoptime, variables=None):
    """
    Return a list of weather objects from sensor data.

    Parameters:
    ------------
    starttime: astropy time object
        time to start getting history.
    stoptime: astropy time object
        time to stop getting history.
    variable: string
        variable to get history for. Must be a key in weather_sensor_dict,
        defaults to all keys in weather_sensor_dict

    Returns:
    -----------
    A list of WeatherData objects
    """
    io_loop = tornado.ioloop.IOLoop.current()
    return io_loop.run_sync(lambda: _helper_create_from_sensors(starttime, stoptime,
                                                                variables=variables))
