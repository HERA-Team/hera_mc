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

import hera_mc.mc as mc


class Parts(MCDeclarativeBase):
    """A table logging parts within the HERA system
       MAKE Part and Port be unique when combined
       Stations will be considered parts of kind='station'
       Note that ideally install_date would also be a primary key, but that screws up ForeignKey in connections
       if a hpn gets replaced, save the data by copying an 'old_parts' database to store the record...
    """
    __tablename__ = 'parts'

    hpn = Column(String(64), primary_key=True)
    "A unique HERA part number for each part; intend to QRcode with this string."

    hptype = NotNull(String(64))
    "A part-dependent string, i.e. feed, frontend, ...  This is also uniquely encoded in the hera part number (see PARTS.md) -- this could be derived from it."

    manufacturer_number = Column(String(64))
    "A part number/serial number as specified by manufacturer"

    install_date = NotNull(DateTime)
    "The date when the part was installed (or otherwise assigned by project)."

    def __repr__(self):
        return '<heraPartNumber id={self.hpn} type={self.hptype} install_date={self.install_date}>'.format(self=self)

class OldParts(MCDeclarativeBase):
    """A table logging parts within the HERA system
       MAKE Part and Port be unique when combined
       Stations will be considered parts of kind='station'
       Note that ideally install_date would also be a primary key, but that screws up ForeignKey in connections
       if a hpn gets replaced, save the data by copying an 'old_parts' database to store the record...
    """
    __tablename__ = 'old_parts'

    hpn = Column(String(64), primary_key=True)
    "A unique HERA part number for each part; intend to QRcode with this string."

    hptype = NotNull(String(64))
    "A part-dependent string, i.e. feed, frontend, ...  This is also uniquely encoded in the hera part number (see PARTS.md) -- this could be derived from it."

    manufacturer_number = Column(String(64))
    "A part number/serial number as specified by manufacturer"

    install_date = NotNull(DateTime,primary_key=True)
    "The date when the part was installed (or otherwise assigned by project)."

    def __repr__(self):
        return '<heraPartNumber id={self.hpn} type={self.hptype} manufacture_date={self.manufacture_date}>'.format(self=self)

def update(args, data):
    """
    update the database given a hera part number with columns/values.
    use with caution -- should usually use in a script which will do datetime primary key

    Parameters:
    ------------
    data:  [[hpn0,column0,value0],[...]]
    hpnN:  hera part number as primary key
    columnN:  column name(s)
    values:  corresponding list of values
    """

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for d in data:
            print (d)
            hpn_to_change = d[0].upper()
            print(hpn_to_change)
            for parts_rec in session.query(Parts).filter(Parts.hpn == hpn_to_change):
                try:
                    xxx = getattr(parts_rec, d[1])
                    setattr(parts_rec, d[1], d[2])
                except AttributeError:
                    print(d[1], 'does not exist')

def parse_update_request(request):
    """
    parses the update request

    return nested list

    Parameters:
    ------------
    request:  hpn0:column0:value0, [hpn1:]column1:value1, [...]
    hpnN:  hera part number, first entry must have one, if absent propagate first
    columnN:  name of parts column
    valueN:  corresponding new value
    """
    data = []
    data_to_proc = request.split(', ')
    hpn0 = data_to_proc[0].split(':')[0]
    for d in data_to_proc:
        pcv = d.split(':')
        if len(pcv) == 3:
            pass
        elif len(pcv) == 2:
            pcv.insert(0, hpn0)
        data.append(pcv)
    return data

class PartInfo(MCDeclarativeBase):
    """A table for logging test information etc for parts."""

    __tablename__ = 'part_info'

    hpn = Column(String(64), ForeignKey(Parts.hpn), nullable=False, primary_key=True)
    "A unique HERA part number for each part; intend to QRcode with this string."

    post_time = NotNull(DateTime, primary_key=True)
    "time that the data are posted"

    comment = NotNull(String(1024))
    "Comment associated with this data - or the data itself..."

    info = Column(String(256))
    "This should be an attachment"

    def __repr__(self):
        return '<heraPartNumber id = {self.hpn} comment = {self.comment}>'.format(self=self)


class Connections(MCDeclarativeBase):
    """A table for logging connections between parts.  Part and Port must be unique when combined
    """
    __tablename__ = 'connections'

    up = Column(String(64), ForeignKey(Parts.hpn), nullable=False, primary_key=True)
    "up refers to the skyward part, e.g. frontend:cable, 'A' is the frontend, 'B' is the cable.  Signal flows from A->B"

    down = Column(String(64), ForeignKey(Parts.hpn), nullable=False, primary_key=True)
    "down refers to the part that is further from the sky, e.g. "

    b_on_up = NotNull(String(64), primary_key=True)
    "connected port on up (skyward) part, which is its port b"

    a_on_down = NotNull(String(64), primary_key=True)
    "connection port on down (further from the sky) part, which is its port a"

    start_time = NotNull(DateTime, primary_key=True)
    "start_time is the time that the connection is set"

    stop_time = Column(DateTime)
    "stop_time is the time that the connection is removed"

    def __repr__(self):
        return '<{self.up}<{self.b_on_up}:{self.a_on_down}>{self.down}>'.format(self=self)

###
