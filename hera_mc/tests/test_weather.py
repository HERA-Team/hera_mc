# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.weather`.

"""
import os
from math import floor

import pytest
import numpy as np
from astropy.time import Time, TimeDelta

from .. import weather
from . import onsite


# could be parameterized
def test_reduce_time_vals():
    times = np.array(range(125)) + 31.24
    values = np.array(range(125)) + 31.24

    dec_times, dec_vals = weather._reduce_time_vals(times, values, 60)

    assert len(dec_times) == 2
    assert np.allclose(dec_times, np.array(range(60, 156, 60)))
    assert np.allclose(dec_vals, np.array(range(60, 156, 60)) + 0.24)

    dec_times, dec_vals = weather._reduce_time_vals(times, values, 3)

    assert len(dec_times) == 41
    assert np.allclose(dec_times, np.array(range(33, 156, 3)))
    assert np.allclose(dec_vals, np.array(range(33, 156, 3)) + 0.24)

    pytest.raises(ValueError, weather._reduce_time_vals, times, values, 1.5)

    # test mean strategy
    dec_times, dec_vals = weather._reduce_time_vals(times, values, 10, strategy="mean")

    assert len(dec_times) == 11
    assert np.allclose(dec_times, np.array(range(40, 146, 10)))
    exp_vals = np.zeros(11)
    for ind in range(11):
        exp_vals[ind] = np.mean(values[ind * 10 + 9 : (ind + 1) * 10 + 9])
    assert np.allclose(dec_vals, exp_vals)

    # test max strategy
    dec_times, dec_vals = weather._reduce_time_vals(times, values, 10, strategy="max")

    assert len(dec_times) == 11
    assert np.allclose(dec_times, np.array(range(40, 146, 10)))
    exp_vals = np.zeros(11)
    for ind in range(11):
        exp_vals[ind] = np.max(values[ind * 10 + 9 : (ind + 1) * 10 + 9])
    assert np.allclose(dec_vals, exp_vals)

    # test sum strategy
    dec_times, dec_vals = weather._reduce_time_vals(times, values, 10, strategy="sum")

    assert len(dec_times) == 11
    assert np.allclose(dec_times, np.array(range(40, 146, 10)))
    exp_vals = np.zeros(11)
    for ind in range(11):
        exp_vals[ind] = np.sum(values[ind * 10 + 9 : (ind + 1) * 10 + 9])
    assert np.allclose(dec_vals, exp_vals)

    # test error
    pytest.raises(
        ValueError, weather._reduce_time_vals, times, values, 10, strategy="foo"
    )


def test_add_weather(mcsession):
    test_session = mcsession
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")

    wind_speeds = [2.5487029167, 2.5470608333]
    wind_directions = [239.382, 223.11]
    temperatures = [11.505, 12.29]

    test_session.add_weather_data(t1, "wind_speed", wind_speeds[0])
    test_session.add_weather_data(t1, "wind_direction", wind_directions[0])
    test_session.add_weather_data(t1, "temperature", temperatures[0])
    test_session.add_weather_data(t2, "wind_speed", wind_speeds[1])
    test_session.add_weather_data(t2, "wind_direction", wind_directions[1])
    test_session.add_weather_data(t2, "temperature", temperatures[1])

    expected = [
        weather.WeatherData(
            time=int(floor(t1.gps)), variable="wind_speed", value=wind_speeds[0]
        ),
        weather.WeatherData(
            time=int(floor(t1.gps)), variable="wind_direction", value=wind_directions[0]
        ),
        weather.WeatherData(
            time=int(floor(t1.gps)), variable="temperature", value=temperatures[0]
        ),
    ]
    result = test_session.get_weather_data(
        starttime=t1 - TimeDelta(3.0, format="sec"), variable="wind_speed"
    )
    assert len(result) == 1
    assert result[0].isclose(expected[0])

    result = test_session.get_weather_data(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t1
    )
    assert len(result) == 3

    result = test_session.get_weather_data(
        starttime=t1 + TimeDelta(200.0, format="sec")
    )
    assert result == []

    expected2 = expected + [
        weather.WeatherData(
            time=int(floor(t2.gps)), variable="wind_speed", value=wind_speeds[1]
        ),
        weather.WeatherData(
            time=int(floor(t2.gps)), variable="wind_direction", value=wind_directions[1]
        ),
        weather.WeatherData(
            time=int(floor(t2.gps)), variable="temperature", value=temperatures[1]
        ),
    ]
    result = test_session.get_weather_data(
        starttime=t1 - TimeDelta(3.0, format="sec"),
        stoptime=t2 + TimeDelta(1.0, format="sec"),
    )
    assert len(result) == len(expected2)

    result = test_session.get_weather_data(
        starttime=t1 + TimeDelta(3.0, format="sec"),
        stoptime=t2 + TimeDelta(1.0, format="sec"),
    )
    assert len(result) == 3

    result_most_recent = test_session.get_weather_data()
    assert result == result_most_recent

    result = test_session.get_weather_data(
        starttime=t1 - TimeDelta(3.0, format="sec"),
        stoptime=t2 + TimeDelta(1.0, format="sec"),
        variable="temperature",
    )
    expected3 = [expected2[2], expected2[5]]
    for i in range(0, len(result)):
        assert result[i].isclose(expected3[i])

    result_var_most_recent = test_session.get_weather_data(variable="temperature")
    assert result_var_most_recent[0] == result[1]

    pytest.raises(ValueError, test_session.get_weather_data, variable="foo")


@onsite
def test_add_from_sensor(mcsession):
    test_session = mcsession
    t1 = Time("2019-11-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(280.0, format="sec")
    t3 = t2 + TimeDelta(300.0, format="sec")
    t4 = t3 + TimeDelta(280.0, format="sec")

    test_session.add_weather_data_from_sensors(t1, t2)
    result = test_session.get_weather_data(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t1
    )
    assert len(result) <= 7
    result = test_session.get_weather_data(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t2
    )
    assert len(result) > 1
    assert len(result) <= (5 * 4 + 2 * 28)

    test_session.add_weather_data_from_sensors(t3, t4, variables="wind_speed")
    result = test_session.get_weather_data(
        starttime=t3 - TimeDelta(3.0, format="sec"), stoptime=t4
    )
    assert len(result) <= 4

    test_session.add_weather_data_from_sensors(
        t3, t4, variables=["wind_direction", "temperature"]
    )
    result = test_session.get_weather_data(
        starttime=t3 - TimeDelta(3.0, format="sec"), stoptime=t3
    )
    assert len(result) <= 3

    pytest.raises(ValueError, weather.create_from_sensors, t1, t2, variables="foo")


def test_weather_errors(mcsession):
    test_session = mcsession
    pytest.raises(ValueError, test_session.add_weather_data, "foo", "wind_speed", 2.548)

    t1 = Time("2017-11-10 01:15:23", scale="utc")
    pytest.raises(ValueError, test_session.add_weather_data, t1, "foo", 2.548)

    pytest.raises(ValueError, test_session.add_weather_data, t1, "wind_speed", "foo")

    t2 = t1 + TimeDelta(280.0, format="sec")

    pytest.raises(
        ValueError,
        test_session.add_weather_data_from_sensors,
        starttime=t1,
        stoptime=t2,
        variables="foo",
    )

    pytest.raises(
        ValueError,
        test_session.add_weather_data_from_sensors,
        starttime=t1,
        stoptime=t2,
        variables=["foo", "bar"],
    )


def test_dump_weather_table(mcsession):
    test_session = mcsession
    # Just make sure it doesn't crash.
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")

    wind_speeds = [2.5487029167, 2.5470608333]
    wind_directions = [239.382, 223.11]
    temperatures = [11.505, 12.29]

    test_session.add_weather_data(t1, "wind_speed", wind_speeds[0])
    test_session.add_weather_data(t1, "wind_direction", wind_directions[0])
    test_session.add_weather_data(t1, "temperature", temperatures[0])
    test_session.add_weather_data(t2, "wind_speed", wind_speeds[1])
    test_session.add_weather_data(t2, "wind_direction", wind_directions[1])
    test_session.add_weather_data(t2, "temperature", temperatures[1])
    for var in ["wind_speed", "wind_direction", "temperature"]:
        filename = var + ".txt"
        test_session.get_weather_data(
            starttime=t1,
            stoptime=t2,
            variable=var,
            write_to_file=True,
            filename=filename,
        )

    os.remove("wind_speed.txt")
    os.remove("wind_direction.txt")
    os.remove("temperature.txt")


def test_tornado_import_error(mcsession):
    test_session = mcsession
    t1 = Time("2019-11-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(280.0, format="sec")

    if not weather.tornado_present:
        with pytest.raises(ImportError, match="tornado is not installed"):
            test_session.add_weather_data_from_sensors(t1, t2)
