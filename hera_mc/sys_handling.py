# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Methods for handling locating correlator and various system aspects.
"""

from __future__ import absolute_import, division, print_function

from astropy.time import Time, TimeDelta
from sqlalchemy import func, asc
import numpy as np

from hera_mc import mc, part_connect, cm_utils, cm_hookup, cm_revisions
from hera_mc import geo_location, geo_handling


class Handling:
    """
    Class to allow various manipulations of correlator inputs etc
    """

    def __init__(self, session=None, hookup_list_to_cache=['HH']):
        """
        session: session on current database. If session is None, a new session
                 on the default database is created and used.
        """
        if session is None:
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.hookup_list_to_cache = hookup_list_to_cache
        self.hookup = cm_hookup.Hookup(self.session, hookup_list_to_cache=hookup_list_to_cache)
        self.geo = geo_handling.Handling(self.session)

    def close(self):
        """
        Close the session
        """
        self.session.close()

    def cofa(self):
        cofa = self.geo.cofa()
        return cofa

    def _search_loop(self, stn, at_date, now, m, base_tdelta):
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
            fc = cm_revisions.get_full_revision(stn, at_date, self.session, hookup_list_to_cache=self.hookup_list_to_cache)
            if len(fc) == 1:
                at_date -= TimeDelta(m * base_tdelta - 600.0, format='sec')
                fc = cm_revisions.get_full_revision(stn, at_date, self.session, hookup_list_to_cache=self.hookup_list_to_cache)
                while len(fc) == 0 and at_date < now:
                    at_date += TimeDelta(base_tdelta, format='sec')
                    if at_date > now:
                        at_date = now + TimeDelta(10.0, format='sec')
                    fc = cm_revisions.get_full_revision(stn, at_date, self.session, hookup_list_to_cache=self.hookup_list_to_cache)
                break
            elif at_date > now:
                break
        return fc, at_date

    def get_all_fully_connected_ever(self, earliest_date=Time('2016-09-01'),
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
        station_types_to_check:  list of station types to limit check, or 'all' (default: 'all')
        """

        base_tdelta = 86400.0  # This the shorter "inner" loop that sets the time resolution.
        m = 10.0  # This multiplier sets the scale of the longer "outer" loop to speed it up.
        if type(station_types_to_check) == str:
            station_types_to_check = station_types_to_check.lower()
        self.geo.get_station_types()
        station_conn = []
        now = cm_utils._get_astropytime('now')
        for k, stn_type in self.geo.station_types.iteritems():
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
                fc = cm_revisions.get_full_revision(stn, at_date, self.session, hookup_list_to_cache=self.hookup_list_to_cache)
                if len(fc) == 0 and at_date < now:
                    fc, at_date = self._search_loop(stn, at_date, now, m, base_tdelta)
                if len(fc) == 0:
                    continue
                station_dict = self.get_fully_connected_location_at_date(stn=stn, at_date=at_date, fc=fc)
                if station_dict is None:
                    continue
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
                    fc, at_date = self._search_loop(stn, at_date, now, m, base_tdelta)
                    if len(fc) == 0:
                        break
                    # Found one - add it to list.
                    station_dict = self.get_fully_connected_location_at_date(stn=stn, at_date=at_date, fc=fc)
                    if station_dict is None:
                        break
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

    def get_all_fully_connected_at_date(self, at_date, station_types_to_check='all'):
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
        station_types_to_check:  list of station types to limit check, or 'all' [default 'all']
        """
        at_date = cm_utils._get_astropytime(at_date)
        self.geo.get_station_types()
        station_conn = []
        for k, stn_type in self.geo.station_types.iteritems():
            if station_types_to_check != 'all' and k not in station_types_to_check:
                continue
            for stn in stn_type['Stations']:
                station_dict = self.get_fully_connected_location_at_date(stn=stn,
                                                                         at_date=at_date,
                                                                         fc=None)
                if len(station_dict.keys()) > 1:
                    station_conn.append(station_dict)
        return station_conn

    def get_fully_connected_location_at_date(self, stn, at_date, fc=None):
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
        """
        if fc is None:
            fc = cm_revisions.get_full_revision(stn, at_date, self.session, hookup_list_to_cache=self.hookup_list_to_cache)
        station_dict = {}
        if len(fc) == 1:
            hu = fc[0].hookup
            if len(hu['hookup'].keys()):
                k0 = hu['hookup'].keys()[0]
            else:
                return None
            ant_num = hu['hookup'][k0]['e'][0].downstream_part
            # ant_num here is unicode with an A in front of the number (e.g. u'A22').
            # But we just want an integer, so we strip the A and cast it to int
            ant_num = int(ant_num[1:])
            corr = cm_hookup.get_correlator_input_from_hookup(hu)
            stn = cm_hookup.get_station_from_hookup(hu)
            fnd_list = self.geo.get_location([stn], at_date, station_types=self.geo.station_types)
            if not len(fnd_list):
                return station_dict
            if len(fnd_list) > 1:
                print("More than one part found:  ", str(fnd))
                print("Setting to first to continue.")
            fnd = fnd_list[0]

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
        from hera_mc import cm_handling

        cm_h = cm_handling.Handling(session=self.session)
        cm_version = cm_h.get_cm_version()
        cofa_loc = self.geo.cofa()[0]
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
        # latitudes, longitudes output by get_all_fully_connected_at_date are in degrees
        # XYZ_from_LatLonAlt wants radians
        ecef_positions = uvutils.XYZ_from_LatLonAlt(np.array(latitudes) * np.pi / 180.,
                                                    np.array(longitudes) * np.pi / 180.,
                                                    elevations)
        rotecef_positions = uvutils.rotECEF_from_ECEF(ecef_positions.T,
                                                      cofa_loc.lon * np.pi / 180.)

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

    def get_pam_info(self, stn, at_date, fc=None):
        """
        input:
            stn: antenna number of format HHi where i is antenna number
            at_date: date at which connection is true, format 'YYYY-M-D' or 'now'
        returns:
            dict of {pol:(rcvr location,pam #)}
        """
        at_date = cm_utils._get_astropytime(at_date)
        fc = cm_revisions.get_full_revision(stn, at_date, self.session, hookup_list_to_cache=self.hookup_list_to_cache)
        hu = fc[0].hookup
        pams = cm_hookup.get_pam_from_hookup(hu)
        return pams

    def publish_summary(self, hlist=['HH'], rev='A', exact_match=False,
                        hookup_cols=['station', 'front-end', 'cable-post-amp(in)', 'post-amp', 'cable-container', 'f-engine', 'level'],
                        force_new_hookup_dict=True, force_specific_hookup_dict=False):
        output_file = 'sys_conn_tmp.html'
        location_on_paper1 = 'paper1:/home/davidm/local/src/rails-paper/public'
        hookup_dict = self.hookup.get_hookup(hpn_list=hlist, rev=rev, port_query='all',
                                             at_date='now', exact_match=exact_match, show_levels=True,
                                             force_new=force_new_hookup_dict, force_specific=force_specific_hookup_dict)

        with open(output_file, 'w') as f:
            self.hookup.show_hookup(hookup_dict=hookup_dict, cols_to_show=hookup_cols, show_levels=True, show_ports=False,
                                    show_revs=False, show_state='full', file=f, output_format='html')
        import subprocess
        from hera_mc import cm_transfer
        if cm_transfer.check_if_main():
            sc_command = 'scp -i ~/.ssh/id_rsa_qmaster {} {}'.format(output_file, location_on_paper1)
            subprocess.call(sc_command, shell=True)
            return 'OK'
        else:
            print('You are not on "main"')
            return 'Not on "main"'
