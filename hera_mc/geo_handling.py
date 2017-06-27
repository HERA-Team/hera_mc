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



def cofa(show_cofa=False):
    """
    Shortcut to just get the current cofa

    Returns location class of current COFA

    Parameters:
    -------------
    show_cofa:  boolean to print out cofa info or just return class
    """
    parser = mc.get_mc_argument_parser()
    args = parser.parse_args([])
    h = Handling(args)
    st = h.get_station_types()
    h.close()
    current_cofa = st['COFA']['Stations']
    located = get_location(current_cofa,'now',show_cofa,'m')[0]
    return located

def get_location(location_names, query_date='now', show_location=False, verbosity='m'):
    """
    This provides a function to query a location and get a geo_location class back, with lon/lat added to the class.
    This is the wrapper for other modules outside cm to call.

    Returns location class of called name

    Parameters:
    -------------
    location_name:  location name, may be either a station (geo_location key) or an antenna
    """

    parser = mc.get_mc_argument_parser()
    args = parser.parse_args([])
    query_date = cm_utils._get_datetime(query_date)
    h = Handling(args)
    located = h.locate_station(location_names, query_date, show_location=show_location, verbosity=verbosity)
    h.close()
    return located

def show_it_now(fignm=0):
    plt.figure(fignm)
    plt.show()


