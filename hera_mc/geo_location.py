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

    station_number = Column(Integer, primary_key=True)
    "Unique station number that the correlator and MIRIAD want.  Currently set to numbers as of \
     16/10/26.  This will be superseded by future version."

    station_number_start_date = NotNull(DateTime)
    "Date the station_number was associated to the station_name."

    station_number_stop_date = Column(DateTime)
    "Date the station_number was disassociated with the station_name"

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
        return '<station_name={self.station_name} station_number={self.station_number} \
        northing={self.northing} easting={self.easting} \
        elevation={self.elevation}>'.format(self=self)


def update(args, data):
    """
    update the database given a station_name and station_number with columns/values and provides some checking
    use with caution -- should usually use in a script which will do datetime primary key etc

    Parameters:
    ------------
    data:  [[station_name0,station_number0,column0,value0],[...]]
    station_nameN:  station_name (starts with char)
    values:  corresponding list of values
    """
    data = check_update_request(data)
    if data is None:
        print('Error: invalid update')
        return False
    station_name = data[0][0]
    station_number = data[0][1]
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        geo_rec = session.query(GeoLocation).filter( (GeoLocation.station_name == station_name) &
                                                     (GeoLocation.station_number == station_number) )
        ngr = geo_rec.count()
        if ngr == 0: 
            if args.add_new_geo:
                gr = GeoLocation()
            else:
                print(d[0],"/",d[1],"exists and add_new_geo not enabled.")
                gr = None
        elif ngr == 1:
            gr = geo_rec.first()
        else:
            print("Shouldn't ever get here.")
            gr = None

        if gr:
            for d in data:
                try:
                    setattr(gr, d[2], d[3])
                except AttributeError:
                    print(d[2], 'does not exist as a field')
                    continue
            session.add(gr)
    return True


def station_name_or_number(station):
    """
    determines if a station query is for a station_name or station_number

    return station, station_col

    Parameters:
    ------------
    station:  station to check
    """
    try:
        station = int(station)
        station_col = GeoLocation.station_number
    except ValueError:
        station = station.upper()
        station_col = GeoLocation.station_name
    return station, station_col


def check_update_request(request):
    """
    parses the update request, limited to one station_name/station_number pair, which is checked

    return nested list

    Parameters:
    ------------
    request:  station_name0:station_number0:column0:value0, [station_name1:station_number1]column1:value1, [...]
    stationN:  station_name:station_number, first entry must have the pair, 
               if it does not propagate first but can't restart 4 values
    columnN:  name of geo_location column
    valueN:  corresponding new value
    """
    data = []
    if type(request) == str:
        tmp = request.split(',')
        data_to_proc = []
        for d in tmp:
            data_to_proc.append(d.split(':'))
    else:
        data_to_proc = request
    if len(data_to_proc[0])==4:
        station_name0 = data_to_proc[0][0]
        station_number0 = data_to_proc[0][1]
        key = '%s:%d' % (station_name0,station_number0)
    else:
        print('Invalid parse request - need 4 parameters for at least first one.')
        data = None
    for d in data_to_proc:
        if len(d) == 4:
            chk = '%s:%d' % (d[0],d[1])
            if chk!=key:
                print("Error:  Request is for one name/number pair only.")
                data = None
                break
        elif len(scv) == 2:
            d.insert(0, station_name0)
            d.insert(1, station_number0)
        data.append(d)
    return data

def is_station_present(args,station_name,station_number=None):
    num_present = False
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        if station_number:
            geo_rec = session.query(GeoLocation).filter( (GeoLocation.station_name == station_name) &
                                                         (GeoLocation.station_number == station_number))
        else:
            geo_rec = session.query(GeoLocation).filter(GeoLocation.station_name == station_name)
        num_present = geo_rec.count()
    return num_present

def is_station_active(args,station_name = None, return_active_station_number = False):
    current = cm_utils._get_datetime(args.date,args.time)
    if station_name is None:
        station, station_col = station_name_or_number(args.locate)
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for a in session.query(GeoLocation).filter(station_col == station):
                station_name = a.station_name
    is_active = False
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for station_query in session.query(GeoLocation).filter(GeoLocation.station_name==station_name):
            stop_date = cm_utils._get_stopdate(station_query.station_number_stop_date)
            if current>station_query.station_number_start_date and current<stop_date:
                is_active = True
                if return_active_station_number:
                    is_active = station_query.station_number
            else:
                is_active = False
    return is_active

def is_in_connections_db(args,station_name = None):
    if station_name is None:
        station, station_col = station_name_or_number(args.locate)
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for a in session.query(GeoLocation).filter(station_col == station):
                station_name = a.station_name
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        connected_station = session.query(part_connect.Connections).filter(part_connect.Connections.up == station_name)
        if connected_station.count() > 0:
            station_connected = True
        else:
            station_connected = False
    return station_connected

def locate_station(args, show_geo=False):
    """Return the location of station_name or station_number as contained in args.locate.
       If sub_array data exists, print subarray name."""
    station, station_col = station_name_or_number(args.locate)
    v = None
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        station_meta = session.get_station_meta()
        for a in session.query(GeoLocation).filter(station_col == station):
            for key in station_meta.keys():
                if a.station_name in station_meta[key]['Stations']:
                    this_station = key
                    break
                else:
                    this_station = 'No station metadata.'
            connected = is_in_connections_db(args,a.station_name) 
            active    = is_station_active(args,a.station_name)
            v = {'easting': a.easting, 'northing': a.northing, 'elevation': a.elevation,
                 'station_name': a.station_name, 'station_number': a.station_number,
                 'station_type': this_station, 'connected':connected, 'active':active}
            if show_geo:
                if args.verbosity == 'm' or args.verbosity == 'h':
                    print('station_name: ', a.station_name)
                    print('\tstation_number: ', a.station_number)
                    print('\teasting: ', a.easting)
                    print('\tnorthing: ', a.northing)
                    print('\televation: ', a.elevation)
                    print('\tstation description (%s):  %s' % (this_station,
                                                               station_meta[this_station]['Description']))
                    print('\tever connected:  ',connected)
                    print('\tactive:  ',active)
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
                        show_it = is_station_active(args,loc)
                    if show_it:
                        pt = {'easting': a.easting, 'northing': a.northing,
                              'elevation': a.elevation}
                        plt.plot(pt[coord[args.xgraph]], pt[coord[args.ygraph]],
                                 station_meta[key]['Marker'], label=a.station_name)
                        if label_station:
                            if args.label_type=='station_name':
                                labeling = a.station_name
                            elif args.label_type=='station_number':
                                labeling = a.station_number
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
        elif overplot['acive'] and not overplot['connected']:
            over_marker = 'yx'
            mkr_lbl = 'xa'
        else:
            over_marker = 'rx'
            mkr_lbl = 'xx'
        overplot_station = plt.plot(overplot[coord[args.xgraph]], overplot[coord[args.ygraph]],
                                    over_marker, markersize=14)
        legendEntries = [overplot_station]
        legendText = [overplot['station_name'] + ':' + str(overplot['station_number']) + ':' + mkr_lbl]
        plt.legend((overplot_station), (legendText), numpoints=1, loc='upper right')
    if args.xgraph != 'Z' and args.ygraph != 'Z':
        plt.axis('equal')
    plt.plot(xaxis=args.xgraph, yaxis=args.ygraph)
    plt.show()



