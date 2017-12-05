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
import warnings
from astropy.time import Time, TimeDelta
from sqlalchemy import func

from pyproj import Proj

from hera_mc import mc, part_connect, cm_utils, geo_location


def cofa(session=None):
    """
    Returns location class of current COFA

    Parameters:
    -------------
    session:  db session to use
    """
    h = Handling(session)
    located = h.cofa()
    h.close()
    return located


def get_location(location_names, query_date='now', session=None):
    """
    This provides a function to query a location and get a geo_location
        class back, with lon/lat added to the class.
    This is the wrapper for other modules outside cm to call.

    Returns location class of called name

    Parameters:
    -------------
    location_names:  location name, may be either a station (geo_location key)
                     or an antenna
    query_date:  date for query
    session:  db session to use
    """
    query_date = cm_utils.get_astropytime(query_date)
    h = Handling(session)
    located = h.get_location(location_names, query_date)
    h.close()
    return located


def show_it_now(fignm):
    """
    Used in scripts to actually make plot (as opposed to within python). Seems to be needed...

    Parameters:
    -------------
    fignm:  string/int for figure
    """
    import matplotlib.pyplot as plt

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
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session

        self.station_types = None

    def close(self):
        """
        Close the session
        """
        self.session.close()

    def cofa(self):
        """
        Get the current center of array.

        Returns located cofa.
        """
        self.get_station_types(add_stations=True)
        current_cofa = self.station_types['COFA']['Stations']
        located = self.get_location(current_cofa, 'now', self.station_types)
        if len(located) > 1:
            s = "{} has multiple cofa values.".format(str(current_cofa))
            warnings.warn(s)

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

    def is_in_database(self, station_name, db_name='geo_location'):
        """
        checks to see if a station_name is in the named database

        return True/False

        Parameters:
        ------------
        station_name:  string name of station
        db_name:  name of database table
        """
        ustn = station_name.upper()
        if db_name == 'geo_location':
            station = self.session.query(geo_location.GeoLocation).filter(
                func.upper(geo_location.GeoLocation.station_name) == ustn)
        elif db_name == 'connections':
            station = self.session.query(part_connect.Connections).filter(
                func.upper(part_connect.Connections.upstream_part) == ustn)
        else:
            raise ValueError('db not found.')
        if station.count() > 0:
            station_present = True
        else:
            station_present = False
        return station_present

    def find_antenna_at_station(self, station, query_date):
        """
        checks to see what antenna is at a station

        Returns a tuple (antenna_name, antenna_revision), representing the antenna
        that was active at the date query_date, or None if no antenna was active
        at the station. Raises ValueError if the database lists multiple active
        connections at the station at query_date.

        Parameters:
        ------------
        station:  station name as string.
        query_date:  is the astropy Time for contemporary antenna
        """

        query_date = cm_utils.get_astropytime(query_date)
        ustn = station.upper()
        connected_antenna = self.session.query(part_connect.Connections).filter(
            (func.upper(part_connect.Connections.upstream_part) == ustn) &
            (query_date.gps >= part_connect.Connections.start_gpstime))
        ctr = 0
        for conn in connected_antenna:
            if conn.stop_gpstime is None or query_date.gps <= conn.stop_gpstime:
                antenna_connected = copy.copy(conn)
                ctr += 1
        if ctr == 0:
            return None
        elif ctr > 1:
            raise ValueError('More than one active connection between station and antenna')
        return antenna_connected.downstream_part, antenna_connected.down_part_rev

    def find_station_of_antenna(self, antenna, query_date):
        """
        checks to see at which station an antenna is located

        Returns None or the active station_name (must be an active station for
            the query_date)

        Parameters:
        ------------
        antenna:  antenna number as float, int, or string. If needed, it prepends the 'A'
        query_date:  is the astropy Time for contemporary antenna
        """

        query_date = cm_utils.get_astropytime(query_date)
        if type(antenna) == float or type(antenna) == int or antenna[0] != 'A':
            antenna = 'A' + str(antenna).strip('0')
        uant = antenna.upper()
        connected_antenna = self.session.query(part_connect.Connections).filter(
            (func.upper(part_connect.Connections.downstream_part) == uant) &
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

    def get_location(self, to_find_list, query_date, station_types=None):
        """
        Return the location of station_name or antenna_number as contained in to_find.
        This accepts the fact that antennas are sort of stations, even though they are parts

        Parameters:
        ------------
        to_find_list:  station names to find (must be a list)
        query_date:  astropy Time for contemporary antenna
        station_types: list of station_type prefixes (e.g. HH)
        show_location:   if True, it will print the information
        verbosity:  sets the verbosity of the print
        """
        if station_types is None:
            self.get_station_types(add_stations=True)
            station_types = self.station_types
        found_location = []
        for L in to_find_list:
            station_name = False
            try:
                antenna_number = int(L)
                station_name = self.find_station_of_antenna(antenna_number, query_date)
            except ValueError:
                station_name = L
            if station_name:
                ustn = station_name.upper()
                for a in self.session.query(geo_location.GeoLocation).filter(
                        func.upper(geo_location.GeoLocation.station_name) == ustn):
                    this_station_type = None
                    for key in self.station_types.keys():
                        if a.station_name in self.station_types[key]['Stations']:
                            this_station_type = key
                            break
                    if this_station_type is None:
                        print("{} not found.".format(L))
                        break
                    a.gps2Time()
                    a.station_type = this_station_type
                    a.desc = self.station_types[this_station_type]['Description']
                    hera_proj = Proj(proj='utm', zone=a.tile, ellps=a.datum, south=True)
                    a.lon, a.lat = hera_proj(a.easting, a.northing, inverse=True)
                    found_location.append(copy.copy(a))
        return found_location

    def print_loc_info(self, loc_list, verbosity='h'):
        """
        Prints out location information as returned from get_location.
        Returns False if provided 'loc' is None, otherwise returns True.
        """
        if loc_list is None or len(loc_list) == 0:
            print("No locations found.")
            return False
        for a in loc_list:
            if verbosity == 'm' or verbosity == 'h':
                print('station_name: ', a.station_name)
                print('\teasting: ', a.easting)
                print('\tnorthing: ', a.northing)
                print('\tlon/lat:  ', a.lon, a.lat)
                print('\televation: ', a.elevation)
                print('\tstation description ({}):  {}'.format(a.station_type, a.desc))
                print('\tcreated:  ', cm_utils.get_time_for_display(a.created_date))
            elif verbosity == 'l':
                print(a)
        return True

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
        for a in self.session.query(geo_location.GeoLocation).filter(
                geo_location.GeoLocation.created_gpstime >= dt):
            if (station_types_to_check == 'all' or
                    self.flipped_station_types[a.station_type_name] in station_types_to_check):
                found_stations.append(a.station_name)
        return found_stations

    def plot_stations(self, stations_to_plot_list, query_date, state_args, testing=False):
        """
        Plot a list of stations.

        Parameters:
        ------------
        stations_to_plot_list:  list containing station_names (note:  NOT antenna_numbers)
        query_date:  date to use to check if active
        state_args:  dictionary with state arguments (fig_num, marker_color,
                     marker_shape, marker_size, show_label)
        """
        if not testing:
            import matplotlib.pyplot as plt

        query_date = cm_utils.get_astropytime(query_date)
        displaying_label = bool(state_args['show_label'])
        if displaying_label:
            label_to_show = state_args['show_label'].lower()
        if not testing:
            plt.figure(state_args['fig_num'])
        for station in stations_to_plot_list:
            ustn = station.upper()
            for a in self.session.query(geo_location.GeoLocation).filter(
                    func.upper(geo_location.GeoLocation.station_name) == ustn):
                pt = {'easting': a.easting, 'northing': a.northing,
                      'elevation': a.elevation}
                X = pt[self.coord[state_args['xgraph']]]
                Y = pt[self.coord[state_args['ygraph']]]
                if not testing:
                    plt.plot(X, Y, color=state_args['marker_color'],
                             marker=state_args['marker_shape'],
                             markersize=state_args['marker_size'],
                             label=a.station_name)
                if displaying_label:
                    if label_to_show == 'name':
                        labeling = a.station_name
                    else:
                        try:
                            ant, rev = self.find_antenna_at_station(a.station_name, query_date)
                        except TypeError:
                            print("{} not found.".format(station))
                            continue
                        if label_to_show == 'num':
                            labeling = ant.strip('A')
                        elif label_to_show == 'ser':
                            p = self.session.query(part_connect.Parts).filter(
                                (part_connect.Parts.hpn == ant) &
                                (part_connect.Parts.hpn_rev == rev))
                            if p.count() == 1:
                                labeling = p.first().manufacturer_number.replace('S/N', '')
                            else:
                                labeling = '-'
                        else:
                            labeling = 'S'
                    if not testing:
                        plt.annotate(labeling, xy=(X, Y), xytext=(X + 2, Y))
        return state_args['fig_num']

    def plot_station_types(self, query_date, state_args, testing=False):
        """
        Plot the various sub-array types

        Return figure number of plot

        Parameters:
        ------------
        query_date:  date to use to check if active.
        state_args:  dictionary with state arguments (fig_num, marker_color,
                     marker_shape, marker_size, show_label)
        """
        if not testing:
            import matplotlib.pyplot as plt
        if state_args['show_state'] == 'active':
            from hera_mc import cm_hookup, cm_revisions
            hookup = cm_hookup.Hookup(query_date, self.session)
            hookup_dict = hookup.get_hookup('cached')

        query_date = cm_utils.get_astropytime(query_date)
        if state_args['station_types'][0] == 'all':
            prefixes_to_plot = 'all'
        else:
            prefixes_to_plot = [x.upper() for x in state_args['station_types']]
        self.get_station_types(add_stations=True)
        for key in self.station_types.keys():
            if prefixes_to_plot == 'all' or key.upper() in prefixes_to_plot:
                stations_to_plot = []
                for loc in self.station_types[key]['Stations']:
                    show_it = True
                    if state_args['show_state'] == 'active':
                        fc = cm_revisions.get_full_revision_keys(loc, hookup_dict)
                        if len(fc) == 0:
                            show_it = False
                    if show_it:
                        stations_to_plot.append(loc)
                state_args['marker_color'] = self.station_types[key]['Marker'][0]
                state_args['marker_shape'] = self.station_types[key]['Marker'][1]
                state_args['marker_size'] = 6
                self.plot_stations(stations_to_plot, query_date, state_args, testing)
        if not testing:
            if state_args['xgraph'].upper() != 'Z' and state_args['ygraph'].upper() != 'Z':
                plt.axis('equal')
            plt.plot(xaxis=state_args['xgraph'], yaxis=state_args['ygraph'])
        return state_args['fig_num']
