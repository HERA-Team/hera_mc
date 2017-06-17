# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Keeping track of geo-located stations.

"""

from __future__ import absolute_import, division, print_function

import os
import socket
import sys
import copy
from astropy.time import Time

from sqlalchemy import Column, Float, Integer, String, BigInteger, ForeignKey, func

from . import MCDeclarativeBase, NotNull
from hera_mc import mc, part_connect, cm_utils


class StationType(MCDeclarativeBase):
    """
    A table to track/denote station type data categories in various ways
    """
    __tablename__ = 'station_type'

    station_type_name = Column(String(64), primary_key=True)
    "Name of type class.  Note that prefix is the primary_key, so there can be multiple prefixes/type_name"

    prefix = NotNull(String(64))
    "String prefix to station type, elements of which are typically characterized by <prefix><int>. \
     Comma-delimit list if more than one."

    description = Column(String(64))
    "Short description of station type."

    plot_marker = Column(String(64))
    "matplotlib marker type to use"

    def __repr__(self):
        return '<subarray prefix={self.prefix} description={self.description} marker={self.plot_marker}>'.format(self=self)


class GeoLocation(MCDeclarativeBase):
    """A table logging stations within HERA.
    """
    __tablename__ = 'geo_location'

    station_name = Column(String(64), primary_key=True)
    "Colloquial name of station (which is a unique location on the ground).  This one shouldn't \
     change. This is the primary key, so precision matters."

    station_type_name = Column(String(64), ForeignKey(StationType.station_type_name), nullable=False)
    "Name of station type of which it is a member.  Should match prefix per station_type table."

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

    created_gpstime = NotNull(BigInteger)
    "The date when the station assigned by project."

    def gps2Time(self):
        self.created_date = Time(self.created_gpstime,format='gps')

    def geo(self, **kwargs):
        for key, value in kwargs.items():
            if key == 'station_name':
                value = value.upper()
            setattr(self, key, value)

    def __repr__(self):
        return '<station_name={self.station_name} station_type={self.station_type_name} \
        northing={self.northing} easting={self.easting} \
        elevation={self.elevation}>'.format(self=self)


def update(args, data):
    """
    update the database given a station_name and station_number with columns/values and provides some checking
    use with caution -- should usually use in a script which will do datetime primary key etc

    Parameters:
    ------------
    data:  [[station_name0,column0,value0],[...]]
    station_nameN:  station_name (starts with char)
    values:  corresponding list of values
    """

    data_dict = format_check_update_request(data)
    if data_dict is None:
        print('Error: invalid update')
        return False
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for station_name in data_dict.keys():
            geo_rec = session.query(GeoLocation).filter(GeoLocation.station_name == station_name)
            ngr = geo_rec.count()
            if ngr == 0:
                if args.add_new_geo:
                    gr = GeoLocation()
                else:
                    print("Error: ", station_name, "does not exist and add_new_geo not enabled.")
                    gr = None
            elif ngr == 1:
                if args.add_new_geo:
                    print("Error: ", station_name, "exists and and_new_geo is not enabled.")
                    gr = None
                else:
                    gr = geo_rec.first()
            else:
                print("Shouldn't ever get here.")
                gr = None
            if gr:
                for d in data_dict[station_name]:
                    try:
                        setattr(gr, d[1], d[2])
                    except AttributeError:
                        print(d[1], 'does not exist as a field')
                        continue
                session.add(gr)
    cm_utils._log('geo_location update', data_dict=data_dict)
    return True


def format_check_update_request(request):
    """
    parses the update request

    return dictionary

    Parameters:
    ------------
    request:  station_name0:column0:value0, [station_name1:]column1:value1, [...] or list
    station_nameN: first entry must have the station_name, 
                   if it does not then propagate first station_name but can't restart 3 then 2
    columnN:  name of geo_location column
    valueN:  corresponding new value
    """
    data = {}
    if type(request) == str:
        tmp = request.split(',')
        data_to_proc = []
        for d in tmp:
            data_to_proc.append(d.split(':'))
    else:
        data_to_proc = request
    if len(data_to_proc[0]) == 3:
        station_name0 = data_to_proc[0][0].upper()
        for d in data_to_proc:
            if len(d) == 3:
                pass
            elif len(d) == 2:
                d.insert(0, station_name0)
            else:
                print('Invalid format for update request.')
                continue
            if d[1] == 'station_name':
                d[2] = d[2].upper()
            if d[0] in data.keys():
                data[d[0]].append(d)
            else:
                data[d[0]] = [d]
    else:
        print('Invalid parse request - need 3 parameters for at least first one.')
        data = None
    return data


def is_in_geo_location(args, station_name):
    """
    checks to see if a station_name is in the geo_location database

    return True/False

    Parameters:
    ------------
    args:  needed arguments to open the database
    station_name:  string name of station
    """

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        station = session.query(GeoLocation).filter(GeoLocation.station_name == station_name)
        if station.count() > 0:
            station_present = True
        else:
            station_present = False
    return station_present


def is_in_connections(args, station_name, check_if_active=False):
    """
    checks to see if the station_name is in the connections database (which means it is also in parts)

    return True/False unless check_if_active flag is set, when it returns the antenna number at that location

    Parameters:
    ------------
    args:  needed arguments to open database and set date/time
    station_name:  string name of station
    check_if_active:  either False to not check/care if active, or astropy Time to check
    """

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        connected_station = session.query(part_connect.Connections).filter(part_connect.Connections.upstream_part == station_name)
        if connected_station.count() > 0:
            station_connected = True
        else:
            station_connected = False
        if station_connected and check_if_active:
            counter = 0
            for connection in connected_station.all():
                connection.gps2Time()
                if cm_utils._is_active(check_if_active, connection.start_date, connection.stop_date):
                    station_connected = connection.downstream_part+':'+connection.down_part_rev
                    counter += 1
                else:
                    station_connected = False
            if counter > 1:
                print("Error:  more than one active connection for", station_name)
                station_connected = False
    return station_connected
