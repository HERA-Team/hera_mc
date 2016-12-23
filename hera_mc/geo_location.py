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

from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey, func

from . import MCDeclarativeBase, NotNull
from hera_mc import mc, part_connect, cm_utils


class StationMeta(MCDeclarativeBase):
    """
    A table to track/denote station metadata categories in various ways
    """
    __tablename__ = 'station_meta'

    meta_class_name = Column(String(64), primary_key=True)
    "Name of meta class.  Note that prefix is the primary_key, so there can be multiple prefixes/meta_name"

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

    meta_class_name = Column(String(64), ForeignKey(StationMeta.meta_class_name), nullable=False)
    "Name of meta-class of which it is a member.  Should match prefix per station_meta table."

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

    created_date = NotNull(DateTime)
    "The date when the station assigned by project."

    def __repr__(self):
        return '<station_name={self.station_name} station_number={self.station_number} \
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
                    print("Error: ",station_name,"does not exist and add_new_geo not enabled.")
                    gr = None
            elif ngr == 1:
                if args.add_new_geo:
                    print("Error: ",station_name,"exists and and_new_geo is not enabled.")
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
    return True

def format_check_update_request(request):
    """
    parses the update request

    return dictionary

    Parameters:
    ------------
    request:  station_name0:column0:value0, [station_name1:]column1:value1, [...] or list
    station_nameN: first entry must have the station_name, 
                   if it does not then propagate first station_name but can't restart 3 values
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
    if len(data_to_proc[0])==3:
        station_name0 = data_to_proc[0][0]
        for d in data_to_proc:
            if len(d) == 3:
                pass
            elif len(d) == 2:
                d.insert(0, station_name0)
            else:
                print('Invalid format for update request.')
                continue
            if d[0] in data.keys():
                data[d[0]].append(d)
            else:
                data[d[0]] = [d]
    else:
        print('Invalid parse request - need 3 parameters for at least first one.')
        data = None
    return data

def is_station_present(args,station_name):
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

def is_in_connections_db(args,station_name,check_if_active=False):
    """
    checks to see if the station_name is in the connections database (which means it is also in parts)

    return True/False unless check_if_active flag is set, when it returns the antenna number at that location

    Parameters:
    ------------
    args:  needed arguments to open database and set date/time
    station_name:  string name of station
    check_if_active:  boolean flag to check if active
    """

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        connected_station = session.query(part_connect.Connections).filter(part_connect.Connections.up == station_name)
        if connected_station.count() > 0:
            station_connected = True
        else:
            station_connected = False
        if station_connected and check_if_active:
            counter = 0
            current = cm_utils._get_datetime(args.date,args.time)
            for connection in connected_station.all():
                stop_date = cm_utils._get_stopdate(connection.stop_date)
                if current>connection.start_date and current<stop_date:
                    station_connected = int(connection.down.strip('A'))
                    counter+=1
                else:
                    station_connected = False
            if counter>1:
                print("Error:  more than one active connection for",station_name)
                station_connected = False
    return station_connected

def find_station_name(args,antenna):
    """
    checks to see what station an antenna is at

    Returns False or the active station_name (must be an active station)

    Parameters:
    ------------
    args:  needed arguments to open database and set date/time
    antenna_number:  antenna number as float or string, if needed, it adds the 'A'
    """

    if type(antenna) == float or antenna[0]!='A':
        antenna = 'A'+str(antenna).strip('0')
    if antenna[1]=='0':
        print("Error:  the antenna part number should not have leading 0's",antenna)
        return False
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        connected_antenna = session.query(part_connect.Connections).filter(part_connect.Connections.down == antenna)
        if connected_antenna.count() > 0:
            antenna_connected = True
        else:
            antenna_connected = False
        if antenna_connected:
            counter = 0
            current = cm_utils._get_datetime(args.date,args.time)
            for connection in connected_antenna.all():
                stop_date = cm_utils._get_stopdate(connection.stop_date)
                if current>connection.start_date and current<stop_date:
                    antenna_connected = connection.up
                    counter+=1
                else:
                    antenna_connected = False
            if counter>1:
                print("Error:  more than one active connection for",antenna)
                antenna_connected = False
    return antenna_connected

def locate_station(args, show_geo=False):
    """Return the location of station_name or station_number as contained in args.locate.
       If sub_array data exists, print subarray name."""

    station_name = False
    try:
        station = int(args.locate)
        station_name = find_station_name(args,station)
    except ValueError:
        station_name = args.locate.upper()
    v = None
    if station_name:
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            station_meta = session.get_station_meta()
            for a in session.query(GeoLocation).filter(GeoLocation.station_name == station_name):
                for key in station_meta.keys():
                    if a.station_name in station_meta[key]['Stations']:
                        this_station = key
                        break
                    else:
                        this_station = 'No station metadata.'
                ever_connected = is_in_connections_db(args,a.station_name) 
                active = is_in_connections_db(args,a.station_name,True)
                v = {'easting': a.easting, 'northing': a.northing, 'elevation': a.elevation,
                     'station_name': a.station_name, 'antenna_number':active, 'station_type': this_station, 
                     'connected':ever_connected, 'active':active, 'created_date':a.created_date}
                if show_geo:
                    if args.verbosity == 'm' or args.verbosity == 'h':
                        print('station_name: ', a.station_name)
                        print('\teasting: ', a.easting)
                        print('\tnorthing: ', a.northing)
                        print('\televation: ', a.elevation)
                        print('\tstation description (%s):  %s' % 
                            (this_station,station_meta[this_station]['Description']))
                        print('\tever connected:  ',ever_connected)
                        print('\tactive:  ',active)
                        print('\tcreated:  ',a.created_date)
                    elif args.verbosity == 'l':
                        print(a, this_station)
    if show_geo:
        if not v and args.verbosity == 'm' or args.verbosity == 'h':
            print(args.locate, ' not found.')
    return v

def plot_arrays(args, overplot=None, label_station=False):
    """Plot the various sub-array types"""
    coord = {'E': 'easting', 'N': 'northing', 'Z': 'elevation'}
    plt.figure(args.xgraph + args.ygraph)
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        station_meta = session.get_station_meta()
        for key in station_meta.keys():
            for loc in station_meta[key]['Stations']:
                for a in session.query(GeoLocation).filter(GeoLocation.station_name == loc):
                    show_it = True
                    if args.active:
                        show_it = is_in_connections_db(args,loc,True)
                    if show_it:
                        pt = {'easting': a.easting, 'northing': a.northing,
                              'elevation': a.elevation}
                        plt.plot(pt[coord[args.xgraph]], pt[coord[args.ygraph]],
                                 station_meta[key]['Marker'], label=a.station_name)
                        if label_station:
                            if args.label_type=='station_name':
                                labeling = a.station_name
                            elif args.label_type=='antenna_number':
                                labeling = is_in_connections_db(args,loc,True)
                                if not labeling:
                                    labeling = 'NA'
                            else:
                                labeling = 'S'
                            plt.annotate(labeling, xy=(pt[coord[args.xgraph]], pt[coord[args.ygraph]]),
                                         xytext=(pt[coord[args.xgraph]] + 5, pt[coord[args.ygraph]]))
    if overplot:
        if overplot['connected'] and overplot['active']:
            over_marker = 'g*'
            mkr_lbl = 'ca'
        elif overplot['connected'] and not overplot['active']:
            over_marker = 'gx'
            mkr_lbl = 'cx'
        elif overplot['active'] and not overplot['connected']:
            over_marker = 'yx'
            mkr_lbl = 'xa'
        else:
            over_marker = 'rx'
            mkr_lbl = 'xx'
        overplot_station = plt.plot(overplot[coord[args.xgraph]], overplot[coord[args.ygraph]],
                                    over_marker, markersize=14)
        legendEntries = [overplot_station]
        legendText = [overplot['station_name'] + ':' + str(overplot['active'])]
        plt.legend((overplot_station), (legendText), numpoints=1, loc='upper right')
    if args.xgraph != 'Z' and args.ygraph != 'Z':
        plt.axis('equal')
    plt.plot(xaxis=args.xgraph, yaxis=args.ygraph)
    plt.show()



