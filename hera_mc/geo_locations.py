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

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String, func

from . import MCDeclarativeBase, NotNull


class GeoLocations(MCDeclarativeBase):
    """A table logging parts within the HERA system
       MAKE Part and Port be unique when combined
    """
    __tablename__ = 'geo_locations'

    station_name = Column(String(64), primary_key=True)

    station_number = Column(Integer)

    future_station_number = Column(Integer)

    datum = Column(String(64))

    tile = Column(String(64))

    northing = Column(Float(precision='53'))

    easting = Column(Float(precision='53'))

    elevation = Column(Float)

    def __repr__(self):
        return '<heraPartNumber id={self.hpn} kind={self.kind} manufacture_date={self.manufacture_date}'.format(self=self)

