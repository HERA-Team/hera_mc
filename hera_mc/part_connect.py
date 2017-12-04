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

from sqlalchemy import BigInteger, Column, Float, ForeignKey, ForeignKeyConstraint, Integer, String, Text, func
#from sqlalchemy.dialects.postgresql import ARRAY

from . import MCDeclarativeBase, NotNull

from hera_mc import mc, cm_utils

no_connection_designator = '-X-'
# This lists the fully complete signal paths
full_connection_path = {'parts_paper': ['station', 'antenna', 'feed', 'front-end', 'cable-feed75', 'cable-post-amp(in)',
                                        'post-amp', 'cable-post-amp(out)', 'cable-receiverator', 'cable-container', 'f-engine'],
                        'parts_test': ['vapor']
                        }
both_pols = ['e', 'n']


class Parts(MCDeclarativeBase):
    """
    A table logging parts within the HERA system
    Stations will be considered parts of type='station'
    Note that ideally install_date would also be a primary key, but that
    screws up ForeignKey in connections

    hpn: HERA part number for each part; intend to QRcode with this string.
         Part of the primary key.
    hpn_rev: A revision letter of sequences of hpn - starts with A. . Part of the primary_key
    hptype: A part-dependent string, i.e. feed, frontend, ...
        This is also uniquely encoded in the hera part number
        (see PARTS.md) -- this could be derived from it but this removes that constraint.
    manufacturer_number: A part number/serial number as specified by manufacturer
    start_gpstime: The date when the part was installed (or otherwise assigned by project).
    stop_gpstime: The date when the part was removed (or otherwise de-assigned by project).
    """
    __tablename__ = 'parts_paper'

    hpn = Column(String(64), primary_key=True)
    hpn_rev = Column(String(32), primary_key=True)
    hptype = NotNull(String(64))
    manufacturer_number = Column(String(64))
    start_gpstime = Column(BigInteger, nullable=False)
    stop_gpstime = Column(BigInteger)

    def __repr__(self):
        return ('<heraPartNumber id={self.hpn}{self.hpn_rev} type={self.hptype}>'
                .format(self=self))

    def gps2Time(self):
        """
        Make astropy.Time object from gps
        """

        self.start_date = Time(self.start_gpstime, format='gps')
        if self.stop_gpstime is None:
            self.stop_date = None
        else:
            self.stop_date = Time(self.stop_gpstime, format='gps')

    def part(self, **kwargs):
        """
        Allows one to specify an arbitrary part.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)


def stop_existing_parts(session, hpnr_list, at_date, actually_do_it):
    """
    This adds stop times to the previous parts.

    Parameters:
    ------------
    session:  db session to use
    hpnr_list:  list of lists containing hpn and revision number
    at_date:  date to use for stopping
    actually_do_it:  boolean to allow the part to be stopped
    """

    stop_at = int(at_date.gps)
    data = []

    for hpnr in hpnr_list:
        print("Stopping part {}:{} at {}".format(hpnr[0], hpnr[1], str(at_date)))
        data.append([hpnr[0], hpnr[1], 'stop_gpstime', stop_at])

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
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    for dkey, dval in data_dict.iteritems():
        hpn_to_change = dval[0][0]
        rev_to_change = dval[0][1]
        # if rev_to_change[:4] == 'LAST':
        #    rev_to_change = cm_revisions.get_last_revision(hpn_to_change, session)[0][0]
        part_rec = session.query(Parts).filter((func.upper(Parts.hpn) == hpn_to_change.upper()) &
                                               (func.upper(Parts.hpn_rev) == rev_to_change.upper()))
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
            for d in dval:
                try:
                    setattr(part, d[2], d[3])
                except AttributeError:
                    print(d[2], 'does not exist as a field')
                    continue
            session.add(part)
            session.commit()
    cm_utils.log('part_connect part update', data_dict=data_dict)
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
        revN:  hera part revision number, if absent, propagate first, which, if
                    absent, defaults to 'last'
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
        dkey = d[0] + ':' + d[1]
        if dkey in data.keys():
            data[dkey].append(d)
        else:
            data[dkey] = [d]
    return data


def get_part_revisions(hpn, session=None):
    """
    Retrieves revision numbers for a given part (exact match).

    Parameters:
    -------------
    hpn:  string for hera part number
    session:  db session to use
    """

    if hpn is None:
        return {}

    uhpn = hpn.upper()
    close_session_when_done = False
    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    revisions = {}
    for parts_rec in session.query(Parts).filter(func.upper(Parts.hpn) == uhpn):
        parts_rec.gps2Time()
        revisions[parts_rec.hpn_rev] = {}
        revisions[parts_rec.hpn_rev]['hpn'] = hpn  # Just carry this along
        revisions[parts_rec.hpn_rev]['started'] = parts_rec.start_date
        revisions[parts_rec.hpn_rev]['ended'] = parts_rec.stop_date
    if close_session_when_done:
        session.close()
    return revisions


class Dubitable(MCDeclarativeBase):
    """
    A table to track the dubitable antennas.

    start_gpstime:  start time of list
    stop_gpstime:  stop time of list
    ant_list:  list of "unapproved" antennas
    """

    __tablename__ = 'dubitable'

    start_gpstime = Column(BigInteger, primary_key=True)
    stop_gpstime = Column(BigInteger)
    ant_list = Column(Text, nullable=False)

    def __repr__(self):
        return ('<{self.start_gpstime}>'.format(self=self))
    #    return ('<{} dubitable entries>'.format(len(self.ant_list)))


def update_dubitable(session=None, transition_gpstime=None, data=None):
    """
    update the database given a new list of dubitable antennas.
    It will stop the previous list at transition_gpstime and start the new one
    at transition_gpstime + 1sec

    Parameters:
    ------------
    session:  db session to use
    transition_gpstime:  time to make the change
    data:  list of antennas
    """

    close_session_when_done = False
    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True

    last_one = session.query(Dubitable).filter(Dubitable.stop_gpstime == None)
    if last_one.count() == 1:  # Stop the previous valid list.
        old_dubi = last_one.first()
        old_dubi.stop_gpstime = transition_gpstime
        session.add(old_dubi)
    elif last_one.count() > 1:
        raise ValueError('Too many open dubitable lists.')

    new_dubi = Dubitable()
    new_dubi.start_gpstime = transition_gpstime + 1
    new_dubi.ant_list = ''
    for a in data:
        new_dubi.ant_list += (str(a) + ',')
    new_dubi.ant_list = new_dubi.ant_list.strip(',')
    session.add(new_dubi)
    session.commit()
    data_dict = {'transition_gpstime': transition_gpstime}
    data_dict = {'ant_list:len': [len(data)]}
    cm_utils.log('part_connect dubitable update', data_dict=data_dict)

    if close_session_when_done:
        session.close()


class PartInfo(MCDeclarativeBase):
    """
    A table for logging test information etc for parts.

    hpn: A HERA part number for each part; intend to QRcode with this string.
        Part of the primary_key
    hpn_rev: HERA part revision number for each part; if sequencing same part number.
        Part of the primary_key
    posting_gpstime: time that the data are posted
        Part of the primary_key
    comment: Comment associated with this data - or the data itself...
    library_file: Name of datafile held in library
    """

    __tablename__ = 'part_info'

    hpn = Column(String(64), nullable=False, primary_key=True)
    hpn_rev = Column(String(32), nullable=False, primary_key=True)
    posting_gpstime = NotNull(BigInteger, primary_key=True)
    comment = NotNull(String(2048))
    library_file = Column(String(256))

    def __repr__(self):
        return '<heraPartNumber id = {self.hpn} comment = {self.comment}>'.format(self=self)

    def gps2Time():
        self.posting_date = Time(self.posting_gpstime, format='gps')

    def info(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def add_part_info(session, hpn, rev, at_date, comment, library_file=None):
    """
    Add part information into database.
    """
    close_session_when_done = False
    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
        close_session_when_done = True
    part_rec = session.query(Parts).filter((func.upper(Parts.hpn) == hpn.upper()) &
                                           (func.upper(Parts.hpn_rev) == rev.upper()))
    if not part_rec.count():
        print("FYI - {}:{} does not exist in parts database.".format(hpn, rev))
        print("This is not a requirement, but you might want to consider adding it.")

    pi = PartInfo()
    pi.hpn = hpn
    pi.hpn_rev = rev
    pi.posting_gpstime = cm_utils.get_astropytime(at_date).gps
    pi.comment = comment
    pi.library_file = library_file
    session.add(pi)
    session.commit()
    if close_session_when_done:
        session.close()


class Connections(MCDeclarativeBase):
    """
    A table for logging connections between parts.
    Part and Port must be unique when combined

    upstream_part: up refers to the skyward part,
        e.g. frontend:cable, 'A' is the frontend, 'B' is the cable.
        Signal flows from A->B"
        Part of the primary_key, Foreign Key into parts_paper
    up_part_rev: up refers to the skyward part revision number.
        Part of the primary_key, Foreign Key into parts_paper
    upstream_output_port: connected output port on upstream (skyward) part.
        Part of the primary_key
    downstream_part: down refers to the part that is further from the sky, e.g.
        Part of the primary_key, Foreign Key into parts_paper
    down_part_rev: down refers to the part that is further from the sky, e.g.
        Part of the primary_key, Foreign Key into parts_paper
    downstream_input_port: connected input port on downstream (further from the sky) part
        Part of the primary_key
    start_gpstime: start_time is the time that the connection is set
        Part of the primary_key
    stop_gpstime: stop_time is the time that the connection is removed

    """
    __tablename__ = 'connections'

    upstream_part = Column(String(64), nullable=False, primary_key=True)
    up_part_rev = Column(String(32), nullable=False, primary_key=True)
    upstream_output_port = NotNull(String(64), primary_key=True)
    downstream_part = Column(String(64), nullable=False, primary_key=True)
    down_part_rev = Column(String(64), nullable=False, primary_key=True)
    downstream_input_port = NotNull(String(64), primary_key=True)

    __table_args__ = (ForeignKeyConstraint(['upstream_part', 'up_part_rev'],
                                           ['parts_paper.hpn', 'parts_paper.hpn_rev']),
                      ForeignKeyConstraint(['downstream_part', 'down_part_rev'],
                                           ['parts_paper.hpn', 'parts_paper.hpn_rev']))

    start_gpstime = NotNull(BigInteger, primary_key=True)
    stop_gpstime = Column(BigInteger)

    def __repr__(self):
        up = '{self.upstream_part}:{self.up_part_rev}'.format(self=self)
        down = '{self.downstream_part}:{self.down_part_rev}'.format(self=self)
        return ('<{}<{self.upstream_output_port}|{self.downstream_input_port}>{}>'
                .format(up, down, self=self))

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
            setattr(self, key, value)


def get_null_connection():
    nc = no_connection_designator
    no_connect = Connections()
    no_connect.connection(upstream_part=nc, up_part_rev=nc, upstream_output_port=nc,
                          downstream_part=nc, down_part_rev=nc, downstream_input_port=nc,
                          start_gpstime=nc)
    return no_connect


def stop_existing_connections_to_part(session, h, conn_list, at_date, actually_do_it):
    """
    This adds stop times to the connections for parts listed in conn_list.  Use this method with
    caution, as it currently doesn't include much checking.  You probably should use the much
    more specific stop_connections method below.  It is being kept around for possible use in
    future scripts that "remove" replaced parts.

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
        CD = h.get_connection_dossier([conn[0]], conn[1], conn[2], at_date, True)
        ck = get_connection_key(CD, conn)
        if ck is None:
            print('There are no connections to stop')
        else:
            x = CD['connections'][ck]
            print("Stopping connection {} at {}".format(x, str(at_date)))
            stopping = [x.upstream_part, x.up_part_rev, x.downstream_part,
                        x.down_part_rev, x.upstream_output_port,
                        x.downstream_input_port, x.start_gpstime,
                        'stop_gpstime', stop_at]
            data.append(stopping)

    if actually_do_it:
        update_connection(session, data, False)
    else:
        print("--Here's what would happen if you set the --actually_do_it flag:")
        for d in data:
            print('\t' + str(d))


