# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.weather`.

"""
from __future__ import absolute_import, division, print_function

import unittest
import socket
from math import floor
import numpy as np
from astropy.time import Time, TimeDelta
from hera_mc import mc, weather
from hera_mc.tests import TestHERAMC


def is_at_katcp_enabled_site():
    hostname = socket.gethostname()
    if hostname == 'qmaster':
        return True
    else:
        return False


class TestWeather(TestHERAMC):

    def test_add_weather(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        wind_speeds = [2.5487029167, 2.5470608333]
        wind_directions = [239.382, 223.11]
        temperatures = [11.505, 12.29]

        self.test_session.add_weather_data(t1, 'wind_speed', wind_speeds[0])
        self.test_session.add_weather_data(t1, 'wind_direction', wind_directions[0])
        self.test_session.add_weather_data(t1, 'temperature', temperatures[0])
        self.test_session.add_weather_data(t2, 'wind_speed', wind_speeds[1])
        self.test_session.add_weather_data(t2, 'wind_direction', wind_directions[1])
        self.test_session.add_weather_data(t2, 'temperature', temperatures[1])

        expected = [weather.WeatherData(time=int(floor(t1.gps)), variable='wind_speed',
                                        value=wind_speeds[0]),
                    weather.WeatherData(time=int(floor(t1.gps)),
                                        variable='wind_direction',
                                        value=wind_directions[0]),
                    weather.WeatherData(time=int(floor(t1.gps)),
                                        variable='temperature', value=temperatures[0])]
        result = self.test_session.get_weather_data(t1 - TimeDelta(3.0, format='sec'),
                                                    variable='wind_speed')
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].isclose(expected[0]))

        result = self.test_session.get_weather_data(t1 - TimeDelta(3.0, format='sec'),
                                                    stoptime=t1)
        self.assertEqual(len(result), 3)

        result = self.test_session.get_weather_data(t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

        expected2 = expected +\
            [weather.WeatherData(time=int(floor(t2.gps)), variable='wind_speed',
                                 value=wind_speeds[1]),
             weather.WeatherData(time=int(floor(t2.gps)),
                                 variable='wind_direction', value=wind_directions[1]),
             weather.WeatherData(time=int(floor(t2.gps)),
                                 variable='temperature', value=temperatures[1])]
        result = self.test_session.get_weather_data(t1 - TimeDelta(3.0, format='sec'),
                                                    stoptime=t2 + TimeDelta(1.0, format='sec'))
        self.assertEqual(len(result), len(expected2))

        result = self.test_session.get_weather_data(t1 - TimeDelta(3.0, format='sec'),
                                                    stoptime=t2 + TimeDelta(1.0, format='sec'),
                                                    variable='temperature')
        expected3 = [expected2[2], expected2[5]]
        for i in range(0, len(result)):
            self.assertTrue(result[i].isclose(expected3[i]))

    def test_add_from_sensor(self):
        t1 = Time('2017-11-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(5.0, format='sec')
        t3 = t2 + TimeDelta(10.0, format='sec')
        t4 = t3 + TimeDelta(5.0, format='sec')

        self.assertRaises(ValueError, self.test_session.add_weather_data_from_sensors,
                          starttime=t1, stoptime=t2, variables='foo')

        self.assertRaises(ValueError, self.test_session.add_weather_data_from_sensors,
                          starttime=t1, stoptime=t2, variables=['foo', 'bar'])

        if is_at_katcp_enabled_site():
            self.test_session.add_weather_data_from_sensors(t1, t2)
            result = self.test_session.get_weather_data(t1 - TimeDelta(3.0, format='sec'),
                                                        stoptime=t1)
            self.assertTrue(len(result) <= 3)

            self.test_session.add_weather_data_from_sensors(t3, t4, variables='wind_speed')
            result = self.test_session.get_weather_data(t3 - TimeDelta(3.0, format='sec'),
                                                        stoptime=t3)
            self.assertTrue(len(result) <= 1)

            self.test_session.add_weather_data_from_sensors(t3, t4, variables=['wind_direction',
                                                                               'temperature'])
            result = self.test_session.get_weather_data(t3 - TimeDelta(3.0, format='sec'),
                                                        stoptime=t3)
            self.assertTrue(len(result) <= 3)

            result = self.test_session.get_weather_data(t1 - TimeDelta(3.0, format='sec'),
                                                        stoptime=t4)
            self.assertTrue(len(result) > 1)
            self.assertTrue(len(result) <= 10 * 3)

            self.assertRaises(ValueError, weather.create_from_sensors, t1, t2, variables='foo')


if __name__ == '__main__':
    unittest.main()
