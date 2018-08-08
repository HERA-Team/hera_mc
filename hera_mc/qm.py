# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Handling quality metrics of HERA data.

"""
from __future__ import absolute_import, division, print_function

import six
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
from math import floor
from sqlalchemy import (Column, Integer, BigInteger, Float, ForeignKey,
                        String, ForeignKeyConstraint)
from sqlalchemy.ext.hybrid import hybrid_property

from . import geo_handling
from . import MCDeclarativeBase, DEFAULT_GPS_TOL, DEFAULT_DAY_TOL, DEFAULT_HOUR_TOL


class AntMetrics(MCDeclarativeBase):
    """
    Definition of ant_metrics table.

    obsid:      observation identification number, generally equal to the floor
                of the start time in gps seconds (long integer)
    ant:        Antenna number (int >= 0)
    pol:        Polarization ('x' or 'y')
    metric:     Name of metric (str)
    mc_time:    time metric is reported to M&C in floor(gps seconds) (BigInteger)
    val:        Value of metric (double)
    """
    __tablename__ = 'ant_metrics'
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), primary_key=True)
    ant = Column(Integer, primary_key=True)
    pol = Column(String, primary_key=True)
    metric = Column(String, ForeignKey('metric_list.metric'), primary_key=True)
    mc_time = Column(BigInteger, nullable=False)
    val = Column(Float, nullable=False)

    # tolerances set to 1ms
    tols = {'mc_time': DEFAULT_GPS_TOL}

    @hybrid_property
    def antpol(self):
        return (self.ant, self.pol)

    @classmethod
    def create(cls, obsid, ant, pol, metric, db_time, val):
        """
        Create a new ant_metric object using Astropy to compute the LST.

        Parameters:
        ------------
        obsid: long integer
            observation identification number.
        ant: integer
            antenna number
        pol: string ('x' or 'y')
            polarization
        metric: string
            metric name
        db_time: astropy time object
            astropy time object based on a timestamp from the database.
            Usually generated from MCSession.get_current_db_time()
        val: float
            value of metric
        """

        if not isinstance(obsid, six.integer_types):
            raise ValueError('obsid must be an integer.')
        if not isinstance(ant, six.integer_types):
            raise ValueError('antenna must be an integer.')
        try:
            pol = str(pol)
        except ValueError:
            raise ValueError('pol must be string "x" or "y".')
        pol = pol.lower()
        if pol not in ('x', 'y'):
            raise ValueError('pol must be string "x" or "y".')
        if not isinstance(metric, six.string_types):
            raise ValueError('metric must be string.')
        if not isinstance(db_time, Time):
            raise ValueError('db_time must be an astropy Time object')
        mc_time = floor(db_time.gps)
        try:
            val = float(val)
        except ValueError:
            raise ValueError('val must be castable as float.')

        return cls(obsid=obsid, ant=ant, pol=pol, metric=metric,
                   mc_time=mc_time, val=val)


class ArrayMetrics(MCDeclarativeBase):
    """
    Definition of array_metrics table.

    obsid:      observation identification number, generally equal to the floor
                of the start time in gps seconds (long integer)
    metric:     Name of metric (str)
    mc_time:    time metric is reported to M&C in floor(gps seconds) (BigInteger)
    val:        Value of metric (double)
    """
    __tablename__ = 'array_metrics'
    obsid = Column(BigInteger, ForeignKey('hera_obs.obsid'), primary_key=True)
    metric = Column(String, ForeignKey('metric_list.metric'), primary_key=True)
    mc_time = Column(BigInteger, nullable=False)
    val = Column(Float, nullable=False)

    # tolerances set to 1ms
    tols = {'mc_time': DEFAULT_GPS_TOL}

    @classmethod
    def create(cls, obsid, metric, db_time, val):
        """
        Create a new array_metric object using Astropy to compute the LST.

        Parameters:
        ------------
        obsid: long integer
            observation identification number.
        metric: string
            metric name
        db_time: astropy time object
            astropy time object based on a timestamp from the database.
            Usually generated from MCSession.get_current_db_time()
        val: float
            value of metric
        """

        if not isinstance(obsid, six.integer_types):
            raise ValueError('obsid must be an integer.')
        if not isinstance(metric, six.string_types):
            raise ValueError('metric must be string.')
        if not isinstance(db_time, Time):
            raise ValueError('db_time must be an astropy Time object')
        mc_time = floor(db_time.gps)
        try:
            val = float(val)
        except ValueError:
            raise ValueError('val must be castable as float.')

        return cls(obsid=obsid, metric=metric, mc_time=mc_time, val=val)


class MetricList(MCDeclarativeBase):
    """
    Definition of metric_list table, which provides descriptions of metrics

    metric:     Name of metric (str)
    desc:       Description of metric (str)
    """
    __tablename__ = 'metric_list'
    metric = Column(String, primary_key=True)
    desc = Column(String, nullable=False)

    @classmethod
    def create(cls, metric, desc):
        """
        Create a new ant_metric object using Astropy to compute the LST.

        Parameters:
        ------------
        metric: string
            metric name
        desc: string
            description of metric
        """

        if not isinstance(metric, six.string_types):
            raise ValueError('metric must be string.')
        if not isinstance(desc, six.string_types):
            raise ValueError('metric description must be a string.')

        return cls(metric=metric, desc=desc)
