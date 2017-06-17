# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Keeping track of geo-located stations.

"""

from __future__ import absolute_import, division, print_function

import os
import sys
import copy
from astropy.time import Time

import numpy as np
import matplotlib.pyplot as plt
from pyproj import Proj

from hera_mc import mc, part_connect, cm_utils, geo_location

current_cofa = 'COFA_HSA7458_V000'

def cofa(show_cofa=False):
    """
    Shortcut to just get the current cofa (currently hard-coded in geo_handling.py)

    Returns location class of current COFA

    Parameters:
    -------------
    show_cofa:  boolean to print out cofa info or just return class
    """

    located = get_location(current_cofa)
    if show_cofa:
        print('Center of array: %s' % (located.station_name))
        try:
            print('UTM:  {} {:.0f}E {:.0f}N at {:.1f}m   ({})'.format(located.tile, located.easting, located.northing, located.elevation, located.datum))
        except TypeError:
            print('UTM:  {} {:.0f}E {:.0f}N   ({})'.format(located.tile, located.easting, located.northing, located.datum))
        print('Lat/Lon:  {}  {}'.format(located.lat, located.lon))
    return located


def get_location(location_name):
    """This provides a function to query a location and get a geo_location class back, with lon/lat added to the class

    Returns location class of called name

    Parameters:
    -------------
    location_name:  string of location name
    """

    local_argv = ['--locate', location_name]
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-l', '--locate', default=None)
    parser.add_argument('-v', '--verbosity', default='l')
    parser.add_argument('--date', default='now')
    parser.add_argument('--time', default='now')
    args = parser.parse_args(local_argv)
    located = locate_station(args, args.locate, show_location=False)
    return located


def find_station_name(args, antenna, query_date):
    """
    checks to see what station an antenna is at

    Returns False or the active station_name (must be an active station for the query_date)

    Parameters:
    ------------
    args:  needed arguments to open database
    antenna:  antenna number as float (why?), int, or string. If needed, it prepends the 'A'
    query_date:  is the astropy Time for contemporary antenna
    """

    if type(antenna) == float or type(antenna) == int or antenna[0] != 'A':
        antenna = 'A' + str(antenna).strip('0')
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        connected_antenna = session.query(part_connect.Connections).filter( (part_connect.Connections.downstream_part == antenna) &
                                                                            (query_date.gps >= part_connect.Connections.start_gpstime) &
                                                                            (query_date.gps <= part_connect.Connections.stop_gpstime) )
        if connected_antenna.count() == 0:
            antenna_connected = False
        elif connected_antenna.count() == 1:
            antenna_connected = connected_antenna.first().upstream_part
        else:
            raise ValueError('More than one active connection')
    return antenna_connected


def locate_station(args, station_to_find, query_date, show_location=False):
    """
    Return the location of station_name or antenna_number as contained in args.locate.
    This accepts the fact that antennas are sort of stations, even though they are parts

    Parameters:
    ------------
    args:  needed arguments to open database
    query_date:  astropy Time for contemporary antenna
    show_location:   if True, it will print the information.
    """

    found_location = None
    station_name = False
    try:
        station = int(station_to_find)
        station_name = find_station_name(args, station,query_date)
    except ValueError:
        station_name = station_to_find.upper()
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
                ever_connected = geo_location.is_in_connections(args, a.station_name, '<')
                active = geo_location.is_in_connections(args, a.station_name, query_date)
                found_it = True
                hera_proj = Proj(proj='utm', zone=a.tile, ellps=a.datum, south=True)
                a.lon, a.lat = hera_proj(a.easting, a.northing, inverse=True)
                found_location = copy.copy(a)
                if show_location:
                    if args.verbosity == 'm' or args.verbosity == 'h':
                        print('station_name: ', a.station_name)
                        print('\teasting: ', a.easting)
                        print('\tnorthing: ', a.northing)
                        print('\tlon/lat:  ', a.lon, a.lat)
                        print('\televation: ', a.elevation)
                        print('\tstation description ({}):  {}'.format(this_station, station_type[this_station]['Description']))
                        print('\tever connected:  ', ever_connected)
                        print('\tactive:  ', active)
                        print('\tcreated:  ', a.created_date)
                    elif args.verbosity == 'l':
                        print(a, this_station)
    if show_location:
        if not found_it and args.verbosity == 'm' or args.verbosity == 'h':
            print(args.locate, ' not found.')
    return found_location

def get_all_locations(args):
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        stations = session.query(geo_location.GeoLocation).all()
        connections = session.query(part_connect.Connections).all()
        stations_new = []
        for stn in stations:
            hera_proj = Proj(proj='utm', zone=stn.tile, ellps=stn.datum, south=True)
            stn.lon, stn.lat = hera_proj(stn.easting, stn.northing, inverse=True)
            ever_connected = geo_location.is_in_connections(args, stn.station_name,'>')
            if ever_connected is True:
                connections = session.query(part_connect.Connections).filter(
                    part_connect.Connections.upstream_part == stn.station_name)
                for conn in connections:
                    ant_num = int(conn.downstream_part[1:])
                    start_date = Time(conn.start_gpstime,format='gps')
                    stop_date = Time(conn.stop_gpstime,format='gps')
                    stations_new.append({'station_name': stn.station_name,
                                         'station_type': stn.station_type_name,
                                         'longitude': stn.lon,
                                         'latitude': stn.lat,
                                         'elevation': stn.elevation,
                                         'antenna_number': ant_num,
                                         'start_date': start_date,
                                         'stop_date': stop_date})
    return stations_new


def get_since_date(args,query_date):
    dt = query_date.gps
    db = mc.connect_to_mc_db(args)
    found_stations = []
    with db.sessionmaker() as session:
        for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.created_gpstime >= dt):
            found_stations.append(a.station_name)
    return found_stations

coord = {'E': 'easting', 'N': 'northing', 'Z': 'elevation'}


def plot_stations(args, stations_to_plot, fignm, query_date=False, marker_color='g', marker_shape='o', marker_size='8', label_station=False):
    """Plot a list of stations.

       Parameters:
       ------------
       args:  needed arguments to open database and set date/time
       stations_to_plot:  list containing station_names (note:  NOT antenna_numbers)
       fignm:  figure name/number to plot on
       marker_color, marker_shape:  color and shape of marker
       label_station:  flag to either label the station or not.  If not false, give label type.
    """

    plt.figure(fignm)
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for station in stations_to_plot:
            for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station):
                show_it = True
                if args.active:
                    show_it = geo_location.is_in_connections(args, station, query_date)
                if show_it is not False:  # Need this since 0 is a valid antenna
                    pt = {'easting': a.easting, 'northing': a.northing, 'elevation': a.elevation}
                    plt.plot(pt[coord[args.xgraph]], pt[coord[args.ygraph]],
                             color=marker_color, marker=marker_shape, markersize=marker_size, label=a.station_name)
                    if label_station:
                        if args.label_type == 'station_name':
                            labeling = a.station_name
                        else:
                            antrev = geo_location.is_in_connections(args, station, query_date)
                            if antrev is False:
                                labeling = 'NA'
                            else:
                                ant = antrev.split(':')[0]
                                rev = antrev.split(':')[1]
                                if args.label_type == 'antenna_number':
                                    labeling = ant.strip('A')
                                elif args.label_type == 'serial_number':
                                    p = session.query(part_connect.Parts).filter((part_connect.Parts.hpn == ant) &
                                                                                 (part_connect.Parts.hpn_rev == rev))
                                    if p.count() == 1:
                                        labeling = p.first().manufacturer_number.replace('S/N', '')
                                    else:
                                        labeling = '-'
                                else:
                                    labeling = 'S'
                        plt.annotate(labeling, xy=(pt[coord[args.xgraph]], pt[coord[args.ygraph]]),
                                     xytext=(pt[coord[args.xgraph]] + 2, pt[coord[args.ygraph]]))


def plot_station_types(args, label_station=False, query_date=False):
    """Plot the various sub-array types

       Return fignm of plot

       Parameters:
       ------------
       args:  needed arguments to open database and set date/time
       label_station:  flag to either label the station or not.  If not false, give label type.
    """

    if ',' in args.graph:
        prefixes_to_plot = args.graph.split(',')
        prefixes_to_plot = [x.upper() for x in prefixes_to_plot]
    elif args.graph == 'all':
        prefixes_to_plot = 'all'
    else:
        prefixes_to_plot = [args.graph.upper()]
    fignm = args.xgraph + args.ygraph
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        station_type = session.get_station_type()
        for key in station_type.keys():
            if prefixes_to_plot == 'all' or key.upper() in prefixes_to_plot:
                stations_to_plot = []
                for loc in station_type[key]['Stations']:
                    for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == loc):
                        show_it = True
                        if args.active:
                            show_it = geo_location.is_in_connections(args, loc, query_date)
                        if show_it is not False:  # Need this since 0 is a valid antenna
                            stations_to_plot.append(loc)
                plot_stations(args, stations_to_plot, fignm, query_date, marker_color=station_type[key]['Marker'][0],
                              marker_shape=station_type[key]['Marker'][1], marker_size='6',
                              label_station=label_station)
    if args.xgraph != 'Z' and args.ygraph != 'Z':
        plt.axis('equal')
    plt.plot(xaxis=args.xgraph, yaxis=args.ygraph)
    return fignm


def overplot(args, located, fignm):
    """Overplot a station on an existing plot.  It sets specific symbols/colors for active, connected, etc

       Parameters:
       ------------
       args:  needed arguments to open database and set date/time
       located:  geo class of station to plot
       fignm:  figure name/number to plot on
    """
    if located:
        ever_connected = geo_location.is_in_connections(args, located.station_name)
        active = geo_location.is_in_connections(args, located.station_name, True)
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
        opt = {'easting': located.easting, 'northing': located.northing, 'elevation': located.elevation}
        plt.figure(fignm)
        overplot_station = plt.plot(opt[coord[args.xgraph]], opt[coord[args.ygraph]], over_marker, markersize=14)
        legendEntries = [overplot_station]
        legendText = [located.station_name + ':' + str(active)]
        plt.legend((overplot_station), (legendText), numpoints=1, loc='upper right')


def show_it_now(fignm):
    plt.figure(fignm)
    plt.show()
