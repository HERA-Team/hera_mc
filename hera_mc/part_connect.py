# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of the parts and the connections between them.

"""

from __future__ import absolute_import, division, print_function

import os
import socket
from tabulate import tabulate
import math
from astropy.time import Time

from sqlalchemy import BigInteger, Column, Float, ForeignKey, ForeignKeyConstraint, Integer, String, func

from . import MCDeclarativeBase, NotNull

from hera_mc import mc, cm_utils

# Probably bad practice, but these currently mirror the class objects to get the case right for values in database.
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

    start_gpstime = Column(BigInteger, nullable=False)
    "The date when the part was installed (or otherwise assigned by project)."

    stop_gpstime = Column(BigInteger)
    "The date when the part was removed (or otherwise de-assigned by project)."

    def __repr__(self):
        return '<heraPartNumber id={self.hpn}{self.hpn_rev} type={self.hptype}>'.format(self=self)

    def gps2Time(self):
        """
        Adds gps seconds to the Time
        """

        self.start_date = Time(self.start_gpstime, format='gps')
        if self.stop_gpstime is None:
            self.stop_date = None
        else:
            self.stop_date = Time(self.stop_gpstime, format='gps')

    def part(self, **kwargs):
        """
        Allows one to specify and arbitrary part.
        """
        for key, value in kwargs.items():
            if key in upper_case:
                value = value.upper()
            setattr(self, key, value)


def stop_existing_parts(session, p, hpnr_list, at_date, actually_do_it):
    """
    This adds stop times to the previous parts.

    Parameters:
    ------------
    session:  db session to use
    p:  part object
    hpnr_list:  list containing hpn and revision
    at_date:  date to use for stopping
    actually_do_it:  boolean to allow the part to be stopped
    """

    stop_at = int(at_date.gps)
    data = []

    for hpnr in hpnr_list:
        p.part(hpn=hpnr[0], hpn_rev=hpnr[1], hptype=hpnr[2], manufacturer_number=hpnr[3])
        print("Stopping part {} at {}".format(p, str(at_date)))
        data.append([p.hpn, p.hpn_rev, 'stop_gpstime', stop_at])

    if actually_do_it:
        update_part(session, data, False)
    else:
        print("--Here's what would happen if you set the --actually_do_it flag:")
        for d in data:
            print('\t' + str(d))


def add_new_parts(session, p, new_part_list, at_date, actually_do_it):
    """
    This adds the new parts.
    Parameters:
    ------------
    session:  db session to use
    p:  part object
    hpnr_list:  list containing hpn and revision
    at_date:  date to use for stopping
    actually_do_it:  boolean to allow the part to be added
    """

    start_at = int(at_date.gps)
    data = []

    for hpnr in new_part_list:
        p.part(hpn=hpnr[0], hpn_rev=hpnr[1], hptype=hpnr[2], manufacturer_number=hpnr[3])
        print("Adding part {} at {}".format(p, str(at_date)))
        data.append([p.hpn, p.hpn_rev, 'hpn', p.hpn])
        data.append([p.hpn, p.hpn_rev, 'hpn_rev', p.hpn_rev])
        data.append([p.hpn, p.hpn_rev, 'hptype', p.hptype])
        data.append([p.hpn, p.hpn_rev, 'manufacturer_number', p.manufacturer_number])
        data.append([p.hpn, p.hpn_rev, 'start_gpstime', start_at])

    if actually_do_it:
        update_part(session, data, True)
    else:
        print("--Here's what would happen if you set the --actually_do_it flag:")
        for d in data:
            print('\t' + str(d))


def update_part(session=None, data=None, add_new_part=False):
    """
    update the database given a hera part number with columns/values.
    adds part if add_new_part flag is true
    use with caution -- should usually use in a script which will do datetime primary key

    Parameters:
    ------------
    session:  db session to use
    data:  [[hpn0,rev0,column0,value0],[...]]
        hpnN:  hera part number as primary key
        revN:  hera part number revision as primary key
        columnN:  column name(s)
        values:  corresponding list of values
    add_new_part:  boolean to allow a new part to be added
    """

    data_dict = format_and_check_update_part_request(data)
    if data_dict is None:
        print('Error: invalid update_part -- doing nothing.')
        return False

    close_session_when_done = False
    if session is None:
        db = mc.connect_mc_db()
        session = db.sessionmaker()
        close_session_when_done = True

    for dkey in data_dict.keys():
        hpn_to_change = data_dict[dkey][0][0]
        rev_to_change = data_dict[dkey][0][1]
        if rev_to_change[:4] == 'LAST':
            rev_to_change = cm_revisions.get_last_revision(hpn_to_change, session)[0][0]
        part_rec = session.query(Parts).filter((Parts.hpn == hpn_to_change) &
                                               (Parts.hpn_rev == rev_to_change))
        num_part = part_rec.count()
        if num_part == 0:
            if add_new_part:
                part = Parts()
            else:
                print("Error: ", dkey, " does not exist and add_new_part not enabled.")
                part = None
        elif num_part == 1:
            if add_new_part:
                print("Error: ", dkey, "exists and add_new_part is enabled.")
                part = None
            else:
                part = part_rec.first()
        else:
            print("Error:  more than one of ", dkey, " exists (which should not happen).")
            part = None
        if part:
            for d in data_dict[dkey]:
                try:
                    setattr(part, d[2], d[3])
                except AttributeError:
                    print(d[2], 'does not exist as a field')
                    continue
            session.add(part)
            session.commit()
    cm_utils._log('part_connect part update', data_dict=data_dict)
    if close_session_when_done:
        session.close()

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
    if request is None:
        return None

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


def __get_part_revisions(hpn, session=None):
    """
    Retrieves revision numbers for a given part (exact match).

    Parameters:
    -------------
    hpn:  string for hera part number
    session:  db session to use
    """

    if hpn is None:
        return None
    close_session_when_done = False
    if session is None:
        db = mc.connect_mc_db()
        session = db.sessionmaker()
        close_session_when_done = True

    revisions = {}
    for parts_rec in session.query(Parts).filter(Parts.hpn == hpn):
        parts_rec.gps2Time()
        revisions[parts_rec.hpn_rev] = {}
        revisions[parts_rec.hpn_rev]['hpn'] = hpn  # Just carry this along
        revisions[parts_rec.hpn_rev]['started'] = parts_rec.start_date
        revisions[parts_rec.hpn_rev]['ended'] = parts_rec.stop_date
    if close_session_when_done:
        session.close()

    return revisions


class PartInfo(MCDeclarativeBase):
    """A table for logging test information etc for parts."""

    __tablename__ = 'part_info'

    hpn = Column(String(64), nullable=False, primary_key=True)
    "A HERA part number for each part; intend to QRcode with this string."

    hpn_rev = Column(String(32), nullable=False, primary_key=True)
    "HERA part revision number for each part; if sequencing same part number."

    posting_gpstime = NotNull(BigInteger, primary_key=True)
    "time that the data are posted"

    comment = NotNull(String(2048))
    "Comment associated with this data - or the data itself..."

    library_file = Column(String(256))
    "Name of datafile held in library"

    def __repr__(self):
        return '<heraPartNumber id = {self.hpn} comment = {self.comment}>'.format(self=self)

    def gps2Time():
        self.posting_date = Time(self.posting_gpstime, format='gps')

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

    upstream_output_port = NotNull(String(64), primary_key=True)
    "connected output port on upstream (skyward) part"

    downstream_part = Column(String(64), nullable=False, primary_key=True)
    "down refers to the part that is further from the sky, e.g. "

    down_part_rev = Column(String(64), nullable=False, primary_key=True)
    "down refers to the part that is further from the sky, e.g. "

    downstream_input_port = NotNull(String(64), primary_key=True)
    "connected input port on downstream (further from the sky) part"

    __table_args__ = (ForeignKeyConstraint(['upstream_part', 'up_part_rev'],
                                           ['parts_paper.hpn', 'parts_paper.hpn_rev']),
                      ForeignKeyConstraint(['downstream_part', 'down_part_rev'],
                                           ['parts_paper.hpn', 'parts_paper.hpn_rev']))

    start_gpstime = NotNull(BigInteger, primary_key=True)
    "start_time is the time that the connection is set"

    stop_gpstime = Column(BigInteger)
    "stop_time is the time that the connection is removed"

    def __repr__(self):
        up = '{self.upstream_part}:{self.up_part_rev}'.format(self=self)
        down = '{self.downstream_part}:{self.down_part_rev}'.format(self=self)
        return '<{}<{self.upstream_output_port}|{self.downstream_input_port}>{}>'.format(up, down, self=self)

    def gps2Time(self):
        """
        Adds gps seconds to Time.
        """
        self.start_date = Time(self.start_gpstime, format='gps')
        if self.stop_gpstime is None:
            self.stop_date = None
        else:
            self.stop_date = Time(self.stop_gpstime, format='gps')

    def connection(self, **kwargs):
        """
        Allows arbitrary connection to be specified.
        """
        for key, value in kwargs.items():
            if type(value) == str:
                if key in upper_case:
                    value = value.upper()
                elif key in lower_case:
                    value = value.lower()
            setattr(self, key, value)


def stop_existing_connections(session, h, conn_list, at_date, actually_do_it):
    """
    This adds stop times to the previous connections in conn_list

    Parameters:
    -------------
    session:  db session to use
    h:  part handling object
    conn_list:  list containing parts to stop
    at_date:  date to stop
    actually_do_it:  boolean to actually stop the part
    """

    stop_at = int(at_date.gps)
    data = []

    for conn in conn_list:
        CD = h.get_connection_dossier(conn[0], conn[1], conn[2], at_date, True)
        ck = get_connection_key(CD, conn)
        if ck is not None:
            x = CD[ck]
            print("Stopping connection {} at {}".format(x, str(at_date)))
            stopping = [x.upstream_part, x.up_part_rev, x.downstream_part, x.down_part_rev,
                        x.upstream_output_port, x.downstream_input_port, x.start_gpstime, 'stop_gpstime', stop_at]
            data.append(stopping)

    if actually_do_it:
        update_connection(session, data, False)
    else:
        print("--Here's what would happen if you set the --actually_do_it flag:")
        for d in data:
            print('\t' + str(d))


def get_connection_key(c, p):
    """
    Returns the key to use

    Parameters:
    ------------
    c:  connection_dossier dictionary
    p:  connection to find
    """

    for ck in c.keys():
        if p[0] in ck:
            break
    else:
        ck = None
    return ck


def add_new_connections(session, c, conn_list, at_date, actually_do_it):
    """
    This generates a connection object to send to the updater for a new connection

    Parameters:
    -------------
    session:  db session to use
    c:  connection handling object
    conn_list:  list containing parts to stop
    at_date:  date to stop
    actually_do_it:  boolean to actually stop the part
    """
    start_at = int(at_date.gps)
    data = []

    for conn in conn_list:
        c.connection(upstream_part=conn[0], up_part_rev=conn[1],
                     downstream_part=conn[3], down_part_rev=conn[4],
                     upstream_output_port=conn[2], downstream_input_port=conn[5],
                     start_gpstime=start_at, stop_gpstime=None)
        print("Starting connection {} at {}".format(c, str(at_date)))
        data.append([c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                     c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
                     'upstream_part', c.upstream_part])
        data.append([c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                     c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
                     'up_part_rev', c.up_part_rev])
        data.append([c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                     c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
                     'downstream_part', c.downstream_part])
        data.append([c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                     c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
                     'down_part_rev', c.down_part_rev])
        data.append([c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                     c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
                     'upstream_output_port', c.upstream_output_port])
        data.append([c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                     c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
                     'downstream_input_port', c.downstream_input_port])
        data.append([c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                     c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
                     'start_gpstime', c.start_gpstime])

    if actually_do_it:
        update_connection(session, data, True)
    else:
        print("--Here's what would happen if you set the --actually_do_it flag:")
        for d in data:
            print('\t' + str(d))


def update_connection(session=None, data=None, add_new_connection=False):
    """
    update the database given a connection with columns/values.
    adds if add_new_connection flag is true

    Parameters:
    ------------
    session:  db session to use
    data:  data for connection:
        columnN:  column name(s)
        values:  corresponding list of values
    add_new_connection:  boolean to actually allow it to be updated
    """

    data_dict = format_check_update_connection_request(data)
    if data_dict is None:
        print('Error: invalid update')
        return False

    close_session_when_done = False
    if session is None:
        db = mc.connect_mc_db()
        session = db.sessionmaker()
        close_session_when_done = True

    for dkey in data_dict.keys():
        upcn_to_change = data_dict[dkey][0][0]
        urev_to_change = data_dict[dkey][0][1]
        dncn_to_change = data_dict[dkey][0][2]
        drev_to_change = data_dict[dkey][0][3]
        boup_to_change = data_dict[dkey][0][4]
        aodn_to_change = data_dict[dkey][0][5]
        strt_to_change = data_dict[dkey][0][6]
        if urev_to_change[:4] == 'LAST':
            urev_to_change = cm_revisions.get_last_revision(upcn_to_change, session)[0][0]
        if drev_to_change[:4] == 'LAST':
            drev_to_change = cm_revisions.get_last_revision(dncn_to_change, session)[0][0]
        conn_rec = session.query(Connections).filter((Connections.upstream_part == upcn_to_change) &
                                                     (Connections.up_part_rev == urev_to_change) &
                                                     (Connections.downstream_part == dncn_to_change) &
                                                     (Connections.down_part_rev == drev_to_change) &
                                                     (Connections.upstream_output_port == boup_to_change) &
                                                     (Connections.downstream_input_port == aodn_to_change) &
                                                     (Connections.start_gpstime == strt_to_change))
        num_conn = conn_rec.count()
        if num_conn == 0:
            if add_new_connection:
                connection = Connections()
                connection.connection(up=upcn_to_change, up_rev=urev_to_change,
                                      down=dncn_to_change, down_rev=drev_to_change,
                                      upstream_output_port=boup_to_change, downstream_input_port=aodn_to_change,
                                      start_gpstime=strt_to_change)
            else:
                print("Error:", dkey, "does not exist and add_new_connection is not enabled.")
                connection = None
        elif num_conn == 1:
            if add_new_connection:
                print("Error:", dkey, "exists and and_new_connection is enabled")
                connection = None
            else:
                connection = conn_rec.first()
        else:
            print("Error:  more than one of ", dkey, " exists (which should not happen).")
            connection = None
        if connection:
            for d in data_dict[dkey]:
                try:
                    setattr(connection, d[7], d[8])
                except AttributeError:
                    print(dkey, 'does not exist as a field')
                    continue
            session.add(connection)
            session.commit()
    cm_utils._log('part_connect connection update', data_dict=data_dict)
    if close_session_when_done:
        session.close()

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

    if request is None:
        return None
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
