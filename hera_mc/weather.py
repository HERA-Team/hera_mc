# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Handle weather data sourced from meerkat's katportalclient."""
from math import floor, isnan

from astropy.time import Time
import numpy as np
from sqlalchemy import Column, BigInteger, Float, String

from . import MCDeclarativeBase

no_tornado_message = (
    "tornado is not installed but is required for to get "
    "weather data from katportalclient"
)

tornado_present = True
try:
    import tornado
    from tornado.gen import coroutine as tornado_coroutine
except ImportError as error:

    def tornado_coroutine(func):
        """Spoof this function to avoid name errors with the minimum dependencies."""
        pass

    tornado_present = False
    tornado_error = error


katportal_url = "http://portal.mkat.karoo.kat.ac.za/api/client"

# These are the weather measurements that can be added to the M&C database.
# To add a sensor, add a similar entry in this dict (paying particular attention
# to data volume and reduction strategies and periods)
# You can get the needed information using the katportal example scripts at:
#   https://github.com/ska-sa/katportalclient/tree/master/examples
weather_sensor_dict = {
    "wind_speed": {
        "sensor_name": "anc_mean_wind_speed",
        "units": "m/s",
        "reduction": "mean",
        "period": 300,
        "description": "Mean of ['wind.wind-speed', "
        "'weather.wind-speed'] in (600 * 1.0s) window "
        "(report period: 1s)",
    },
    "wind_gust": {
        "sensor_name": "anc_gust_wind_speed",
        "units": "m/s",
        "reduction": "max",
        "period": 120,
        "description": "Max of ['wind.wind-speed', "
        "'weather.wind-speed'] in (3 * 1.0s) window "
        "(report period: 1s)",
    },
    "wind_direction": {
        "sensor_name": "anc_wind_wind_direction",
        "units": "deg",
        "reduction": "mean",
        "period": 30,
        "description": "Wind direction angle " "(report period: 10s)",
    },
    "temperature": {
        "sensor_name": "anc_weather_temperature",
        "units": "deg Celsius",
        "reduction": "decimate",
        "period": 30,
        "description": "Air temperature (report period: 10s)",
    },
    "humidity": {
        "sensor_name": "anc_weather_humidity",
        "units": "percent",
        "reduction": "mean",
        "period": 60,
        "description": "Air humidity (report period: 10s)",
    },
    "pressure": {
        "sensor_name": "anc_weather_pressure",
        "units": "mbar",
        "reduction": "mean",
        "period": 60,
        "description": "Barometric pressure (report period: 10s)",
    },
    "rain": {
        "sensor_name": "anc_weather_rain",
        "units": "mm",
        "reduction": "sum",
        "period": 60,
        "description": "Rainfall (report period: 10s)",
    },
}


