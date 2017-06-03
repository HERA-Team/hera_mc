# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Tracking observations.

"""
from __future__ import absolute_import, division, print_function

import numpy as np
from math import floor
from astropy.time import Time
from astropy.coordinates import EarthLocation, Angle
from sqlalchemy import Column, BigInteger, Float
from hera_mc import geo_handling
from . import MCDeclarativeBase


class Observation(MCDeclarativeBase):
    """
    Definition of hera_obs table.

    obsid: observation identification number, generally equal to the
        start time in gps seconds (long integer)
    starttime: observation start time in jd (double)
    stoptime: observation stop time in jd (double)
    lststart: observation start time in lst (double)
    """
    __tablename__ = 'hera_obs'
    obsid = Column(BigInteger, primary_key=True)
    start_time_jd = Column(Float, nullable=False)  # Float is mapped to DOUBLE PRECISION in postgresql
    stop_time_jd = Column(Float, nullable=False)
    lst_start_hr = Column(Float, nullable=False)

    # tolerances set to 1ms
    tols = {'obsid': {'atol': .1, 'rtol': 0},
            'start_time_jd': {'atol': 1e-3 / (3600. * 24.), 'rtol': 0},
            'stop_time_jd': {'atol': 1e-3 / (3600. * 24.), 'rtol': 0},
            'lst_start_hr': {'atol': 1e-3 / (3600), 'rtol': 0}}

    @classmethod
    def new_observation(cls, starttime, stoptime, obsid=None):
        """
        Create a new observation object using Astropy to compute the LST.

        Parameters:
        ------------
        starttime: astropy time object
            observation starttime
        stoptime: astropy time object
            observation stoptime
        obsid: long integer
            observation identification number. If not provided, will be set
            to the gps second corresponding to the starttime using floor.
        """
        if not isinstance(starttime, Time):
            raise ValueError('starttime must be an astropy Time object')
        if not isinstance(stoptime, Time):
            raise ValueError('starttime must be an astropy Time object')
        starttime = starttime.utc
        stoptime = stoptime.utc

        if obsid is None:
            obsid = floor(starttime.gps)

        hera_cofa = geo_handling.cofa()
        starttime.location = EarthLocation.from_geodetic(hera_cofa.lon, hera_cofa.lat)
        return cls(obsid=obsid, start_time_jd=starttime.jd,
                   stop_time_jd=stoptime.jd,
                   lst_start_hr=starttime.sidereal_time('apparent').hour)
