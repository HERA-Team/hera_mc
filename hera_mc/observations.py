# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Tracking observations.

"""
from __future__ import absolute_import, division, print_function

import six
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
from sqlalchemy import Column, BigInteger, Float
from sqlalchemy.ext.hybrid import hybrid_property

from . import geo_handling
from . import MCDeclarativeBase, DEFAULT_GPS_TOL, DEFAULT_DAY_TOL, DEFAULT_HOUR_TOL


class Observation(MCDeclarativeBase):
    """
    Definition of hera_obs table.

    obsid: observation identification number, generally equal to the floor of
        the start time in gps seconds (long integer)
    starttime: observation start time in gps seconds (double)
    stoptime: observation stop time in gps seconds (double)
    jd_start: observation start time in JDs, calculated from starttime (double)
    lststart: observation start time in lst, calculated from starttime and
        HERA array location (double)
    """
    __tablename__ = 'hera_obs'
    obsid = Column(BigInteger, primary_key=True, autoincrement=False)
    starttime = Column(Float, nullable=False)  # Float is mapped to DOUBLE PRECISION in postgresql
    stoptime = Column(Float, nullable=False)
    jd_start = Column(Float, nullable=False)
    lst_start_hr = Column(Float, nullable=False)

    # tolerances set to 1ms
    tols = {'starttime': DEFAULT_GPS_TOL, 'stoptime': DEFAULT_GPS_TOL,
            'jd_start': DEFAULT_DAY_TOL, 'lst_start_hr': DEFAULT_HOUR_TOL}

    @hybrid_property
    def length(self):
        return self.stoptime - self.starttime

    @classmethod
    def create(cls, starttime, stoptime, obsid, hera_cofa):
        """
        Create a new observation object using Astropy to compute the LST.

        Parameters:
        ------------
        starttime: astropy time object
            observation starttime
        stoptime: astropy time object
            observation stoptime
        obsid: long integer
            observation identification number.
        """
        if not isinstance(starttime, Time):
            raise ValueError('starttime must be an astropy Time object')
        if not isinstance(stoptime, Time):
            raise ValueError('starttime must be an astropy Time object')
        if not isinstance(obsid, six.integer_types):
            raise ValueError('obsid must be an integer')
        if abs(float(obsid) - starttime.gps) > 1.5:
            raise ValueError('obsid should be close to the starttime in gps seconds')

        # for jd need to ensure that we're in utc
        starttime = starttime.utc

        starttime.location = EarthLocation.from_geodetic(hera_cofa.lon, hera_cofa.lat)

        return cls(obsid=obsid, starttime=starttime.gps, stoptime=stoptime.gps,
                   jd_start=starttime.jd,
                   lst_start_hr=starttime.sidereal_time('apparent').hour)