def get_connection_key(c, p):
    """
    Returns the key to use:  this is to make sure edge cases don't trip you up.

    Parameters:
    ------------
    c:  connection_dossier dictionary
    p:  connection to find
    """

    p = [p[0].upper(), p[1].upper(), p[2].upper()]
    ctr = 0
    return_key = None
    for ckey, cval in c['connections'].iteritems():
        ca = (cval.upstream_part.upper(), cval.downstream_part.upper())
        cr = (cval.up_part_rev.upper(), cval.down_part_rev.upper())
        co = (cval.upstream_output_port.upper(), cval.downstream_input_port.upper())
        if cval.stop_gpstime is None and p[0] in ca and p[1] in cr and p[2] in co:
            ctr += 1
            return_key = ckey
    if ctr > 1:
        print("Warning:  too many connections were found.  Returning None")
        return_key = None
    return return_key


def stop_connections(session, conn_list, at_date, actually_do_it):
    """
    This adds a stop_date to the connections in conn_list

    Parameters:
    -------------
    Session:  db session to use
    conn_list:  list of lists with data [[upstream_part,rev,port,downstream_part,rev,port,start_gpstime],...]
    at_date:  date to stop connection
    actually_do_it:  boolean to actually stop the part
    """
    stop_at = int(at_date.gps)
    data = []
    for conn in conn_list:
        print("Stopping connection {}:{}<{} - {}>{}:{} at {}".format(conn[0], conn[1], conn[4],
                                                                     conn[2], conn[3], conn[5], str(at_date)))
        this_one = []
        for cc in conn:
            this_one.append(cc)
        this_one.append('stop_gpstime')
        this_one.append(stop_at)
        data.append(this_one)

    if actually_do_it:
        update_connection(session, data, False)
    else:
        print("--Here's what would happen if you set the --actually_do_it flag:")
        for d in data:
            print('\t' + str(d))


def add_new_connections(session, c, conn_list, at_date, actually_do_it):
    """
    This uses a connection object to send data to the update_connection method to make a new connection

    Parameters:
    -------------
    session:  db session to use
    c:  connection handling object
    conn_list:  list containing parts to stop
    at_date:  date to stop
    actually_do_it:  boolean to actually add the part
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
        db = mc.connect_to_mc_db(None)
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
        conn_rec = session.query(Connections).filter(
            (Connections.upstream_part == upcn_to_change) &
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
                connection.connection(up=upcn_to_change,
                                      up_rev=urev_to_change,
                                      down=dncn_to_change,
                                      down_rev=drev_to_change,
                                      upstream_output_port=boup_to_change,
                                      downstream_input_port=aodn_to_change,
                                      start_gpstime=strt_to_change)
            else:
                print("Error:", dkey, "does not exist and add_new_connection is "
                      "not enabled.")
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
    cm_utils.log('part_connect connection update', data_dict=data_dict)
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
        if dkey in data.keys():
            data[dkey].append(d)
        else:
            data[dkey] = [d]
    return data

###
