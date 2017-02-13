# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Tracking observations.

"""
from __future__ import absolute_import, division, print_function

import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation, Angle
from sqlalchemy import Column, BigInteger, String, Float
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

from . import MCDeclarativeBase


# TODO: these should not be hardcoded in some random M&C file!!!!
HERA_LAT = Angle('-30d43m17.5s').degree
HERA_LON = Angle('21d25m41.9s').degree
"value taken from capo/cals/hsa7458_v000.py, comment reads KAT/SA  (GPS)"


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
    start_time_jd = Column(DOUBLE_PRECISION, nullable=False)
    stop_time_jd = Column(DOUBLE_PRECISION, nullable=False)
    lst_start_hr = Column(DOUBLE_PRECISION, nullable=False)

    def __repr__(self):
        return ("<Observation('{self.obsid}', '{self.start_time_jd}', "
                "'{self.stop_time_jd}', '{self.lst_start_hr}')>".format(
                    self=self))

    def __eq__(self, other):
        return isinstance(other, Observation) and (
            other.obsid == self.obsid and
            np.allclose(other.start_time_jd, self.start_time_jd) and
            np.allclose(other.stop_time_jd, self.stop_time_jd) and
            np.allclose(other.lst_start_hr, self.lst_start_hr))

    @classmethod
    def new_with_astropy(cls, starttime, stoptime, obsid=None):
        """
        Add an observation to the M&C database, using Astropy to compute
        the LST.

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
        t_start = starttime.utc
        t_stop = stoptime.utc

        if obsid is None:
            from math import floor
            obsid = floor(t_start.gps)

        t_start.location = EarthLocation.from_geodetic(HERA_LON, HERA_LAT)
        return cls(obsid=obsid, start_time_jd=t_start.jd,
                   stop_time_jd=t_stop.jd,
                   lst_start_hr=t_start.sidereal_time('apparent').hour)
