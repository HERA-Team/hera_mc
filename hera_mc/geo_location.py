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

from sqlalchemy import Column, Float, Integer, String, func

from . import MCDeclarativeBase, NotNull
import hera_mc.mc as mc


class GeoLocation(MCDeclarativeBase):
    """A table logging parts within the HERA system
       MAKE Part and Port be unique when combined
    """
    __tablename__ = 'geo_location'

    station_name = Column(String(64), primary_key=True)
    "Colloquial name of station (which is a unique location on the ground.  This is the primary key, so precision matters."

    station_number = Column(Integer)
    "Unique station number that the correlator and MIRIAD want.  Currently set to numbers as of 16/10/26.  This will be superseded by future version."

    future_station_number = Column(Integer)
    "Unique station nymber in the HERA era."

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
        return '<station_name={self.station_name} station_number={self.station_number} northing={self.northing} \
        easting={self.easting} elevation={self.elevation}>'.format(self=self)

    def update(self,args,data):
        """
        update the database given a station_name/_number with columns/values

        Parameters:
        ------------
        data:  [[station0,column0,value0],[...]]
        stationN:  may be station_name (starts with char) or station_number (is an int)
        values:  corresponding list of values
        """
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            for d in data:
                station, station_col = self.station_name_or_number(d[0])
                for geo_rec in session.query(self).filter(station_col==station):
                    try:
                        xxx = getattr(geo_rec,d[1])
                        setattr(geo_rec,d[1],d[2])
                    except AttributeError:
                        print(d[1],'does not exist')

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

def split_update_request(request):
    """
    splits out the update request

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
        sub_arrays = session.split_arrays()
        for a in session.query(GeoLocation).filter(station_col==station):
            for key in sub_arrays.keys():
                if a.station_name in sub_arrays[key]['Stations']:
                    this_sub_array = key
                    break
            else:
                this_sub_array = 'No sub-array information.'
            v = [a.easting, a.northing, a.elevation, a.station_name, a.station_number, this_sub_array]
            if show_geo:
                if args.verbosity=='m' or args.verbosity=='h':
                    print('station_name: ',a.station_name)
                    print('\tstation_number: ',a.station_number)
                    print('\teasting: ',a.easting)
                    print('\tnorthing: ',a.northing)
                    print('\televation: ',a.elevation)
                    print('\tsub-array: ',this_sub_array,sub_arrays[this_sub_array]['Description'])
                elif args.verbosity=='l':
                    print(a,this_sub_array)
    if show_geo:
        if not v and args.verbosity == 'm' or args.verbosity == 'h':
            print(args.locate, ' not found.')
    return v


def plot_arrays(args, overplot=None):
    """Plot the various sub-array types"""
    vpos = {'E':0,'N':1,'Z':2}
    plt.figure(args.xgraph+args.ygraph)
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        sub_arrays = session.split_arrays()
        for key in sub_arrays.keys():
            for loc in sub_arrays[key]['Stations']:
                for a in session.query(GeoLocation).filter(GeoLocation.station_name==loc):
                    v = [a.easting,a.northing,a.elevation]
                plt.plot(v[vpos[args.xgraph]],v[vpos[args.ygraph]],sub_arrays[key]['Marker'],label=a.station_name)
    if overplot:
        overplot_station = plt.plot(overplot[vpos[args.xgraph]], overplot[vpos[args.ygraph]],
                 'ys', markersize=10)
        legendEntries = [overplot_station]
        legendText = [overplot[3]+':'+str(overplot[4])]
        plt.legend((overplot_station),(legendText),numpoints=1,loc='upper right')
    if args.xgraph != 'Z' and args.ygraph != 'Z':
        plt.axis('equal')
    plt.plot(xaxis=args.xgraph, yaxis=args.ygraph)
    plt.show()


class StationMeta(MCDeclarativeBase):
    """
    A table to track sub_array things in various ways
    """
    __tablename__ = 'station_meta'

    prefix = Column(String(64), primary_key=True)
    "String prefix to station type, elements of which are typically characterized by <prefix><int>."

    description = Column(String(64))
    "Short description of station type."

    plot_marker = Column(String(64))
    "matplotlib marker type to use"

    def __repr__(self):
        return '<subarray prefix={self.prefix} description={self.description} marker={self.plot_marker}>'.format(self=self)

