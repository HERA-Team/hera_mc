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

    obsid:      observation identification number, generally equal to the floor
                of the start time in gps seconds (long integer)
    mc_time:    time metric is reported to M&C in floor(gps seconds) (BigInteger)
    
    """
    __tablename__ = 'ant_metrics'
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), primary_key=True)
    mc_time = Column(BigInteger, nullable=False)

    # tolerances set to 1ms
    tols = {'mc_time': DEFAULT_GPS_TOL}
    
    @classmethod
    def create(cls, obsid, ant, pol, metric, db_time, val):
        """
        Create a new weather object using Astropy to compute the LST.

        Parameters:
        ------------
        obsid: long integer
            observation identification number.
        db_time: astropy time object
            astropy time object based on a timestamp from the database.
            Usually generated from MCSession.get_current_db_time()
        """

        if not isinstance(obsid, (int, long)):
            raise ValueError('obsid must be an integer.')
        if not isinstance(db_time, Time):
            raise ValueError('db_time must be an astropy Time object')
        mc_time = floor(db_time.gps)

        return cls(obsid=obsid, mc_time=mc_time)