# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Keeping track of geo-located stations.

"""

from __future__ import absolute_import, division, print_function

import os
import sys
import copy

import numpy as np
import matplotlib.pyplot as plt
from pyproj import Proj

from hera_mc import mc, part_connect, cm_utils, geo_location

current_cofa = 'COFA_HSA7458_V000'
def cofa():
    """shortcut to just get cofa"""
    pos = get_location(current_cofa)
    return pos

def get_location(location_name):
    """This provides a function to query a location and get a geo_location class back, with lon/lat added to the class"""
    local_argv = ['--locate',location_name]
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-l', '--locate', default=None)
    parser.add_argument('-v', '--verbosity', default='l')
    parser.add_argument('--date', default='now')
    parser.add_argument('--time', default='now')
    args = parser.parse_args(local_argv)
    located = locate_station(args,show_geo=False)
    return located


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
        connected_antenna = session.query(part_connect.Connections).filter(part_connect.Connections.downstream_part == antenna)
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
                    antenna_connected = connection.upstream_part
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
    found_it = False
    if station_name:
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            station_type = session.get_station_type()
            for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station_name):
                for key in station_type.keys():
                    if a.station_name in station_type[key]['Stations']:
                        this_station = key
                        break
                    else:
                        this_station = 'No station type data.'
                ever_connected = geo_location.is_in_connections(args,a.station_name) 
                active = geo_location.is_in_connections(args,a.station_name,True)
                found_it = True
                hera_proj = Proj(proj='utm', zone=a.tile, ellps=a.datum, south=True)
                a.lon, a.lat = hera_proj(a.easting, a.northing, inverse=True)
                found_location = copy.copy(a)
                if show_geo:
                    if args.verbosity == 'm' or args.verbosity == 'h':
                        print('station_name: ', a.station_name)
                        print('\teasting: ', a.easting)
                        print('\tnorthing: ', a.northing)
                        print('\tlon/lat:  ',a.lon,a.lat)
                        print('\televation: ', a.elevation)
                        print('\tstation description ({}):  {}'.format(this_station,station_type[this_station]['Description']))
                        print('\tever connected:  ',ever_connected)
                        print('\tactive:  ',active)
                        print('\tcreated:  ',a.created_date)
                    elif args.verbosity == 'l':
                        print(a, this_station)
    if show_geo:
        if not found_it and args.verbosity == 'm' or args.verbosity == 'h':
            print(args.locate, ' not found.')
    return found_location

def plot_stations(args, stations_to_plot, fignm, marker_color='g', marker_shape='o', label_station=False):
    """Plot the various sub-array types"""
    coord = {'E': 'easting', 'N': 'northing', 'Z': 'elevation'}
    plt.figure(fignm)
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for station in stations_to_plot:
            for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station):
                show_it = True
                if args.active:
                    show_it = geo_location.is_in_connections(args,station,True)
                if show_it is not False:  #Need this since 0 is a valid antenna
                    pt = {'easting': a.easting, 'northing': a.northing,'elevation': a.elevation}
                    plt.plot(pt[coord[args.xgraph]], pt[coord[args.ygraph]], 
                             color=marker_color, marker=marker_shape, label=a.station_name)
                    if label_station:
                        if args.label_type=='station_name':
                            labeling = a.station_name
                        elif args.label_type=='antenna_number':
                            labeling = geo_location.is_in_connections(args,station,True)
                            if labeling is False:
                                labeling = 'NA'
                        else:
                            labeling = 'S'
                        plt.annotate(labeling, xy=(pt[coord[args.xgraph]], pt[coord[args.ygraph]]),
                                     xytext=(pt[coord[args.xgraph]] + 2, pt[coord[args.ygraph]]))


def plot_station_types(args, label_station=False):
    """Plot the various sub-array types"""
    if ',' in args.station_prefix:
        prefixes_to_plot = args.station_prefix.split(',')
        prefixes_to_plot = [x.lower() for x in prefixes_to_plot]
    elif args.station_prefix == 'all':
        prefixes_to_plot = 'all'
    else:
        prefixes_to_plot = [args.station_prefix.upper()]
    fignm = args.xgraph + args.ygraph
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        station_type = session.get_station_type()
        for key in station_type.keys():
            if prefixes_to_plot=='all' or key.upper() in prefixes_to_plot:
                stations_to_plot = []
                for loc in station_type[key]['Stations']:
                    for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == loc):
                        show_it = True
                        if args.active:
                            show_it = geo_location.is_in_connections(args,loc,True)
                        if show_it is not False:  #Need this since 0 is a valid antenna
                            stations_to_plot.append(loc)
                plot_stations(args, stations_to_plot, fignm, station_type[key]['Marker'][0], station_type[key]['Marker'][1], label_station)
    if args.xgraph != 'Z' and args.ygraph != 'Z':
        plt.axis('equal')
    plt.plot(xaxis=args.xgraph, yaxis=args.ygraph)
    plt.show()

#====================================
def plot_arrays(args, overplot=None, label_station=False):
    """Plot the various sub-array types"""
    coord = {'E': 'easting', 'N': 'northing', 'Z': 'elevation'}
    plt.figure(args.xgraph + args.ygraph)
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        station_type = session.get_station_type()
        for key in station_type.keys():
            for loc in station_type[key]['Stations']:
                for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == loc):
                    show_it = True
                    if args.active:
                        show_it = geo_location.is_in_connections(args,loc,True)
                    if show_it is not False:  #Need this since 0 is a valid antenna
                        pt = {'easting': a.easting, 'northing': a.northing,'elevation': a.elevation}
                        plt.plot(pt[coord[args.xgraph]], pt[coord[args.ygraph]],
                                 station_type[key]['Marker'], label=a.station_name)
                        if label_station:
                            if args.label_type=='station_name':
                                labeling = a.station_name
                            elif args.label_type=='antenna_number':
                                labeling = geo_location.is_in_connections(args,loc,True)
                                if labeling is False:
                                    labeling = 'NA'
                            else:
                                labeling = 'S'
                            plt.annotate(labeling, xy=(pt[coord[args.xgraph]], pt[coord[args.ygraph]]),
                                         xytext=(pt[coord[args.xgraph]] + 2, pt[coord[args.ygraph]]))
    if overplot:
        ever_connected = geo_location.is_in_connections(args,overplot.station_name) 
        active = geo_location.is_in_connections(args,overplot.station_name,True)
        if ever_connected and active:
            over_marker = 'g*'
            mkr_lbl = 'ca'
        elif ever_connected and not active:
            over_marker = 'gx'
            mkr_lbl = 'cx'
        elif active and not ever_connected:
            over_marker = 'yx'
            mkr_lbl = 'xa'
        else:
            over_marker = 'rx'
            mkr_lbl = 'xx'
        opt = {'easting': overplot.easting, 'northing': overplot.northing,'elevation': overplot.elevation}
        overplot_station = plt.plot(opt[coord[args.xgraph]], opt[coord[args.ygraph]], over_marker, markersize=14)
        legendEntries = [overplot_station]
        legendText = [overplot.station_name + ':' + str(active)]
        plt.legend((overplot_station), (legendText), numpoints=1, loc='upper right')
    if args.xgraph != 'Z' and args.ygraph != 'Z':
        plt.axis('equal')
    plt.plot(xaxis=args.xgraph, yaxis=args.ygraph)
    plt.show()




