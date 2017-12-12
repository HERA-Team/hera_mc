# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.weather`.

"""
from __future__ import absolute_import, division, print_function

import unittest
import nose.tools as nt
from math import floor
import numpy as np
from astropy.time import Time, TimeDelta
from hera_mc import mc, weather
from hera_mc.tests import TestHERAMC, is_onsite


def test_reduce_time_vals():
    times = np.array(range(125)) + 31.24
    values = np.array(range(125)) + 31.24

    dec_times, dec_vals = weather._reduce_time_vals(times, values, 60)

    nt.assert_equal(len(dec_times), 2)
    nt.assert_true(np.allclose(dec_times, np.array(range(60, 156, 60))))
    nt.assert_true(np.allclose(dec_vals, np.array(range(60, 156, 60)) + .24))

    dec_times, dec_vals = weather._reduce_time_vals(times, values, 3)

    nt.assert_equal(len(dec_times), 41)
    nt.assert_true(np.allclose(dec_times, np.array(range(33, 156, 3))))
    nt.assert_true(np.allclose(dec_vals, np.array(range(33, 156, 3)) + .24))

    nt.assert_raises(ValueError, weather._reduce_time_vals, times, values, 1.5)

    # test mean strategy
    dec_times, dec_vals = weather._reduce_time_vals(times, values, 10, strategy='mean')

    nt.assert_equal(len(dec_times), 11)
    nt.assert_true(np.allclose(dec_times, np.array(range(40, 146, 10))))
    exp_vals = np.zeros(11)
    for ind in range(11):
        exp_vals[ind] = np.mean(values[ind * 10 + 9: (ind + 1) * 10 + 9])
    nt.assert_true(np.allclose(dec_vals, exp_vals))

    # test max strategy
    dec_times, dec_vals = weather._reduce_time_vals(times, values, 10, strategy='max')

    nt.assert_equal(len(dec_times), 11)
    nt.assert_true(np.allclose(dec_times, np.array(range(40, 146, 10))))
    exp_vals = np.zeros(11)
    for ind in range(11):
        exp_vals[ind] = np.max(values[ind * 10 + 9: (ind + 1) * 10 + 9])
    nt.assert_true(np.allclose(dec_vals, exp_vals))

    # test sum strategy
    dec_times, dec_vals = weather._reduce_time_vals(times, values, 10, strategy='sum')

    nt.assert_equal(len(dec_times), 11)
    nt.assert_true(np.allclose(dec_times, np.array(range(40, 146, 10))))
    exp_vals = np.zeros(11)
    for ind in range(11):
        exp_vals[ind] = np.sum(values[ind * 10 + 9: (ind + 1) * 10 + 9])
    nt.assert_true(np.allclose(dec_vals, exp_vals))

    # test error
    nt.assert_raises(ValueError, weather._reduce_time_vals, times, values, 10, strategy='foo')


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
        t2 = t1 + TimeDelta(280.0, format='sec')
        t3 = t2 + TimeDelta(300.0, format='sec')
        t4 = t3 + TimeDelta(280.0, format='sec')

        self.assertRaises(ValueError, self.test_session.add_weather_data_from_sensors,
                          starttime=t1, stoptime=t2, variables='foo')

        self.assertRaises(ValueError, self.test_session.add_weather_data_from_sensors,
                          starttime=t1, stoptime=t2, variables=['foo', 'bar'])

        if is_onsite():
            self.test_session.add_weather_data_from_sensors(t1, t2)
            result = self.test_session.get_weather_data(t1 - TimeDelta(3.0, format='sec'),
                                                        stoptime=t1)
            self.assertTrue(len(result) <= 7)
            result = self.test_session.get_weather_data(t1 - TimeDelta(3.0, format='sec'),
                                                        stoptime=t2)
            self.assertTrue(len(result) > 1)
            self.assertTrue(len(result) <= (5 * 4 + 2 * 28))

            self.test_session.add_weather_data_from_sensors(t3, t4, variables='wind_speed')
            result = self.test_session.get_weather_data(t3 - TimeDelta(3.0, format='sec'),
                                                        stoptime=t4)
            self.assertTrue(len(result) <= 4)

            self.test_session.add_weather_data_from_sensors(t3, t4, variables=['wind_direction',
                                                                               'temperature'])
            result = self.test_session.get_weather_data(t3 - TimeDelta(3.0, format='sec'),
                                                        stoptime=t3)
            self.assertTrue(len(result) <= 3)

            self.assertRaises(ValueError, weather.create_from_sensors, t1, t2, variables='foo')

    def test_read_weather_table(self):
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

        W = weather.Handling(self.test_session)
        W.read_weather_table()
        read_t1 = min(W.wx['wind_speed'].keys())
        self.assertTrue(int(t1.gps), read_t1)
        self.assertTrue(W.wx['wind_speed'][read_t1], wind_speeds[0])

        W.write_weather_files(path='.')
        W.read_weather_files(wx=['wind_speed', 'wind_direction', 'temperature'], path='.')
        self.assertTrue(int(t1.gps), read_t1)
        self.assertTrue(W.wx['wind_speed'][read_t1], wind_speeds[0])

        import os
        os.remove('wind_speed.txt')
        os.remove('wind_direction.txt')
        os.remove('temperature.txt')

if __name__ == '__main__':
    unittest.main()
