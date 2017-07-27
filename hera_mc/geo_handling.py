# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Keeping track of geo-located stations.
Top modules are generally called by external (to CM) scripts.
Bottom part is the class that does the work.
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


def cofa(show_cofa=False, session=None):
    """
    Returns location class of current COFA

    Parameters:
    -------------
    show_cofa:  boolean to print out cofa info or just return class
    """

    h = Handling(session)
    located = h.cofa(show_cofa)
    h.close()
    return located


def get_location(location_names, query_date='now', show_location=False, verbosity='m', session=None):
    """
    This provides a function to query a location and get a geo_location class back, with lon/lat added to the class.
    This is the wrapper for other modules outside cm to call.

    Returns location class of called name

    Parameters:
    -------------
    location_name:  location name, may be either a station (geo_location key) or an antenna
    """

    query_date = cm_utils._get_datetime(query_date)
    h = Handling(session)
    located = h.get_location(location_names, query_date, show_location=show_location, verbosity=verbosity)
    h.close()
    return located


def show_it_now(fignm):
    """
    Used in scripts to actually make plot (as opposed to within python).  Seems to be needed...
    """
    if fignm is not False and fignm is not None:
        plt.figure(fignm)
        plt.show()


class Handling:
    """
    Class to allow various manipulations of geo_locations and their properties etc.
    """

    coord = {'E': 'easting', 'N': 'northing', 'Z': 'elevation'}

    def __init__(self, session=None):
        """
        session: session on current database. If session is None, a new session
                 on the default database is created and used.
        """
        if session is None:
            db = mc.connect_to_mc_db()
            self.session = db.sessionmaker()
        else:
            self.session = session

        self.station_types = None

    def close(self):
        self.session.close()

    def cofa(self, show_cofa=False):
        self.get_station_types(add_stations=True)
        current_cofa = self.station_types['COFA']['Stations']
        located = self.get_location(current_cofa, 'now', show_cofa, 'm')[0]

        return located

    def get_station_types(self, add_stations=True):
        """
        adds a dictionary of sub-arrays (station_types) to the class
             [prefix]{'Description':'...', 'plot_marker':'...', 'stations':[]}
        also adds the "flipped" dictionary

        return dictionary with station information

        Parameters:
        -------------
        add_stations:  if True, add all of the stations to their types
                       if False, just return station types
        """

        station_data = self.session.query(geo_location.StationType).all()
        stations = {}
        for sta in station_data:
            stations[sta.prefix] = {'Name': sta.station_type_name,
                                    'Description': sta.description,
                                    'Marker': sta.plot_marker, 'Stations': []}
        if add_stations:
            locations = self.session.query(geo_location.GeoLocation).all()
            for loc in locations:
                for k in stations.keys():
                    if loc.station_name[:len(k)] == k:
                        stations[k]['Stations'].append(loc.station_name)
        self.station_types = stations
        self.flipped_station_types = {}
        for key in self.station_types.keys():
            self.flipped_station_types[self.station_types[key]['Name']] = key

    def is_in_geo_location(self, station_name):
        """
        checks to see if a station_name is in the geo_location database

        return True/False

        Parameters:
        ------------
        station_name:  string name of station
        """

        station = self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station_name)
        if station.count() > 0:
            station_present = True
        else:
            station_present = False
        return station_present

    def is_in_connections(self, station_name, active_date=None, return_antrev=True):
        """
        checks to see if the station_name is in the connections database (which means it is also in parts)
        if active_date is None, it will return True/False if ever connected
        if active_date is given, it will check whether it was connected at that time

        return True/False unless (1) active_date is provided and (2) return_antrev is True

        Parameters:
        ------------
        station_name:  string name of station
        active_date:  astropy Time to check if active, default is None
        return_antrev:  boolean flag to return True/False or antrev tuple, default is True
        """

        active_date = cm_utils._get_datetime(active_date)
        connected_antenna = self.session.query(part_connect.Connections).filter(part_connect.Connections.upstream_part == station_name)
        if connected_antenna.count() > 0:
            antenna_connected = True
        else:
            antenna_connected = False
        if antenna_connected and active_date is not None:
            counter = 0
            for connection in connected_antenna.all():
                connection.gps2Time()
                if cm_utils._is_active(active_date, connection.start_date, connection.stop_date):
                    if return_antrev:
                        antenna_connected = (connection.downstream_part, connection.down_part_rev)
                    else:
                        antenna_connected = True
                    counter += 1
                else:
                    antenna_connected = False
            if counter > 1:
                print("Warning:  more than one active connection for", station_name)
                print("\tYou should check this out and correct it.")
                antenna_connected = False
        return antenna_connected

    def find_station_of_antenna(self, antenna, query_date):
        """
        checks to see at which station an antenna is located

        Returns None or the active station_name (must be an active station for the query_date)

        Parameters:
        ------------

        antenna:  antenna number as float, int, or string. If needed, it prepends the 'A'
        query_date:  is the astropy Time for contemporary antenna
        """

        query_date = cm_utils._get_datetime(query_date)
        if type(antenna) == float or type(antenna) == int or antenna[0] != 'A':
            antenna = 'A' + str(antenna).strip('0')
        connected_antenna = self.session.query(part_connect.Connections).filter((part_connect.Connections.downstream_part == antenna) &
                                                                                (query_date.gps >= part_connect.Connections.start_gpstime))
        ctr = 0
        for conn in connected_antenna:
            if conn.stop_gpstime is None or query_date.gps <= conn.stop_gpstime:
                antenna_connected = copy.copy(conn)
                ctr += 1
        if ctr == 0:
            antenna_connected = None
        elif ctr > 1:
            raise ValueError('More than one active connection between station and antenna')
        return antenna_connected.upstream_part

    def get_location(self, to_find, query_date, show_location=False, verbosity='m'):
        """
        Return the location of station_name or antenna_number as contained in to_find.
        This accepts the fact that antennas are sort of stations, even though they are parts

        Parameters:
        ------------
        to_find:  station names to find (must be a list)
        query_date:  astropy Time for contemporary antenna
        show_location:   if True, it will print the information
        verbosity:  sets the verbosity of the print
        """
        self.get_station_types(add_stations=True)
        found_location = []
        for L in to_find:
            station_name = False
            try:
                antenna_number = int(L)
                station_name = self.find_station_of_antenna(antenna_number, query_date)
            except ValueError:
                station_name = L.upper()
            found_it = False
            if station_name:
                for a in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station_name):
                    for key in self.station_types.keys():
                        if a.station_name in self.station_types[key]['Stations']:
                            this_station = key
                            break
                        else:
                            this_station = 'No station type data.'
                    a.gps2Time()
                    desc = self.station_types[this_station]['Description']
                    ever_connected = self.is_in_connections(a.station_name)
                    active = self.is_in_connections(a.station_name, query_date, return_antrev=True)
                    found_it = True
                    hera_proj = Proj(proj='utm', zone=a.tile, ellps=a.datum, south=True)
                    a.lon, a.lat = hera_proj(a.easting, a.northing, inverse=True)
                    found_location.append(copy.copy(a))
                    if show_location:
                        if verbosity == 'm' or verbosity == 'h':
                            print('station_name: ', a.station_name)
                            print('\teasting: ', a.easting)
                            print('\tnorthing: ', a.northing)
                            print('\tlon/lat:  ', a.lon, a.lat)
                            print('\televation: ', a.elevation)
                            print('\tstation description ({}):  {}'.format(this_station, desc))
                            print('\tever connected:  ', ever_connected)
                            print('\tactive:  ', active)
                            print('\tcreated:  ', cm_utils._get_displayTime(a.created_date))
                        elif verbosity == 'l':
                            print(a, this_station)
            else:
                found_location.append(None)
            if show_location:
                if not found_it and verbosity == 'm' or verbosity == 'h':
                    print(L, ' not found.')
        return found_location

    def get_all_everconnected_locations(self):
        """
        Returns a list of all of the locations ever connected.
        """

        stations = self.session.query(geo_location.GeoLocation).all()
        connections = self.session.query(part_connect.Connections).all()
        stations_conn = []
        for stn in stations:
            hera_proj = Proj(proj='utm', zone=stn.tile, ellps=stn.datum, south=True)
            stn.lon, stn.lat = hera_proj(stn.easting, stn.northing, inverse=True)
            ever_connected = self.is_in_connections(stn.station_name)
            if ever_connected:
                connections = self.session.query(part_connect.Connections).filter(
                    part_connect.Connections.upstream_part == stn.station_name)
                for conn in connections:
                    ant_num = int(conn.downstream_part[1:])
                    conn.gps2Time()
                    stations_conn.append({'station_name': stn.station_name,
                                          'station_type': stn.station_type_name,
                                          'longitude': stn.lon,
                                          'latitude': stn.lat,
                                          'elevation': stn.elevation,
                                          'antenna_number': ant_num,
                                          'start_date': conn.start_date,
                                          'stop_date': conn.stop_date})
        return stations_conn

    def get_ants_installed_since(self, query_date, station_types_to_check='all'):
        """
        Returns list of antennas installed since query_date.

        Parameters
        -----------
        query_date:  date to limit check for installation
        station_types_to_check:  list of stations types to limit check
        """

        self.get_station_types(add_stations=False)
        dt = query_date.gps
        found_stations = []
        for a in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.created_gpstime >= dt):
            if station_types_to_check == 'all' or self.flipped_station_types[a.station_type_name] in station_types_to_check:
                found_stations.append(a.station_name)
        return found_stations

    def plot_stations(self, stations_to_plot, query_date, state_args):
        """
        Plot a list of stations.

        Parameters:
        ------------
        stations_to_plot:  list containing station_names (note:  NOT antenna_numbers)
        query_date:  date to use to check if active
        state_args:  dictionary with state arguments (fig_num, marker_color, marker_shape, marker_size, show_label)
        """
        query_date = cm_utils._get_datetime(query_date)
        displaying_label = bool(state_args['show_label'])
        if displaying_label:
            label_to_show = state_args['show_label'].lower()
        plt.figure(state_args['fig_num'])
        for station in stations_to_plot:
            for a in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station):
                show_it = True
                if state_args['show_state'].lower() == 'active':
                    show_it = self.is_in_connections(station, query_date, return_antrev=False)
                if show_it:
                    pt = {'easting': a.easting, 'northing': a.northing, 'elevation': a.elevation}
                    __X = pt[self.coord[state_args['xgraph']]]
                    __Y = pt[self.coord[state_args['ygraph']]]
                    plt.plot(__X, __Y, color=state_args['marker_color'], marker=state_args['marker_shape'],
                             markersize=state_args['marker_size'], label=a.station_name)
                    if displaying_label:
                        if label_to_show == 'name':
                            labeling = a.station_name
                        else:
                            antrev = self.is_in_connections(station, query_date, True)
                            if antrev is False:
                                labeling = 'NA'
                            else:
                                ant, rev = antrev
                                if label_to_show == 'num':
                                    labeling = ant.strip('A')
                                elif label_to_show == 'ser':
                                    p = self.session.query(part_connect.Parts).filter((part_connect.Parts.hpn == ant) &
                                                                                      (part_connect.Parts.hpn_rev == rev))
                                    if p.count() == 1:
                                        labeling = p.first().manufacturer_number.replace('S/N', '')
                                    else:
                                        labeling = '-'
                                else:
                                    labeling = 'S'
                        plt.annotate(labeling, xy=(__X, __Y), xytext=(__X + 2, __Y))
        return state_args['fig_num']

    def plot_station_types(self, query_date, state_args):
        """
        Plot the various sub-array types

        Return figure number of plot

        Parameters:
        ------------
        query_date:  date to use to check if active.
        state_args:  dictionary with state arguments (fig_num, marker_color, marker_shape, marker_size, show_label)
        """

        query_date = cm_utils._get_datetime(query_date)
        if state_args['background'][0] == 'all':
            prefixes_to_plot = 'all'
        else:
            prefixes_to_plot = [x.upper() for x in state_args['background']]
        self.get_station_types(add_stations=True)
        for key in self.station_types.keys():
            if prefixes_to_plot == 'all' or key.upper() in prefixes_to_plot:
                stations_to_plot = []
                for loc in self.station_types[key]['Stations']:
                    for a in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == loc):
                        show_it = True
                        if state_args['show_state'].lower() == 'active':
                            show_it = self.is_in_connections(loc, query_date, False)
                        if show_it:
                            stations_to_plot.append(loc)
                state_args['marker_color'] = self.station_types[key]['Marker'][0]
                state_args['marker_shape'] = self.station_types[key]['Marker'][1]
                state_args['marker_size'] = 6
                self.plot_stations(stations_to_plot, query_date, state_args)
        if state_args['xgraph'].upper() != 'Z' and state_args['ygraph'].upper() != 'Z':
            plt.axis('equal')
        plt.plot(xaxis=state_args['xgraph'], yaxis=state_args['ygraph'])
        return state_args['fig_num']

    def overplot(self, located_stations, state_args):
        """Overplot station on an existing plot.  It sets specific symbols/colors for active, connected, etc

           Parameters:
           ------------
           located_stations:  geo class of station to plot
           state_args:  dictionary with state arguments (fig_num, marker_color, marker_shape, marker_size, show_label)
        """
        for located in located_stations:
            ever_connected = self.is_in_connections(located.station_name)
            active = self.is_in_connections(located.station_name, query_date)
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
            plt.figure(state_args['fig_num'])
            __X = opt[self.coord[state_args['xgraph']]]
            __Y = opt[self.coord[state_args['ygraph']]]
            overplot_station = plt.plot(__X, __Y, over_marker, markersize=state_args['marker_size'])
            legendEntries = [overplot_station]
            legendText = [located.station_name + ':' + str(active)]
            plt.legend((overplot_station), (legendText), numpoints=1, loc='upper right')
