# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the parts and the connections between them.

"""

from __future__ import absolute_import, division, print_function

import datetime
import os
import socket
from tabulate import tabulate

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer, String, func

from . import MCDeclarativeBase, NotNull

from hera_mc import mc, cm_utils


class Parts(MCDeclarativeBase):
    """A table logging parts within the HERA system
       MAKE Part and Port be unique when combined
       Stations will be considered parts of kind='station'
       Note that ideally install_date would also be a primary key, but that screws up ForeignKey in connections
       if a hpn gets replaced, save the data by copying an 'old_parts' database to store the record...
    """
    __tablename__ = 'parts_paper'

    hpn = Column(String(64), primary_key=True)
    "HERA part number for each part; intend to QRcode with this string.  hpn+hpn_rev is unique"

    hpn_rev = Column(String(32), primary_key=True)
    "A revision letter if sequences of hpn - starts with A.  hpn+hpn_rev is unique"

    hptype = NotNull(String(64))
    "A part-dependent string, i.e. feed, frontend, ...  This is also uniquely encoded in the hera part number \
     (see PARTS.md) -- this could be derived from it."

    manufacturer_number = Column(String(64))
    "A part number/serial number as specified by manufacturer"

    start_date = NotNull(DateTime)
    "The date when the part was installed (or otherwise assigned by project)."

    stop_date = Column(DateTime)
    "The date when the part was removed (or otherwise de-assigned by project)."

    def __repr__(self):
        return '<heraPartNumber id={self.hpn}{self.hpn_rev} type={self.hptype}>'.format(self=self)

def get_last_revision_number(args,hpn=None,show_revisions=False):
    """
    Return the last revision number for a given part (exact match)
    """
    current = cm_utils._get_datetime(args.date,args.time)
    if hpn is None:
        hpn = args.hpn
    revisions = []
    started = []
    ended = []
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for parts_rec in session.query(Parts).filter(Parts.hpn==hpn):
            revisions.append(parts_rec.hpn_rev)
            started.append(parts_rec.start_date)
            ended.append(parts_rec.stop_date)
    revisions = sorted(revisions)

    over_ride_print = False
    end_date = cm_utils._get_stopdate(ended[-1])
    if current < started[-1] or current > end_date:
        print('Warning:  last revision out of date')
        over_ride_print = True
    if (show_revisions and args.verbosity=='h') or over_ride_print:
        headers = ['HPN','Revision','Start','Stop']
        table_data = []
        for i,rev in enumerate(revisions):
            table_data.append([hpn,rev,started[i],ended[i]])
        print(tabulate(table_data,headers=headers,tablefmt='simple'))
        print('\n')
    elif show_revisions and args.verbosity=='m':
        print('Last revision: ',revisions[-1])
    end_date = cm_utils._get_stopdate(ended[-1])

    return revisions[-1]


def update(args, data):
    """
    update the database given a hera part number with columns/values.
    adds part if add_new_part flag is true
    use with caution -- should usually use in a script which will do datetime primary key

    Parameters:
    ------------
    data:  [[hpn0,rev0,column0,value0],[...]]
    hpnN:  hera part number as primary key
    revN:  hera part number revision as primary key
    columnN:  column name(s)
    values:  corresponding list of values
    """

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for d in data:
            hpn_to_change = d[0].upper()
            rev_to_change = d[1].upper()
            if rev_to_change[:4]=='LAST':
                rev_to_change = get_last_revision_number(args,hpn_to_change)
            part_rec = session.query(Parts).filter( (Parts.hpn == hpn_to_change) & (Parts.hpn_rev == rev_to_change) )
            try:
                if not args.add_new_part:  ### done this way to stop accidentally adding one
                    xxx = getattr(part_rec, d[2])
                setattr(part_rec, d[2], d[3])
            except AttributeError:
                print(d[2], 'does not exist')

def parse_update_request(request):
    """
    parses the update request

    return nested list

    Parameters:
    ------------
    request:  hpn0:[rev0:]column0:value0,hpn1:[rev0]:]column1:value1,[...]
    hpnN:  hera part number, first entry must have one, if absent propagate first
    revN:  hera part revision number, if absent, propagate first, which, if absent, defaults to 'last'
    columnN:  name of parts column
    valueN:  corresponding new value
    """

    # Split out and get first
    data = []
    data_to_proc = request.split(',')
    pcv0 = data_to_proc[0].split(':')
    hpn0 = pcv0[0]
    if len(pcv0)==3:
        rev0 = 'LAST'
    elif len(pcv0)==4:
        rev0 = pcv[1]
    else:
        print('Error:  wrong format for first update entry: ',data_to_proc[0])
        return None

    # Work through all; first must have 3 or 4 entries per above
    for d in data_to_proc:
        pcv = d.split(':')
        if len(pcv) == 4:
            pass
        if len(pcv) == 3:
            pcv.insert(1,'LAST')
        elif len(pcv) == 2:
            pcv.insert(0, hpn0)
            pcv.insert(1, rev0)
        data.append(pcv)
    return data

class PartInfo(MCDeclarativeBase):
    """A table for logging test information etc for parts."""

    __tablename__ = 'part_info'

    hpn = Column(String(64), nullable=False, primary_key=True)
    "A HERA part number for each part; intend to QRcode with this string."

    hpn_rev = Column(String(32), nullable=False, primary_key=True)
    "HERA part revision number for each part; if sequencing same part number."

    posting_date = NotNull(DateTime, primary_key=True)
    "time that the data are posted"

    comment = NotNull(String(1024))
    "Comment associated with this data - or the data itself..."

    info = Column(String(256))
    "This could/should be an attachment"

    def __repr__(self):
        return '<heraPartNumber id = {self.hpn} comment = {self.comment}>'.format(self=self)


class Connections(MCDeclarativeBase):
    """A table for logging connections between parts.  Part and Port must be unique when combined
    """
    __tablename__ = 'connections'

    up = Column(String(64), nullable=False, primary_key=True)
    "up refers to the skyward part, e.g. frontend:cable, 'A' is the frontend, 'B' is the cable.  Signal flows from A->B"

    up_rev = Column(String(32), nullable=False, primary_key=True)
    "up refers to the skyward part revision number"

    down = Column(String(64), nullable=False, primary_key=True)
    "down refers to the part that is further from the sky, e.g. "

    down_rev = Column(String(64), nullable=False, primary_key=True)
    "down refers to the part that is further from the sky, e.g. "

    __table_args__ = (ForeignKeyConstraint(['up',        'up_rev'],
                                           ['parts_paper.hpn', 'parts_paper.hpn_rev']),
                      ForeignKeyConstraint(['down',      'down_rev'],
                                           ['parts_paper.hpn', 'parts_paper.hpn_rev']))

    b_on_up = NotNull(String(64), primary_key=True)
    "connected port on up (skyward) part, which is its port b"

    a_on_down = NotNull(String(64), primary_key=True)
    "connection port on down (further from the sky) part, which is its port a"

    start_date = NotNull(DateTime, primary_key=True)
    "start_time is the time that the connection is set"

    stop_date = Column(DateTime)
    "stop_time is the time that the connection is removed"

    def __repr__(self):
        return '<{self.up}<{self.b_on_up}:{self.a_on_down}>{self.down}>'.format(self=self)

###
