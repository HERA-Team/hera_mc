# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
M&C logging of antenna autocorrelation powers.

These are key data for tracking antenna performance and failures.

"""

from math import floor
from astropy.time import Time
import numpy as np
from sqlalchemy import BigInteger, Column, Float, Integer, String
import re
import redis

from . import MCDeclarativeBase
from .correlator import DEFAULT_REDIS_ADDRESS


allowed_measurement_types = ["median"]
measurement_func_dict = {"median": np.median}


def _get_autos_from_redis(redishost=DEFAULT_REDIS_ADDRESS):
    # This is retained so that explicitly providing redishost=None has the desired behavior
    if redishost is None:
        redishost = DEFAULT_REDIS_ADDRESS
    redis_pool = redis.ConnectionPool(host=redishost)
    rsession = redis.Redis(connection_pool=redis_pool)

    auto_time = Time(
        np.frombuffer(rsession.get("auto:timestamp"), dtype=np.float64).item(),
        format="jd",
    )
    autos_dict = {"timestamp": auto_time.jd}

    keys = [
        k.decode("utf-8")
        for k in rsession.keys()
        if k.startswith(b"auto") and not k.endswith(b"timestamp")
    ]

    for key in keys:
        match = re.search(r"auto:(?P<ant>\d+)(?P<pol>e|n)", key)
        if match is not None:
            ant, pol = int(match.group("ant")), match.group("pol")

            antpol = "{ant:d}:{pol:s}".format(ant=ant, pol=pol)
            auto = rsession.get("auto:{ant:d}{pol:s}".format(ant=ant, pol=pol))
            if auto is not None:
                # copy the value because frombuffer returns immutable type
                auto = np.frombuffer(auto, dtype=np.float32).copy()

            autos_dict[antpol] = auto

    return autos_dict


class HeraAuto(MCDeclarativeBase):
    """
    Definition of median antenna autocorrelation table of hera antennas.

    Attributes
    ----------
    time : BigInteger Column
        The time in GPS seconds of the observation, floored as an int. Part of primary_key
    antenna_number : Integer Column
        Antenna number. Part of primary_key.
    antenna_feed_pol : String Column
        Feed polarization, either 'e' or 'n'. Part of primary_key.
    measurement_type : String Column
        The type of measurement.
        Currently available types: median
        Cannot be None.
    value : Float Columnn
        Cannot be None
    """

    __tablename__ = "hera_autos"

    time = Column(BigInteger, primary_key=True)
    antenna_number = Column(Integer, primary_key=True)
    antenna_feed_pol = Column(String, primary_key=True)
    measurement_type = Column(String, nullable=False)
    value = Column(Float, nullable=False)

    @classmethod
    def create(cls, time, antenna_number, antenna_feed_pol, measurement_type, value):
        """
        Create a new Autocorrelation table object.

        Parameters
        ----------
        time : astropy time object
            Astropy time object based on timestamp of autocorrelation.
        antenna_number : int
            Antenna Number
        antenna_feed_pol : str
            Feed polarization, either 'e' or 'n'.
        measurement_type : str
            The measurment type of the autocorrelation.
            Currently supports: 'median'.
        value : float
            The median autocorrelation value as a float.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object.")
        auto_time = floor(time.gps)

        if antenna_feed_pol not in ["e", "n"]:
            raise ValueError("antenna_feed_pol must be 'e' or 'n'.")

        if not isinstance(measurement_type, str):
            raise ValueError("measurement_type must be a string")

        if measurement_type not in allowed_measurement_types:
            raise ValueError(
                "Autocorrelation type {0} not supported. "
                "Only the following types are supported: {1}".format(
                    measurement_type, allowed_measurement_types
                )
            )

        return cls(
            time=auto_time,
            antenna_number=antenna_number,
            antenna_feed_pol=antenna_feed_pol,
            measurement_type=measurement_type,
            value=value,
        )
