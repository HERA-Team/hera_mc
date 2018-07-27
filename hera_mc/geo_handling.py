# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
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
import six
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
    # import matplotlib.pyplot as plt

    if fignm is not False and fignm is not None:
        plt.figure(fignm)
        plt.show()


class Handling:
    """
    Class to allow various manipulations of geo_locations and their properties etc.
    """

    coord = {'E': 'easting', 'N': 'northing', 'Z': 'elevation'}

    def __init__(self, session=None, testing=False):
        """
        session: session on current database. If session is None, a new session
                 on the default database is created and used.
        """
        if session is None:
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.testing = testing

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
        self.get_station_types()
        current_cofa = self.station_types['cofa']['Stations']
        located = self.get_location(current_cofa, 'now')
        if len(located) > 1:
            s = "{} has multiple cofa values.".format(str(current_cofa))
            warnings.warn(s)

        return located

    def get_station_types(self):
        """
        adds a dictionary of sub-arrays (station_types) to the class
             [station_type_name]{'Prefix', 'Description':'...', 'plot_marker':'...', 'stations':[]}
        """
        if self.station_types is not None:
            return
        self.station_types = {}
        for sta in self.session.query(geo_location.StationType):
            self.station_types[sta.station_type_name.lower()] = {'Prefix': sta.prefix.upper(),
                                                                 'Description': sta.description,
                                                                 'Marker': sta.plot_marker, 'Stations': []}
        for loc in self.session.query(geo_location.GeoLocation):
            self.station_types[loc.station_type_name]['Stations'].append(loc.station_name)
            expected_prefix = self.station_types[loc.station_type_name]['Prefix'].upper()
            actual_prefix = loc.station_name[:len(expected_prefix)].upper()
            if expected_prefix != actual_prefix:
                s = "Prefixes don't match: expected {} but got {} for {}".format(expected_prefix, actual_prefix, loc.station_name)
                warnings.warn(s)

    def is_in_database(self, station_name, db_name='geo_location'):
        """
        checks to see if a station_name is in the named database

        return True/False

        Parameters:
        ------------
        station_name:  string name of station
        db_name:  name of database table
        """
        if db_name == 'geo_location':
            station = self.session.query(geo_location.GeoLocation).filter(
                func.upper(geo_location.GeoLocation.station_name) == station_name.upper())
        elif db_name == 'connections':
            station = self.session.query(part_connect.Connections).filter(
                func.upper(part_connect.Connections.upstream_part) == station_name.upper())
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
        connected_antenna = self.session.query(part_connect.Connections).filter(
            (func.upper(part_connect.Connections.upstream_part) == station.upper())
            & (query_date.gps >= part_connect.Connections.start_gpstime))
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
        print("Antenna ", antenna)
        connected_antenna = self.session.query(part_connect.Connections).filter(
            (func.upper(part_connect.Connections.downstream_part) == antenna.upper())
            & (query_date.gps >= part_connect.Connections.start_gpstime))
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

    def get_location(self, to_find_list, query_date):
        """
        Return the location of station_name or antenna_number as contained in to_find.
        This accepts the fact that antennas are sort of stations, even though they are parts

        Parameters:
        ------------
        to_find_list:  station/antenna names to find (must be a list)
        query_date:  astropy Time for contemporary antenna
        """
        self.get_station_types()
        locations = []
        for L in to_find_list:
            station_name = False
            try:
                antenna_number = int(L)
                station_name = self.find_station_of_antenna(antenna_number, query_date)
            except ValueError:
                station_name = L
            if station_name:
                for a in self.session.query(geo_location.GeoLocation).filter(
                        func.upper(geo_location.GeoLocation.station_name) == station_name.upper()):
                    a.gps2Time()
                    a.desc = self.station_types[a.station_type_name]['Description']
                    hera_proj = Proj(proj='utm', zone=a.tile, ellps=a.datum, south=True)
                    a.lon, a.lat = hera_proj(a.easting, a.northing, inverse=True)
                    locations.append(copy.copy(a))
        return locations

    def print_loc_info(self, loc_list):
        """
        Prints out location information as returned from get_location.
        Returns False if provided 'loc' is None, otherwise returns True.
        """
        if loc_list is None or len(loc_list) == 0:
            print("No locations found.")
            return False
        for a in loc_list:
            print('station_name: ', a.station_name)
            print('\teasting: ', a.easting)
            print('\tnorthing: ', a.northing)
            print('\tlon/lat:  ', a.lon, a.lat)
            print('\televation: ', a.elevation)
            print('\tstation description ({}):  {}'.format(a.station_type_name, a.desc))
            print('\tcreated:  ', cm_utils.get_time_for_display(a.created_date))
        return True

    def parse_station_types_to_check(self, sttc):
        self.get_station_types()
        if isinstance(sttc, (six.text_type, six.string_types)):
            if sttc.lower() == 'all':
                return self.station_types.keys()
            elif sttc.lower() == 'default':
                sttc = cm_utils.default_station_prefixes
            else:
                sttc = [sttc]
        sttypes = set()
        for s in sttc:
            if s.lower() in self.station_types.keys():
                sttypes.add(s.lower())
            else:
                for k, st in six.iteritems(self.station_types):
                    if s.upper() == st['Prefix'][:len(s)].upper():
                        sttypes.add(k.lower())
        return sttypes

    def get_ants_installed_since(self, query_date, station_types_to_check='all'):
        """
        Returns list of antennas installed since query_date.

        Parameters
        -----------
        query_date:  date to limit check for installation
        station_types_to_check:  list of stations types to limit check
        """

        station_types_to_check = self.parse_station_types_to_check(station_types_to_check)
        dt = query_date.gps
        found_stations = []
        for a in self.session.query(geo_location.GeoLocation).filter(
                geo_location.GeoLocation.created_gpstime >= dt):
            if a.station_type_name.lower() in station_types_to_check:
                found_stations.append(a.station_name)
        return found_stations

    def get_antenna_label(self, label_to_show, stn, query_date):
        if label_to_show == 'name':
            return stn.station_name
        try:
            ant, rev = self.find_antenna_at_station(stn.station_name, query_date)
        except TypeError:
            return ''.join([x if x.isdigit() else '' for x in stn.station_name])
        if label_to_show == 'num':
            return ant.strip('A')
        if label_to_show == 'ser':
            p = self.session.query(part_connect.Parts).filter(
                (part_connect.Parts.hpn == ant)
                & (part_connect.Parts.hpn_rev == rev))
            if p.count() == 1:
                return p.first().manufacturer_number.replace('S/N', '')
            else:
                return '-'
        return None

    def plot_stations(self, stations_to_plot_list, query_date, **kwargs):
        """
        Plot a list of stations.

        Parameters:
        ------------
        stations_to_plot_list:  list containing station_names (note:  NOT antenna_numbers)
        query_date:  date to use to check if active
        kwargs:  arguments for marker_color, marker_shape, marker_size, show_label, xgraph, ygraph
        """
        # import matplotlib.pyplot as plt

        query_date = cm_utils.get_astropytime(query_date)
        displaying_label = bool(kwargs['show_label'])
        if displaying_label:
            label_to_show = kwargs['show_label'].lower()
        locations = self.get_location(stations_to_plot_list, query_date)
        fig_label = kwargs['xgraph'] + kwargs['ygraph']
        if not self.testing:
            plt.figure(fig_label)
        for a in locations:
            pt = {'easting': a.easting, 'northing': a.northing,
                  'elevation': a.elevation}
            X = pt[self.coord[kwargs['xgraph']]]
            Y = pt[self.coord[kwargs['ygraph']]]
            if not self.testing:
                plt.plot(X, Y, color=kwargs['marker_color'], label=a.station_name,
                         marker=kwargs['marker_shape'], markersize=kwargs['marker_size'])
            if displaying_label:
                labeling = self.get_antenna_label(label_to_show, a, query_date)
                if labeling and not self.testing:
                    plt.annotate(labeling, xy=(X, Y), xytext=(X + 2, Y))
        return fig_label

    def plot_station_types(self, query_date, station_types_to_use, **kwargs):
        """
        Plot the various sub-array types

        Return figure number of plot

        Parameters:
        ------------
        query_date:  date to use to check if active.
        station_types:  station_types or prefixes to plot
        kwargs:  marker_color, marker_shape, marker_size, show_label, xgraph, ygraph
        """
        from hera_mc import cm_hookup, cm_revisions
        # import matplotlib.pyplot as plt
        hookup = cm_hookup.Hookup(query_date, self.session)
        hookup_dict = hookup.get_hookup(hookup.hookup_list_to_cache)
        fig_num = None

        station_types_to_use = self.parse_station_types_to_check(station_types_to_use)
        query_date = cm_utils.get_astropytime(query_date)
        for st in station_types_to_use:
            active_stations = []
            for loc in self.station_types[st]['Stations']:
                if cm_revisions.get_full_revision(loc, hookup_dict):
                    active_stations.append(loc)
            kwargs['marker_color'] = self.station_types[st]['Marker'][0]
            kwargs['marker_shape'] = self.station_types[st]['Marker'][1]
            kwargs['marker_size'] = 6
            fig_num = self.plot_stations(self.station_types[st]['Stations'], query_date, **kwargs)
            if kwargs['show_state'] == 'all':  # Make active stations different
                kwargs['marker_color'] = 'g'
                kwargs['marker_shape'] = 'o'
                kwargs['marker_size'] = 7
                self.plot_stations(active_stations, query_date, **kwargs)
        if not self.testing:
            if kwargs['xgraph'].upper() != 'Z' and kwargs['ygraph'].upper() != 'Z':
                plt.axis('equal')
            plt.plot(xaxis=kwargs['xgraph'], yaxis=kwargs['ygraph'])
        return fig_num
