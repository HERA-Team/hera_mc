# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Roach info from Redis database

"""
from __future__ import absolute_import, division, print_function

from astropy.time import Time
from math import floor
from sqlalchemy import Column, BigInteger, Float, String

from . import MCDeclarativeBase

redis_dbname = "paper1.paper.pvt"

# These are the values to keep out of the redis database
roach_key_dict = {'ambient_temp': 'raw.temp.ambient', 'inlet_temp': 'raw.temp.inlet',
                  'outlet_temp': 'raw.temp.outlet', 'fpga_temp': 'raw.temp.fpga',
                  'ppc_temp': 'raw.temp.ppc'}


class RoachTemperature(MCDeclarativeBase):
    """
    Definition of roach (fpga correlator board) temperature table.

    time: gps time of the roach data, floored (BigInteger, part of primary_key).
    roach: roach number (Integer, part of primary_key)
    ambient_temp: ambient temperature reported by roach in Celcius
    inlet_temp: inlet temperature reported by roach in Celcius
    outlet_temp: outlet temperature reported by roach in Celcius
    fpga_temp: fpga temperature reported by roach in Celcius
    ppc_temp: ppc temperature reported by roach in Celcius
    """
    __tablename__ = 'roach_temperature'
    time = Column(BigInteger, primary_key=True)
    roach = Column(String, primary_key=True)
    ambient_temp = Column(Float)
    inlet_temp = Column(Float)
    outlet_temp = Column(Float)
    fpga_temp = Column(Float)
    ppc_temp = Column(Float)

    @classmethod
    def create(cls, time, roach, ambient_temp, inlet_temp, outlet_temp, fpga_temp, ppc_temp):
        """
        Create a new roach temperature object.

        Parameters:
        ------------
        time: astropy time object
            astropy time object based on a timestamp from the katportal sensor.
        roach: string
            roach name or number
        ambient_temp: float
            ambient temperature reported by roach for this time in Celcius
        inlet_temp: float
            inlet temperature reported by roach for this time in Celcius
        outlet_temp: float
            outlet temperature reported by roach for this time in Celcius
        fpga_temp: float
            fpga temperature reported by roach for this time in Celcius
        ppc_temp: float
            ppc temperature reported by roach for this time in Celcius
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        roach_time = floor(time.gps)

        return cls(time=roach_time, roach=roach, ambient_temp=ambient_temp,
                   inlet_temp=inlet_temp, outlet_temp=outlet_temp,
                   fpga_temp=fpga_temp, ppc_temp=ppc_temp)


def _get_redis_dict(roach_num):
    import redis

    r = redis.Redis(redis_dbname)

    # redis key names have the form "roachsensor:<roachhostname>"
    # roachhostnames are pf1, pf2, ..., pf8
    # Each key stores a hash table of different sensors
    roach = "pf%d" % roach_num
    rkey = "roachsensor:%s" % roach

    # Get the entire hash table for this ROACH's key, returned as a dictionary
    return r.hgetall(rkey)


def create_from_redis(redis_dict=None):
    """
    Return a list of roach temperature objects from the redis database.

    Parameters:
    ------------
    redis_dict: A dict spoofing the return dict from _get_redis_dict for testing
        purposes. Default: None

    Returns:
    -----------
    A list of RoachTemperature objects
    """

    roach_obj_list = []
    for i in range(1, 9):

        if redis_dict is None:
            # All items in this dictionary are strings.
            rdict = _get_redis_dict(i)
        else:
            rdict = redis_dict["pf%d" % i]

        time = Time(float(rdict['timestamp']), format='unix')

        # temperatures are in millidegrees C. convert to degrees C
        ambient_temp = float(rdict[roach_key_dict['ambient_temp']]) / 1000.
        inlet_temp = float(rdict[roach_key_dict['inlet_temp']]) / 1000.
        outlet_temp = float(rdict[roach_key_dict['outlet_temp']]) / 1000.
        fpga_temp = float(rdict[roach_key_dict['fpga_temp']]) / 1000.
        ppc_temp = float(rdict[roach_key_dict['ppc_temp']]) / 1000.

        roach_obj_list.append(RoachTemperature.create(time, str(i), ambient_temp,
                                                      inlet_temp, outlet_temp,
                                                      fpga_temp, ppc_temp))

    return roach_obj_list
