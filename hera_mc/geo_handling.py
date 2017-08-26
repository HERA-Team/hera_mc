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

import numpy as np
from pyproj import Proj

from hera_mc import mc, part_connect, cm_utils, geo_location, cm_revisions


def cofa(show_cofa=False, session=None):
    """
    Returns location class of current COFA

    Parameters:
    -------------
    show_cofa:  boolean to print out cofa info or just return class
    session:  db session to use
    """
    h = Handling(session)
    located = h.cofa(show_cofa)
    h.close()
    return located


def get_location(location_names, query_date='now', show_location=False,
                 verbosity='m', session=None):
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
    show_location:  boolean to show location or not
    verbosity:  string to specify verbosity
    session:  db session to use
    """
    query_date = cm_utils._get_astropytime(query_date)
    h = Handling(session)
    located = h.get_location(location_names, query_date)
    if show_location:
        h.print_loc_info(located)
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

        Parameters:
        ------------
        show_cofa:  boolean to either show cofa or not
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
            raiseValueError('db not found.')
        if station.count() > 0:
            station_present = True
        else:
            station_present = False
        return station_present

    def find_antenna_at_station(self, station, query_date):
        """
        checks to see what antenna is at a station

        Returns None or the active antenna_name and revision (must be an active
        antenna_name for the query_date)

        Parameters:
        ------------
        station:  station name as string.
        query_date:  is the astropy Time for contemporary antenna
        """

        query_date = cm_utils._get_astropytime(query_date)
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
            antenna_connected = None
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

        query_date = cm_utils._get_astropytime(query_date)
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

    def get_location(self, to_find, query_date, station_types=None):
        """
        Return the location of station_name or antenna_number as contained in to_find.
        This accepts the fact that antennas are sort of stations, even though they are parts

        Parameters:
        ------------
        to_find:  station names to find (must be a list)
        query_date:  astropy Time for contemporary antenna
        station_types: list of station_type prefixes (e.g. HH)
        show_location:   if True, it will print the information
        verbosity:  sets the verbosity of the print
        """
        if station_types is None:
            self.get_station_types(add_stations=True)
            station_types = self.station_types
        found_location = []
        for L in to_find:
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

    def print_loc_info(self, loc, verbosity='h'):
        if loc is None:
            print("No location found.")
            return
        for a in loc:
            if verbosity == 'm' or verbosity == 'h':
                print('station_name: ', a.station_name)
                print('\teasting: ', a.easting)
                print('\tnorthing: ', a.northing)
                print('\tlon/lat:  ', a.lon, a.lat)
                print('\televation: ', a.elevation)
                print('\tstation description ({}):  {}'.format(a.station_type, a.desc))
                print('\tcreated:  ', cm_utils._get_displayTime(a.created_date))
            elif verbosity == 'l':
                print(a)

    def _search_loop(self, stn, at_date, now, m, base_tdelta, full_req):
        """
        To find a fully connected signal path, you must loop through times.
        To speed it up, this has one loop with bigger time steps (but not too
        big to miss connections), then a shorter time step to the desired
        resolution.  The big loop is m*base_tdelta and the smaller is base_tdelta.
        These parameters can be tuned in the future.
        """
        fc = []
        for i in range(1000):  # Just to give some reasonable outer limit
            at_date += TimeDelta(m * base_tdelta, format='sec')
            if at_date > now:
                at_date = now + TimeDelta(10.0, format='sec')
            fc = cm_revisions.get_full_revision(stn, at_date, full_req, self.session)
            if len(fc) == 1:
                at_date -= TimeDelta(m * base_tdelta - 600.0, format='sec')
                fc = cm_revisions.get_full_revision(stn, at_date, full_req, self.session)
                while len(fc) == 0 and at_date < now:
                    at_date += TimeDelta(base_tdelta, format='sec')
                    if at_date > now:
                        at_date = now + TimeDelta(10.0, format='sec')
                    fc = cm_revisions.get_full_revision(stn, at_date, full_req, self.session)
                break
            elif at_date > now:
                break
        return fc, at_date

    def get_all_fully_connected_ever(self, earliest_date=Time('2016-09-01'),
                                     full_req=part_connect.full_connection_parts_paper,
                                     station_types_to_check='all'):
        """
        Returns a list of dictionaries of all of the locations fully connected ever that
        have station_types in station_types_to_check.  The dictonary is defined in
        get_fully_connected_location_at_date.

        It loops through the stations within station_types (which you select, e.g. HH).
        The time loop starts at either when the station was first "installed" or earliest_date,
        whichever is later.  It finds the earliest connection first, then loops over time
        after that.

        Each location is returned as one dict in the list. Dict keys are:
            'station_name': name of station (string, e.g. 'HH27')
            'station_type': type of station (string, e.g. 'HH', 'PI', etc)
            'tile': UTM tile name (string, e.g. '34J'
            'datum': UTM datum (string, e.g. 'WGS84')
            'easting': station UTM easting (float)
            'northing': station UTM northing (float)
            'longitude': station longitude (float)
            'latitude': station latitude (float)
            'elevation': station elevation (float)
            'antenna_number': antenna number (integer)
            'correlator_input_x': correlator input for x (East) pol (string e.g. 'DF7B4')
            'correlator_input_y': correlator input for y (North) pol (string e.g. 'DF7B4')
            'start_date': start of connection in gps seconds (long)
            'stop_date': end of connection in gps seconds (long or None no end time)

        Parameters
        -----------
        earliest_date:  earliest_date to check for connections.
        full_req: list of parts required for a connection to be a 'full' connection
            (default: part_connect.full_connection_parts_paper)
        station_types_to_check:  list of station types to limit check, or 'all' (default: 'all')
        """
        from hera_mc import cm_hookup
        from sqlalchemy import asc
        hookup = cm_hookup.Hookup(self.session)

        base_tdelta = 86400.0  # This the shorter "inner" loop that sets the time resolution.
        m = 10.0  # This multiplier sets the scale of the longer "outer" loop to speed it up.
        if type(station_types_to_check) == str:
            station_types_to_check = station_types_to_check.lower()
        self.get_station_types()
        station_conn = []
        now = cm_utils._get_astropytime('now')
        for k, stn_type in self.station_types.iteritems():
            if station_types_to_check != 'all' and k not in station_types_to_check:
                continue
            for stn in stn_type['Stations']:
                print("Checking {}".format(stn))
                # Get First one to set the starting time for that station.
                ustn = stn.upper()
                conn = self.session.query(part_connect.Connections).filter(
                    func.upper(part_connect.Connections.upstream_part) == ustn).order_by(
                    asc(part_connect.Connections.start_gpstime)).first()
                if conn is None:  # This location was never connected, so move on.
                    continue
                conn.gps2Time()
                if conn.start_date < earliest_date:  # Get the later of the two.
                    at_date = earliest_date
                else:
                    at_date = conn.start_date + TimeDelta(600.0, format='sec')
                # Find the first fully connected signal path from location.
                fc = cm_revisions.get_full_revision(stn, at_date, full_req, self.session)
                if len(fc) == 0 and at_date < now:
                    fc, at_date = self._search_loop(stn, at_date, now, m, base_tdelta, full_req)
                if len(fc) == 0:
                    continue
                station_dict = self.get_fully_connected_location_at_date(stn=stn, at_date=at_date,
                                                                         hookup=hookup, fc=fc, full_req=full_req)
                station_conn.append(station_dict)
                # Get subsequent ones up to 'now'.  To speed up the search, start the next time at the stop time of previous connection.
                k0 = fc[0].hookup['timing'].keys()[0]
                tp = fc[0].hookup['timing'][k0]
                fc_strt = Time(cm_utils.get_date_from_pair(tp['e'][0], tp['n'][0], 'earliest'), format='gps')
                fc_stop = cm_utils.get_date_from_pair(tp['e'][1], tp['n'][1], 'earliest')
                if fc_stop is None or fc_stop > now.gps:
                    continue
                fc_stop = Time(fc_stop, format='gps')
                at_date = fc_stop + TimeDelta(base_tdelta, format='sec')
                while fc_stop is not None:  # Keep searching until there are no more full connections up to now.
                    fc, at_date = self._search_loop(stn, at_date, now, m, base_tdelta, full_req)
                    if len(fc) == 0:
                        break
                    # Found one - add it to list.
                    station_dict = self.get_fully_connected_location_at_date(stn=stn, at_date=at_date,
                                                                             hookup=hookup, fc=fc,
                                                                             full_req=full_req)
                    station_conn.append(station_dict)
                    # Get the connection stop time to start looking for next one.  Break as appropriate
                    k0 = fc[0].hookup['timing'].keys()[0]
                    tp = fc[0].hookup['timing'][k0]
                    fc_stop = cm_utils.get_date_from_pair(tp['e'][1], tp['n'][1], 'earliest')
                    if fc_stop is None:
                        break
                    fc_stop = Time(fc_stop, format='gps')
                    at_date = fc_stop + TimeDelta(base_tdelta, format='sec')
                    if fc_stop > now:
                        break
        return station_conn

    def get_all_fully_connected_at_date(self, at_date,
                                        full_req=part_connect.full_connection_parts_paper,
                                        station_types_to_check='all'):
        """
        Returns a list of dictionaries of all of the locations fully connected at_date
        have station_types in station_types_to_check.  The dictonary is defined in
        get_fully_connected_location_at_date.

        Each location is returned as one dict in the list. Dict keys are:
            'station_name': name of station (string, e.g. 'HH27')
            'station_type': type of station (string, e.g. 'HH', 'PI', etc)
            'tile': UTM tile name (string, e.g. '34J'
            'datum': UTM datum (string, e.g. 'WGS84')
            'easting': station UTM easting (float)
            'northing': station UTM northing (float)
            'longitude': station longitude (float)
            'latitude': station latitude (float)
            'elevation': station elevation (float)
            'antenna_number': antenna number (integer)
            'correlator_input_x': correlator input for x (East) pol (string e.g. 'DF7B4')
            'correlator_input_y': correlator input for y (North) pol (string e.g. 'DF7B4')
            'start_date': start of connection in gps seconds (long)
            'stop_date': end of connection in gps seconds (long or None no end time)

        Parameters
        -----------
        at_date:  date to check for connections
        full_req:  list contining needed parts to be considered complete
        station_types_to_check:  list of station types to limit check, or 'all' [default 'all']
        """
        from hera_mc import cm_hookup
        hookup = cm_hookup.Hookup(self.session)

        at_date = cm_utils._get_astropytime(at_date)
        self.get_station_types()
        station_conn = []
        for k, stn_type in self.station_types.iteritems():
            if station_types_to_check != 'all' and k not in station_types_to_check:
                continue
            for stn in stn_type['Stations']:
                station_dict = self.get_fully_connected_location_at_date(stn=stn,
                                                                         at_date=at_date,
                                                                         hookup=hookup,
                                                                         fc=None,
                                                                         full_req=full_req)
                if len(station_dict.keys()) > 1:
                    station_conn.append(station_dict)
        return station_conn

    def get_fully_connected_location_at_date(self, stn, at_date, hookup, fc=None,
                                             full_req=part_connect.full_connection_parts_paper):
        """
        Returns a dictionary for location stn that is fully connected at_date.  Provides
        the dictonary used in other methods.

        The returned dict keys are:
            'station_name': name of station (string, e.g. 'HH27')
            'station_type': type of station (string, e.g. 'HH', 'PI', etc)
            'tile': UTM tile name (string, e.g. '34J'
            'datum': UTM datum (string, e.g. 'WGS84')
            'easting': station UTM easting (float)
            'northing': station UTM northing (float)
            'longitude': station longitude (float)
            'latitude': station latitude (float)
            'elevation': station elevation (float)
            'antenna_number': antenna number (integer)
            'correlator_input_x': correlator input for x (East) pol (string e.g. 'DF7B4')
            'correlator_input_y': correlator input for y (North) pol (string e.g. 'DF7B4')
            'start_date': start of connection in gps seconds (long)
            'stop_date': end of connection in gps seconds (long or None no end time)

        Parameters
        -----------
        stn:  is the station information to check
        at_date:  date to check for connections, must be an astropy.Time
        hookup:  is to provide a hookup instance to not have to do it everytime
        fc:  is the full hookup/revision, in case you already have it don't call it again
        full_req:  list contining needed parts to be considered complete
        """
        if fc is None:
            fc = cm_revisions.get_full_revision(stn, at_date, full_req, self.session)
        station_dict = {}
        if len(fc) == 1:
            hu = fc[0].hookup
            k0 = hu['hookup'].keys()[0]
            ant_num = hu['hookup'][k0]['e'][0].downstream_part
            # ant_num here is unicode with an A in front of the number (e.g. u'A22').
            # But we just want an integer, so we strip the A and cast it to int
            ant_num = int(ant_num[1:])
            corr = hookup.get_correlator_input_from_hookup(hu)
            fnd = self.get_location([stn], at_date, station_types=self.station_types)[0]
            hera_proj = Proj(proj='utm', zone=fnd.tile, ellps=fnd.datum, south=True)
            strtd = cm_utils.get_date_from_pair(hu['timing'][k0]['e'][0], hu['timing'][k0]['n'][0], 'latest')
            ended = cm_utils.get_date_from_pair(hu['timing'][k0]['e'][1], hu['timing'][k0]['n'][1], 'earliest')
            station_dict = {'station_name': str(fnd.station_name),
                            'station_type': str(fnd.station_type_name),
                            'tile': str(fnd.tile),
                            'datum': str(fnd.datum),
                            'easting': fnd.easting,
                            'northing': fnd.northing,
                            'longitude': fnd.lon,
                            'latitude': fnd.lat,
                            'elevation': fnd.elevation,
                            'antenna_number': ant_num,
                            'correlator_input_x': str(corr['e']),
                            'correlator_input_y': str(corr['n']),
                            'start_date': strtd,
                            'stop_date': ended}
        return station_dict

    def get_cminfo_correlator(self, mc_config_path=None, cm_csv_path=None):
        """
        Returns a dict with info needed by the correlator.

        Dict keys are:
            'antenna_number': Antenna numbers (list of integers)
            'antenna_names': Station names (we use antenna_names because that's
                what they're called in data files) (list of strings)
            'station_type': Station type ('herahex', 'paperimaging', etc.)
                (list of strings)
            'correlator_inputs': Correlator input strings for x/y (e/n)
                polarizations (list of 2 element tuples of strings)
            'antenna_utm_datum_vals': UTM Datum values (list of strings)
            'antenna_utm_tiles': UTM Tile values (list of strings)
            'antenna_utm_eastings': UTM eastings (list of floats)
            'antenna_utm_northings': UTM northings (list of floats)
            'antenna_positions': Antenna positions in standard Miriad coordinates
                (list of 3-element vectors of floats)
            'cm_version': CM git hash (string)

        Note: This method requires pyuvdata
        """
        from pyuvdata import utils as uvutils
        from hera_mc import cm_hookup, cm_handling

        cm_h = cm_handling.Handling(session=self.session)
        cm_version = cm_h.get_cm_version()
        cofa_loc = self.cofa()[0]
        stations_conn = self.get_all_fully_connected_at_date(at_date='now')

        ant_nums = []
        stn_names = []
        stn_types = []
        corr_inputs = []
        tiles = []
        datums = []
        eastings = []
        northings = []
        longitudes = []
        latitudes = []
        elevations = []
        for stn in stations_conn:
            ant_nums.append(stn['antenna_number'])
            stn_names.append(stn['station_name'])
            stn_types.append(stn['station_type'])
            corr_inputs.append((stn['correlator_input_x'], stn['correlator_input_y']))
            tiles.append(stn['tile'])
            datums.append(stn['datum'])
            eastings.append(stn['easting'])
            northings.append(stn['northing'])
            longitudes.append(stn['longitude'])
            latitudes.append(stn['latitude'])
            elevations.append(stn['elevation'])

        ecef_positions = uvutils.XYZ_from_LatLonAlt(latitudes, longitudes, elevations)
        rotecef_positions = uvutils.rotECEF_from_ECEF(ecef_positions.T, cofa_loc.lon)

        return {'antenna_numbers': ant_nums,
                # This is actually station names, not antenna names,
                # but antenna_names is what it's called in pyuvdata
                'antenna_names': stn_names,
                'station_types': stn_types,
                # this is a tuple giving the f-engine names for x, y
                'correlator_inputs': corr_inputs,
                'antenna_utm_datum_vals': datums,
                'antenna_utm_tiles': tiles,
                'antenna_utm_eastings': eastings,
                'antenna_utm_northings': northings,
                'antenna_positions': rotecef_positions,
                'cm_version': cm_version,
                'cofa_lat': cofa_loc.lat,
                'cofa_lon': cofa_loc.lon,
                'cofa_alt': cofa_loc.elevation}

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

    def plot_stations(self, stations_to_plot, query_date, state_args):
        """
        Plot a list of stations.

        Parameters:
        ------------
        stations_to_plot:  list containing station_names (note:  NOT antenna_numbers)
        query_date:  date to use to check if active
        state_args:  dictionary with state arguments (fig_num, marker_color,
                     marker_shape, marker_size, show_label)
        """
        import matplotlib.pyplot as plt

        query_date = cm_utils._get_astropytime(query_date)
        displaying_label = bool(state_args['show_label'])
        if displaying_label:
            label_to_show = state_args['show_label'].lower()
        plt.figure(state_args['fig_num'])
        for station in stations_to_plot:
            ustn = station.upper()
            for a in self.session.query(geo_location.GeoLocation).filter(
                    func.upper(geo_location.GeoLocation.station_name) == ustn):
                pt = {'easting': a.easting, 'northing': a.northing,
                      'elevation': a.elevation}
                __X = pt[self.coord[state_args['xgraph']]]
                __Y = pt[self.coord[state_args['ygraph']]]
                plt.plot(__X, __Y, color=state_args['marker_color'],
                         marker=state_args['marker_shape'],
                         markersize=state_args['marker_size'],
                         label=a.station_name)
                if displaying_label:
                    if label_to_show == 'name':
                        labeling = a.station_name
                    else:
                        ant, rev = self.find_antenna_at_station(a.station_name, query_date)
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
                        plt.annotate(labeling, xy=(__X, __Y), xytext=(__X + 2, __Y))
        return state_args['fig_num']

    def plot_station_types(self, query_date, state_args):
        """
        Plot the various sub-array types

        Return figure number of plot

        Parameters:
        ------------
        query_date:  date to use to check if active.
        state_args:  dictionary with state arguments (fig_num, marker_color,
                     marker_shape, marker_size, show_label)
        """
        import matplotlib.pyplot as plt

        query_date = cm_utils._get_astropytime(query_date)
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
                        fc = cm_revisions.get_full_revision(loc, query_date,
                                                            part_connect.full_connection_parts_paper,
                                                            self.session)
                        if len(fc) == 0:
                            show_it = False
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
