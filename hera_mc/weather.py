# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Handling quality metrics of HERA data.

"""
from __future__ import absolute_import, division, print_function

import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
from math import floor
from sqlalchemy import (Column, Integer, BigInteger, Float, ForeignKey,
                        String, ForeignKeyConstraint)
from sqlalchemy.ext.hybrid import hybrid_property

from hera_mc import geo_handling
from . import MCDeclarativeBase, DEFAULT_GPS_TOL, DEFAULT_DAY_TOL, DEFAULT_HOUR_TOL

class WeatherData(MCDeclarativeBase):
    """
    Definition of weather table.
    
    weather_time: timestamp of KAT weather sensor data, floored (BigInteger).
    
    mc_time:    time metric is reported to M&C in floor(gps seconds) (BigInteger)
    
    wind_speed: wind speed reported by sensor name "anc_wind_wind_speed" in m/s (Float)
    
    wind_direction: wind direction reported by sensor name "anc_wind_wind_direction" 
                    in degrees (Float)
    
    temperature: air temperature reported by sensor name "anc_weather_temperature" in
                 degrees Celcius (Float)
    """
    __tablename__ = 'ant_metrics'
    weather_time = Column(BigInteger, primary_key=True)
    mc_time = Column(BigInteger, nullable=False)
    
    # these sensors can go down some times, so I'm going to keep them nullable
    wind_speed = Column(Float)
    wind_direction = Column(Float)
    temperature = Column(Float)
    
    # tolerances set to 1ms
    tols = {'mc_time': DEFAULT_GPS_TOL}
    
    @classmethod
    def create(cls, weather_time, mc_time, windspeedval, winddirval, tempval):
        """
        Create a new weather object.

        Parameters:
        ------------
        weather_time: long integer
            sensor time
        mc_time: astropy time object
            astropy time object based on a timestamp from the database.
            Usually generated from MCSession.get_current_db_time()
        windspeedval: float
            wind speed from KAT sensor
        winddirval: float
            wind direction from KAT sensor
        tempval: float
            temperature from KAT sensor
        """
        if not isinstance(weather_time, (int, long)):
            raise ValueError('weather_time must be an integer.')
        if not isinstance(mc_time, Time):
            raise ValueError('db_time must be an astropy Time object')
        if not isinstance(windspeedval, (float)):
            raise ValueError('wind_speed must be a float.')
        if not isinstance(winddirval, (float)):
            raise ValueError('wind_direction must be a float.')
        if not isinstance(tempval, (float)):
            raise ValueError('temperature must be a float.')
        mc_time = floor(mc_time.gps)

        return cls(weather_time=weather_time, mc_time=mc_time,
                   wind_speed=windspeedval, wind_direction=winddirval,
                   temperature=tempval)