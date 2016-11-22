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
import hera_mc.mc as mc

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
    """A table logging parts within the HERA system
       MAKE Part and Port be unique when combined
    """
    __tablename__ = 'geo_location'

    station_name = Column(String(64), primary_key=True)
    "Colloquial name of station (which is a unique location on the ground).  This one shouldn't \
     change. This is the primary key, so precision matters."

    meta_class_name = Column(String(64), ForeignKey(StationMeta.meta_class_name), nullable=False)
    "Name of meta-class of which it is a member.  Should match prefix per station_meta table."

    station_number = NotNull(Integer)
    "Unique station number that the correlator and MIRIAD want.  Currently set to numbers as of \
     16/10/26.  This will be superseded by future version."

    station_number_start_date = Column(DateTime,primary_key=True)
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
    update the database given a station_name/_number with columns/values
    use with caution -- should usually use in a script which will do datetime primary key etc

    Parameters:
    ------------
    data:  [[station0,column0,value0],[...]]
    stationN:  may be station_name (starts with char) or station_number (is an int)
    values:  corresponding list of values
    """
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for d in data:
            station, station_col = station_name_or_number(d[0])
            for geo_rec in session.query(GeoLocation).filter(station_col == station):
                try:
                    if not args.add_new_geo:  # Flag to allow adding a new record
                        xxx = getattr(geo_rec, d[1])
                    setattr(geo_rec, d[1], d[2])
                except AttributeError:
                    print(d[1], 'does not exist')


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


def parse_update_request(request):
    """
    parses the update request

    return nested list

    Parameters:
    ------------
    request:  station0:column0:value0, [station1:]column1:value1, [...]
    stationN:  station_name or station_number, first entry must have one, if absent propagate first
    columnN:  name of geo_location column
    valueN:  corresponding new value
    """
    data = []
    data_to_proc = request.split(', ')
    station0 = data_to_proc[0].split(':')[0]
    for d in data_to_proc:
        scv = d.split(':')
        if len(scv) == 3:
            pass
        elif len(scv) == 2:
            scv.insert(0, station0)
        data.append(scv)
    return data


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
            v = {'easting': a.easting, 'northing': a.northing, 'elevation': a.elevation,
                 'station_name': a.station_name, 'station_number': a.station_number,
                 'station_type': this_station}
            if show_geo:
                if args.verbosity == 'm' or args.verbosity == 'h':
                    print('station_name: ', a.station_name)
                    print('\tstation_number: ', a.station_number)
                    print('\teasting: ', a.easting)
                    print('\tnorthing: ', a.northing)
                    print('\televation: ', a.elevation)
                    print('\tstation description (%s):  %s' % (this_station,
                                                               station_meta[this_station]['Description']))
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
                    pt = {'easting': a.easting, 'northing': a.northing,
                          'elevation': a.elevation}
                    plt.plot(pt[coord[args.xgraph]], pt[coord[args.ygraph]],
                             station_meta[key]['Marker'], label=a.station_name)
                    if label_station:
                        plt.annotate(a.station_number, xy=(pt[coord[args.xgraph]], pt[coord[args.ygraph]]),
                                     xytext=(pt[coord[args.xgraph]] + 5, pt[coord[args.ygraph]]))
    if overplot:
        overplot_station = plt.plot(overplot[coord[args.xgraph]], overplot[coord[args.ygraph]],
                                    'ys', markersize=10)
        legendEntries = [overplot_station]
        legendText = [overplot['station_name'] + ':' + str(overplot['station_number'])]
        plt.legend((overplot_station), (legendText), numpoints=1, loc='upper right')
    if args.xgraph != 'Z' and args.ygraph != 'Z':
        plt.axis('equal')
    plt.plot(xaxis=args.xgraph, yaxis=args.ygraph)
    plt.show()



