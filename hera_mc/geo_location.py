# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the parts and the connections between them.

"""

from __future__ import absolute_import, division, print_function

import datetime
import os
import socket

import numpy as np

from sqlalchemy import Column, Float, Integer, String, func

from . import MCDeclarativeBase, NotNull


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
        return '<station_name={self.station_name} station_number={self.station_number}'
        ' northing={self.northing} easting={self.easting} elevation={self.elevation}>'.format(self=self)

