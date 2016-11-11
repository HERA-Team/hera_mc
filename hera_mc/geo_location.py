# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Keeping track of geo-located stations.

"""

from __future__ import absolute_import, division, print_function

import datetime
import os
import socket

import numpy as np
import matplotlib.pyplot as plt

from sqlalchemy import Column, Float, Integer, String, func

from . import MCDeclarativeBase, NotNull
import hera_mc.mc as mc


class GeoLocation(MCDeclarativeBase):
    """A table logging parts within the HERA system
       MAKE Part and Port be unique when combined
    """
    __tablename__ = 'geo_location'

    station_name = Column(String(64), primary_key=True)
    "Colloquial name of station (which is a unique location on the ground.  This is the primary key, so precision matters."

    station_number = Column(Integer)
    "Unique station number that the correlator and MIRIAD want.  Currently set to numbers as of 16/10/26.  This will be superseded by future version."

    future_station_number = Column(Integer)
    "Unique station nymber in the HERA era."

    datum = Column(String(64))
    "Datum of the geoid."

    tile = Column(String(64))
    "UTM tile"

    northing = Column(Float(precision='53'))
    "Northing coordinate in m"

    easting = Column(Float(precision='53'))
    "Easting coordinate in m"

    elevation = Column(Float)
    "Elevation in m"

    def __repr__(self):
        return '<station_name={self.station_name} station_number={self.station_number} northing={self.northing} \
        easting={self.easting} elevation={self.elevation}>'.format(self=self)

    def update(self,args,data):
        """
        update the database given a station_name/_number with columns/values

        Parameters:
        ------------
        data:  [[station0,column0,value0],[...]]
        stationN:  may be station_name (starts with char) or station_number (is an int)
        values:  corresponding list of values
        """
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for d in data:
                station, station_col = self.station_name_or_number(d[0])
                for geo_rec in session.query(self).filter(station_col==station):
                    try:
                        xxx = getattr(geo_rec,d[1])
                        setattr(geo_rec,d[1],d[2])
                    except AttributeError:
                        print(d[1],'does not exist')

def station_name_or_number(station):
    """
    determines if a station query is for a station_name or station_number
    
    return station, station_col

    Parameters:
    ------------
    station:  station to check
    """
    try:
        station = int(station)
        station_col = GeoLocation.station_number
    except ValueError:
        station = station.upper()
        station_col = GeoLocation.station_name
    return station, station_col

class SubArray(MCDeclarativeBase):
    """
    A table to track sub_array things in various ways
    """
    __tablename__ = 'sub_array'

    prefix = Column(String(64), primary_key=True)
    "String prefix to sub-array type, elements of which are typically characterized by <prefix><int>."

    description = Column(String(64))
    "Short description of sub-array type."

    plot_marker = Column(String(64))
    "matplotlib marker type to use"

    def __repr__(self):
        return '<subarray prefix={self.prefix} description={self.description} marker={self.plot_marker}>'.format(self=self)

