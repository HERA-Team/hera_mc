# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the parts and the connections between them.

"""

from __future__ import absolute_import, division, print_function

import datetime
import os
import socket

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String, func

from . import MCDeclarativeBase, NotNull

class Parts(MCDeclarativeBase):
    """A table logging parts within the HERA system
       MAKE Part and Port be unique when combined
       Stations will be considered parts of kind='station'
    """
    __tablename__ = 'parts'

    hpn = Column(String(64), primary_key=True)
    "A unique HERA part number for each part; intend to QRcode with this string."

    short_description = NotNull(String(64))
    "A part-dependent string, i.e. feed, frontend, ...  This is also uniquely encoded in the hera part number (see PARTS.md)"

    manufacturer_number = Column(String(64))
    "A part number/serial number as specified by manufacturer"

    manufacture_date = NotNull(DateTime)
    "The date when the part was manufactured (or assigned by project)."

    def __repr__(self):
        return '<heraPartNumber id={self.hpn} description={self.short_description} manufacture_date={self.manufacture_date}>'.format(self=self)

class PartInfo(MCDeclarativeBase):
    """A table for logging test information etc for parts"""

    __tablename__ = 'part_info'

    id = Column(String(64), primary_key=True)
    "A unique identifier to key on part info"

    hpn = Column(String(64), ForeignKey(Parts.hpn), nullable=False)
    "A unique HERA part number for each part; intend to QRcode with this string."

    short_description = NotNull(String(64))
    "A part-dependent string, i.e. feed, frontend, ...  This is also uniquely encoded in the hera part number (see PARTS.md)"

    info = Column(String(64))
    "This should be an attachment"

    def __repr__(self):
        return '<heraPartNumber id = {self.hpn} description = {self.short_description}>'.format(self=self)

class Connections(MCDeclarativeBase):
    """A table for logging connections between part
       MAKE Part and Port be unique when combined
    """
    __tablename__ = 'connections'

    id = Column(String(64), primary_key=True)
    "A unique identifier to key on connections - A+port_A:B+port_B"

    a = Column(String(64), ForeignKey(Parts.hpn), nullable=False)
    "a refers to the skyward part, e.g. frontend:cable, 'A' is the frontend, 'B' is the cable.  Signal flows from A->B"

    b = Column(String(64), ForeignKey(Parts.hpn), nullable=False)
    "b refers to the part that is further from the sky, e.g. "

    port_on_a = NotNull(String(64))
    "port_on_a refers to the port on the part that is skyward"

    port_on_b = NotNull(String(64))
    "port_on_b refers to the port on the part that is further from the sky"
    
    start_time = NotNull(DateTime)
    "start_time is the time that the connection is set"

    stop_time = Column(DateTime)
    "stop_time is the time that the connection is removed"

    def __repr__(self):
        return '<id = {self.id}>'.format(self=self)

###