def _reduce_time_vals(times, vals, period, strategy="decimate"):
    """
    Reduce the number of values.

    Parameters
    ----------
    times : float or astropy.time.Time
        Times of readings.
    vals : float
        Reading values.
    period : int
        Final period of reduced values in seconds.
    strategy : {'decimate', 'max', 'mean', 'sum'}
        Strategy for data reduction.

    """
    if not isinstance(period, (int, np.int_)):
        raise ValueError("period must be an integer")

    # the // operator is a floored divide.
    times_keep, inds = np.unique((times // period) * period, return_index=True)
    if times_keep[0] < np.min(times):
        times_keep = times_keep[1:]
        inds = inds[1:]

    if len(inds) < 2:
        return None, None
    if strategy == "decimate":
        vals_keep = vals[inds]  # Could keep with len(inds) == 1, but oh well
    elif strategy == "max":
        vals_keep = []
        times_keep = times_keep[:-1]
        for count in range(len(inds) - 1):
            vals_keep.append(np.max(vals[inds[count] : inds[count + 1]]))
        vals_keep = np.array(vals_keep)
    elif strategy == "mean":
        vals_keep = []
        times_keep = times_keep[:-1]
        for count in range(len(inds) - 1):
            vals_keep.append(np.mean(vals[inds[count] : inds[count + 1]]))
        vals_keep = np.array(vals_keep)
    elif strategy == "sum":
        vals_keep = []
        times_keep = times_keep[:-1]
        for count in range(len(inds) - 1):
            vals_keep.append(np.sum(vals[inds[count] : inds[count + 1]]))
        vals_keep = np.array(vals_keep)
    else:
        raise ValueError("unknown reduction strategy")

    return times_keep, vals_keep


class WeatherData(MCDeclarativeBase):
    """
    Definition of weather table.

    Attributes
    ----------
    time : BigInteger Column
        GPS time of KAT weather sensor data, floored. Part of the primary key.
    variable : String Column
        Name of weather variable. One of the keys in weather_sensor_dict.
        Part of the primary key.
    value : Float Column
        Measured value.

    """

    __tablename__ = "weather_data"
    time = Column(BigInteger, primary_key=True)
    variable = Column(String, nullable=False, primary_key=True)
    value = Column(Float, nullable=False)

    @classmethod
    def create(cls, time, variable, value):
        """
        Create a new weather object.

        Parameters
        ----------
        time : astropy Time object
            Astropy time object based on a timestamp from the katportal sensor.
        variable : str
            Must be a key in weather_sensor_dict.
        value : float
            Value from the sensor associated with the variable.

        Returns
        -------
        WeatherData object

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        if variable not in weather_sensor_dict.keys():
            raise ValueError("variable must be a key in weather_sensor_dict.")
        if not isinstance(value, float):
            raise ValueError("value must be a float.")
        weather_time = floor(time.gps)

        return cls(time=weather_time, variable=variable, value=value)


@tornado_coroutine
def _helper_create_from_sensors(starttime, stoptime, variables=None):
    """
    Create a list of weather objects from sensor data using tornado server.

    Parameters
    ----------
    starttime : astropy Time object
        Time to start getting history.
    stoptime : astropy Time object
        Time to stop getting history.
    variable : str
        Variable to get history for. Must be a key in weather_sensor_dict,
        defaults to all keys in weather_sensor_dict.

    Returns
    -------
    A list of WeatherData objects (only accessible via a yield call)

    """
    from katportalclient import KATPortalClient

    if not isinstance(starttime, Time):
        raise ValueError("starttime must be an astropy Time object")

    if not isinstance(stoptime, Time):
        raise ValueError("stoptime must be an astropy Time object")

    if variables is None:
        variables = weather_sensor_dict.keys()
    elif not isinstance(variables, (list, tuple)):
        variables = [variables]

    sensor_names = []
    sensor_var_dict = {}
    for var in variables:
        if var not in weather_sensor_dict.keys():
            raise ValueError("variable must be a key in weather_sensor_dict")
        sensor_names.append(weather_sensor_dict[var]["sensor_name"])
        sensor_var_dict[weather_sensor_dict[var]["sensor_name"]] = var

    portal_client = KATPortalClient(katportal_url, on_update_callback=None)

    histories = yield portal_client.sensors_histories(
        sensor_names, starttime.unix, stoptime.unix, timeout_sec=120
    )

    weather_obj_list = []
    for sensor_name, history in histories.items():
        variable = sensor_var_dict[sensor_name]
        sensor_times = [0.0]
        sensor_data = []
        for item in history:
            # status is usually nominal, but can indicate sensor errors.
            # Since we can't do anything about those and the data might be bad, ignore them
            if item.status != "nominal":
                continue
            # skip it if nan is supplied
            if isnan(float(item.value)):
                continue

            # the value_time is the sensor timestamp, while the other is
            # when the recording system got it. The value_time isn't always
            # present, so test for it
            if "value_time" in item._fields:
                timestamp = item.value_time
            else:
                timestamp = item.sample_time
            if timestamp > sensor_times[-1]:
                sensor_times.append(timestamp)
                sensor_data.append(float(item.value))
        del sensor_times[0]
        if len(sensor_data):
            reduction = weather_sensor_dict[variable]["reduction"]
            period = weather_sensor_dict[variable]["period"]

            times_use, values_use = _reduce_time_vals(
                np.array(sensor_times),
                np.array(sensor_data),
                period,
                strategy=reduction,
            )
            if times_use is not None:
                for count, timestamp in enumerate(times_use.tolist()):
                    time_obj = Time(timestamp, format="unix")
                    weather_obj_list.append(
                        WeatherData.create(time_obj, variable, values_use[count])
                    )

    raise tornado.gen.Return(weather_obj_list)


def create_from_sensors(starttime, stoptime, variables=None):
    """
    Return a list of weather objects from sensor data.

    Parameters
    ----------
    starttime : astropy Time object
        Time to start getting history.
    stoptime : astropy Time object
        Time to stop getting history.
    variable : str
        Variable to get history for. Must be a key in weather_sensor_dict,
        defaults to all keys in weather_sensor_dict.

    Returns
    -------
    A list of WeatherData objects

    """
    if not tornado_present:
        raise ImportError(no_tornado_message) from tornado_error

    io_loop = tornado.ioloop.IOLoop.current()
    return io_loop.run_sync(
        lambda: _helper_create_from_sensors(starttime, stoptime, variables=variables)
    )