class Handling:
    """
    Class to allow various manipulations of geo_locations and their properties etc.
    """
    coord = {'E': 'easting', 'N': 'northing', 'Z': 'elevation'}

    def __init__(self,args):
        """
        args:  needed arguments to open database
        """
        self.args = args
        db = mc.connect_to_mc_db(self.args)
        self.session = db.sessionmaker()

    def close(self):
        self.session.close()

    def get_station_types(self):
        """
        returns a dictionary of sub-arrays
             [prefix]{'Description':'...', 'plot_marker':'...', 'stations':[]}
        """

        station_data = self.session.query(geo_location.StationType).all()
        stations = {}
        for sta in station_data:
            stations[sta.prefix] = {'Name': sta.station_type_name,
                                    'Description': sta.description,
                                    'Marker': sta.plot_marker, 'Stations': []}
        locations = self.session.query(geo_location.GeoLocation).all()
        for loc in locations:
            for k in stations.keys():
                if loc.station_name[:len(k)] == k:
                    stations[k]['Stations'].append(loc.station_name)
        return stations


    def is_in_geo_location(self, station_name):
        """
        checks to see if a station_name is in the geo_location database

        return True/False

        Parameters:
        ------------
        args:  needed arguments to open the database
        station_name:  string name of station
        """

        station = self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station_name)
        if station.count() > 0:
            station_present = True
        else:
            station_present = False
        return station_present


    def is_in_connections(self, station_name, active_date=None):
        """
        checks to see if the station_name is in the connections database (which means it is also in parts)

        return True/False unless check_if_active flag is set, when it returns the antenna number at that location

        Parameters:
        ------------
        args:  needed arguments to open database and set date/time
        station_name:  string name of station
        active_date:  astropy Time to check if active, ignores if not an instance of Time
        """

        connected_station = self.session.query(part_connect.Connections).filter(part_connect.Connections.upstream_part == station_name)
        if connected_station.count() > 0:
            station_connected = True
        else:
            station_connected = False
        if station_connected and isinstance(active_date,Time):
            counter = 0
            for connection in connected_station.all():
                connection.gps2Time()
                if cm_utils._is_active(active_date, connection.start_date, connection.stop_date):
                    station_connected = connection.downstream_part+':'+connection.down_part_rev
                    counter += 1
                else:
                    station_connected = False
            if counter > 1:
                print("Error:  more than one active connection for", station_name)
                station_connected = False
        return station_connected


    def find_station_of_antenna(self, antenna, query_date):
        """
        checks to see at which station an antenna is located

        Returns False or the active station_name (must be an active station for the query_date)

        Parameters:
        ------------

        antenna:  antenna number as float (why?), int, or string. If needed, it prepends the 'A'
        query_date:  is the astropy Time for contemporary antenna
        """

        if type(antenna) == float or type(antenna) == int or antenna[0] != 'A':
            antenna = 'A' + str(antenna).strip('0')
        connected_antenna = self.session.query(part_connect.Connections).filter( (part_connect.Connections.downstream_part == antenna) &
                                                                                 (query_date.gps >= part_connect.Connections.start_gpstime) &
                                                                                 (query_date.gps <= part_connect.Connections.stop_gpstime) )
        if connected_antenna.count() == 0:
            antenna_connected = False
        elif connected_antenna.count() == 1:
            antenna_connected = connected_antenna.first().upstream_part
        else:
            raise ValueError('More than one active connection')
        return antenna_connected


    def locate_station(self, to_find, query_date, show_location=False, verbosity='m'):
        """
        Return the location of station_name or antenna_number as contained in args.locate.
        This accepts the fact that antennas are sort of stations, even though they are parts

        Parameters:
        ------------
        to_find:  station names to find (must be a list)
        query_date:  astropy Time for contemporary antenna
        show_location:   if True, it will print the information
        verbosity:  sets the verbosity of the print
        """

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
                station_type = self.get_station_types()
                for a in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station_name):
                    for key in station_type.keys():
                        if a.station_name in station_type[key]['Stations']:
                            this_station = key
                            break
                        else:
                            this_station = 'No station type data.'
                    a.gps2Time()
                    ever_connected = self.is_in_connections(a.station_name, '<')
                    active = self.is_in_connections(a.station_name, query_date)
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
                            print('\tstation description ({}):  {}'.format(this_station, station_type[this_station]['Description']))
                            print('\tever connected:  ', ever_connected)
                            print('\tactive:  ', active)
                            print('\tcreated:  ', cm_utils._get_displayTime(a.created_date))
                        elif verbosity == 'l':
                            print(a, this_station)
            if show_location:
                if not found_it and verbosity == 'm' or verbosity == 'h':
                    print(L, ' not found.')
        return found_location

    def get_all_locations(self):
        stations = self.session.query(geo_location.GeoLocation).all()
        connections = self.session.query(part_connect.Connections).all()
        stations_new = []
        for stn in stations:
            hera_proj = Proj(proj='utm', zone=stn.tile, ellps=stn.datum, south=True)
            stn.lon, stn.lat = hera_proj(stn.easting, stn.northing, inverse=True)
            ever_connected = self.is_in_connections(stn.station_name,'>')
            if ever_connected is True:
                connections = session.query(part_connect.Connections).filter(
                    part_connect.Connections.upstream_part == stn.station_name)
                for conn in connections:
                    ant_num = int(conn.downstream_part[1:])
                    conn.gps2Time()
                    stations_new.append({'station_name': stn.station_name,
                                         'station_type': stn.station_type_name,
                                         'longitude': stn.lon,
                                         'latitude': stn.lat,
                                         'elevation': stn.elevation,
                                         'antenna_number': ant_num,
                                         'start_date': start_date,
                                         'stop_date': stop_date})
        return stations_new


    def get_since_date(self,query_date):
        dt = query_date.gps
        found_stations = []
        for a in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.created_gpstime >= dt):
            found_stations.append(a.station_name)
        return found_stations


    def plot_stations(self, stations_to_plot, query_date, state_args):
        """
        Plot a list of stations.

        Parameters:
        ------------
        stations_to_plot:  list containing station_names (note:  NOT antenna_numbers)
        query_date:  date for active-only plot
        state_args:  dictionary with state arguments (fig_num, marker_color, marker_shape, marker_size, show_label)
        """
        displaying_label = bool(state_args['show_label'])
        if displaying_label:
            label_to_show = state_args['show_label'].lower()
        plt.figure(state_args['fig_num'])
        for station in stations_to_plot:
            for a in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == station):
                show_it = True
                if state_args['show_state'].lower() == 'active':
                    show_it = self.is_in_connections(station, query_date)
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
                            antrev = self.is_in_connections(station, query_date)
                            if antrev is False:
                                labeling = 'NA'
                            else:
                                ant = antrev.split(':')[0]
                                rev = antrev.split(':')[1]
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


    def plot_station_types(self, query_date, state_args):
        """
        Plot the various sub-array types

        Return fignm of plot

        Parameters:
        ------------
        label_station:  flag to either label the station or not.  If not false, give label type.
        query_date:
        """

        if state_args['background'][0] == 'all':
            prefixes_to_plot = 'all'
        else:
            prefixes_to_plot = [x.upper() for x in state_args['background']]
        station_type = self.get_station_types()
        for key in station_type.keys():
            if prefixes_to_plot == 'all' or key.upper() in prefixes_to_plot:
                stations_to_plot = []
                for loc in station_type[key]['Stations']:
                    for a in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name == loc):
                        show_it = True
                        if state_args['show_state'].lower() =='active':
                            show_it = self.is_in_connections(loc, query_date)
                        if show_it:
                            stations_to_plot.append(loc)
                state_args['marker_color']=station_type[key]['Marker'][0]
                state_args['marker_shape']=station_type[key]['Marker'][1]
                state_args['marker_size']=6
                self.plot_stations(stations_to_plot, query_date, state_args)
        if state_args['xgraph'].upper() != 'Z' and state_args['ygraph'].upper() != 'Z':
            plt.axis('equal')
        plt.plot(xaxis=state_args['xgraph'], yaxis=state_args['ygraph'])
        return state_args['fig_num']


    def overplot(self, located, state_args):
        """Overplot a station on an existing plot.  It sets specific symbols/colors for active, connected, etc

           Parameters:
           ------------
           located:  geo class of station to plot
           state_args:  
        """
        if located:
            ever_connected = self.is_in_connections(located.station_name)
            active = self.is_in_connections(located.station_name, True)
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
            __X = opt[coord[state_args['xgraph']]]
            __Y = opt[coord[state_args['ygraph']]]
            overplot_station = plt.plot(__X, __Y, over_marker, markersize=state_args['marker_size'])
            legendEntries = [overplot_station]
            legendText = [located.station_name + ':' + str(active)]
            plt.legend((overplot_station), (legendText), numpoints=1, loc='upper right')
