# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the parts and the connections between them.

"""

from __future__ import absolute_import, division, print_function

import os
import socket
from tabulate import tabulate

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer, String, func

from . import MCDeclarativeBase, NotNull

from hera_mc import mc, cm_utils

# Probably bad practice, but these currently mirror the class objects to get the case right for values.
upper_case = ['hpn', 'hpn_rev', 'upstream_part', 'up_part_rev', 'downstream_part', 'down_part_rev']
lower_case = ['upstream_output_port', 'downstream_input_port']

class Parts(MCDeclarativeBase):
    """A table logging parts within the HERA system
       Stations will be considered parts of type='station'
       Note that ideally install_date would also be a primary key, but that screws up ForeignKey in connections
    """
    __tablename__ = 'parts_paper'

    hpn = Column(String(64), primary_key=True)
    "HERA part number for each part; intend to QRcode with this string.  hpn+hpn_rev is unique"

    hpn_rev = Column(String(32), primary_key=True)
    "A revision letter of sequences of hpn - starts with A.  hpn+hpn_rev is unique"

    hptype = NotNull(String(64))
    "A part-dependent string, i.e. feed, frontend, ...  This is also uniquely encoded in the hera part number \
     (see PARTS.md) -- this could be derived from it but this removes that constraint."

    manufacturer_number = Column(String(64))
    "A part number/serial number as specified by manufacturer"

    start_date = Column(DateTime(timezone=True), nullable=False)
    "The date when the part was installed (or otherwise assigned by project)."

    stop_date = Column(DateTime(timezone=True))
    "The date when the part was removed (or otherwise de-assigned by project)."

    def __repr__(self):
        return '<heraPartNumber id={self.hpn}{self.hpn_rev} type={self.hptype}>'.format(self=self)

    def part(self, **kwargs):
        for key, value in kwargs.items():
            if key in upper_case:
                value = value.upper()
            setattr(self, key, value)


def get_last_revision(args, hpn=None, show_revisions=False):
    """
    Return the last revision number for a given part (exact match)
    """
    current = cm_utils._get_datetime(args.date, args.time)
    if hpn is None:
        hpn = args.hpn
    revisions = []
    started = []
    ended = []
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for parts_rec in session.query(Parts).filter(Parts.hpn == hpn):
            revisions.append(parts_rec.hpn_rev)
            started.append(parts_rec.start_date)
            ended.append(parts_rec.stop_date)
    revisions = sorted(revisions)

    over_ride_print = False
    end_date = cm_utils._get_stopdate(ended[-1])
    if current < started[-1] or current > end_date:
        print('Warning:  last revision out of date')
        over_ride_print = True
    if (show_revisions and args.verbosity == 'h') or over_ride_print:
        headers = ['HPN', 'Revision', 'Start', 'Stop']
        table_data = []
        for i, rev in enumerate(revisions):
            table_data.append([hpn, rev, started[i], ended[i]])
        print(tabulate(table_data, headers=headers, tablefmt='simple'))
        print('\n')
    elif show_revisions and args.verbosity == 'm':
        print('Last revision: ', revisions[-1])
    #end_date = cm_utils._get_stopdate(ended[-1])

    return revisions[-1]


def update_part(args, data):
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
    data_dict = format_and_check_update_part_request(data)
    if data_dict is None:
        print('Error: invalid update')
        return False
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for dkey in data_dict.keys():
            hpn_to_change = data_dict[dkey][0][0]
            rev_to_change = data_dict[dkey][0][1]
            if rev_to_change[:4] == 'LAST':
                rev_to_change = get_last_revision_number(args, hpn_to_change)
            part_rec = session.query(Parts).filter((Parts.hpn == hpn_to_change) &
                                                   (Parts.hpn_rev == rev_to_change))
            npc = part_rec.count()
            if npc == 0:
                if args.add_new_part:
                    part = Parts()
                else:
                    print("Error: ", dkey,
                          "does not exist and add_new_part not enabled.")
                    part = None
            elif npc == 1:
                if args.add_new_part:
                    print("Error: ", dkey, "exists and add_new_part is enabled.")
                    part = None
                else:
                    part = part_rec.first()
            else:
                print("Shouldn't ever get here.")
                part = None
            if part:
                for d in data_dict[dkey]:
                    try:
                        setattr(part, d[2], d[3])
                    except AttributeError:
                        print(d[2], 'does not exist as a field')
                        continue
                session.add(part)
    cm_utils._log('part_connect part update', data_dict=data_dict)
    return True


def format_and_check_update_part_request(request):
    """
    parses the update request

    return dictionary

    Parameters:
    ------------
    request:  hpn0:[rev0:]column0:value0,hpn1:[rev0]:]column1:value1,[...] or list
    hpnN:  hera part number, first entry must have one, if absent propagate first
    revN:  hera part revision number, if absent, propagate first, which, if absent, defaults to 'last'
    columnN:  name of parts column
    valueN:  corresponding new value
    """

    # Split out and get first
    data = {}
    if type(request) == str:
        tmp = request.split(',')
        data_to_proc = []
        for d in tmp:
            data_to_proc.append(d.split(':'))
    else:
        data_to_proc = request
    if len(data_to_proc[0]) == 4:
        hpn0 = data_to_proc[0][0].upper()
        rev0 = data_to_proc[0][1].upper()
    elif len(data_to_proc[0]) == 3:
        hpn0 = data_to_proc[0][0].upper()
        rev0 = 'LAST'
    else:
        print('Error:  wrong format for first part update entry: ',
              data_to_proc[0])
        return None
    for d in data_to_proc:
        if len(d) == 4:
            pass
        elif len(d) == 3:
            d.insert(1, 'LAST')
        elif len(d) == 2:
            d.insert(0, hpn0)
            d.insert(1, rev0)
        else:
            print('Invalid format for update request.')
            continue
        d[0] = d[0].upper()
        d[1] = d[1].upper()
        if d[2] in upper_case:
            d[3] = d[3].upper()
        dkey = d[0] + ':' + d[1]
        if dkey in data.keys():
            data[dkey].append(d)
        else:
            data[dkey] = [d]
    return data


class PartInfo(MCDeclarativeBase):
    """A table for logging test information etc for parts."""

    __tablename__ = 'part_info'

    hpn = Column(String(64), nullable=False, primary_key=True)
    "A HERA part number for each part; intend to QRcode with this string."

    hpn_rev = Column(String(32), nullable=False, primary_key=True)
    "HERA part revision number for each part; if sequencing same part number."

    posting_date = NotNull(DateTime(timezone=True), primary_key=True)
    "time that the data are posted"

    comment = NotNull(String(2048))
    "Comment associated with this data - or the data itself..."

    library_file = Column(String(256))
    "Name of datafile held in library"

    def __repr__(self):
        return '<heraPartNumber id = {self.hpn} comment = {self.comment}>'.format(self=self)

    def info(self, **kwargs):
        for key, value in kwargs.items():
            if key in upper_case:
                value = value.upper()
            setattr(self, key, value)


class Connections(MCDeclarativeBase):
    """A table for logging connections between parts.  Part and Port must be unique when combined
    """
    __tablename__ = 'connections'

    upstream_part = Column(String(64), nullable=False, primary_key=True)
    "up refers to the skyward part, e.g. frontend:cable, 'A' is the frontend, 'B' is the cable.  Signal flows from A->B"

    up_part_rev = Column(String(32), nullable=False, primary_key=True)
    "up refers to the skyward part revision number"

    downstream_part = Column(String(64), nullable=False, primary_key=True)
    "down refers to the part that is further from the sky, e.g. "

    down_part_rev = Column(String(64), nullable=False, primary_key=True)
    "down refers to the part that is further from the sky, e.g. "

    __table_args__ = (ForeignKeyConstraint(['upstream_part',   'up_part_rev'],
                                           ['parts_paper.hpn', 'parts_paper.hpn_rev']),
                      ForeignKeyConstraint(['downstream_part', 'down_part_rev'],
                                           ['parts_paper.hpn', 'parts_paper.hpn_rev']))

    upstream_output_port = NotNull(String(64), primary_key=True)
    "connected output port on upstream (skyward) part"

    downstream_input_port = NotNull(String(64), primary_key=True)
    "connected input port on downstream (further from the sky) part"

    start_date = NotNull(DateTime(timezone=True), primary_key=True)
    "start_time is the time that the connection is set"

    stop_date = Column(DateTime(timezone=True))
    "stop_time is the time that the connection is removed"

    def __repr__(self):
        return '<{self.upstream_part}<{self.upstream_output_port}:{self.downstream_input_port}>{self.downstream_part}>'.format(self=self)

    def connection(self, **kwargs):
        for key, value in kwargs.items():
            if key in upper_case:
                value = value.upper()
            elif key in lower_case:
                value = value.lower()
            setattr(self, key, value)


def update_connection(args, data):
    """
    update the database given a connection with columns/values.
    adds if add_new_connection flag is true

    Parameters:
    ------------

    columnN:  column name(s)
    values:  corresponding list of values
    """
    data_dict = format_check_update_connection_request(data)
    if data_dict is None:
        print('Error: invalid update')
        return False
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for dkey in data_dict.keys():
            upcn_to_change = data_dict[dkey][0][0]
            urev_to_change = data_dict[dkey][0][1]
            dncn_to_change = data_dict[dkey][0][2]
            drev_to_change = data_dict[dkey][0][3]
            boup_to_change = data_dict[dkey][0][4]
            aodn_to_change = data_dict[dkey][0][5]
            strt_to_change = data_dict[dkey][0][6]
            if urev_to_change[:4] == 'LAST':
                urev_to_change = get_last_revision_number(args, upcn_to_change)
            if drev_to_change[:4] == 'LAST':
                drev_to_change = get_last_revision_number(args, dncn_to_change)
            conn_rec = session.query(Connections).filter((Connections.upstream_part == upcn_to_change) &
                                                         (Connections.up_part_rev == urev_to_change) &
                                                         (Connections.downstream_part == dncn_to_change) &
                                                         (Connections.down_part_rev == drev_to_change) &
                                                         (Connections.upstream_output_port == boup_to_change) &
                                                         (Connections.downstream_input_port == aodn_to_change) &
                                                         (Connections.start_date == strt_to_change))
            ncc = conn_rec.count()
            if ncc == 0:
                if args.add_new_connection:
                    connection = Connections()
                    connection.connection(up=upcn_to_change, up_rev=urev_to_change,
                                          down=dncn_to_change, down_rev=drev_to_change,
                                          upstream_output_port=boup_to_change, downstream_input_port=aodn_to_change,
                                          start_date=strt_to_change)
                else:
                    print(
                        "Error:", dkey, "does not exist and add_new_connection is not enabled.")
                    connection = None
            elif ncc == 1:
                if args.add_new_connection:
                    print("Error:", dkey, "exists and and_new_connection is enabled")
                    connection = None
                else:
                    connection = conn_rec.first()
            else:
                print("Shouldn't ever get here.")
                connection = None
            if connection:
                for d in data_dict[dkey]:
                    try:
                        setattr(connection, d[7], d[8])
                    except AttributeError:
                        print(dkey, 'does not exist as a field')
                        continue
                session.add(connection)
    cm_utils._log('part_connect connection update', data_dict=data_dict)
    return True


def format_check_update_connection_request(request):
    """
    parses the update request

    return dictionary

    Parameters:
    ------------
    request:   or list
    columnN:  name of parts column
    valueN:  corresponding new value
    """

    # Split out and get first
    data = {}
    if type(request) == str:
        tmp = request.split(',')
        data_to_proc = []
        for d in tmp:
            data_to_proc.append(d.split(':'))
    else:
        data_to_proc = request
    for d in data_to_proc:
        if len(d) == 9:
            pass
        elif len(d) == 7:
            d.insert(1, 'LAST')
            d.insert(3, 'LAST')
        else:
            print('Invalid format for connection update request.')
            continue
        dkey = d[0] + ':' + d[2] + ':' + d[4] + ':' + d[5]
        # Make the case of everything correct
        for i in range(4):
            d[i] = d[i].upper()
        for i in range(4, 6):
            d[i] = d[i].lower()
        if d[7] in upper_case:
            d[8] = d[8].upper()
        elif d[7] in lower_case:
            d[8] = d[8].lower()
        if dkey in data.keys():
            data[dkey].append(d)
        else:
            data[dkey] = [d]
    return data

###
