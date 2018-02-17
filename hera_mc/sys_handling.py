# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
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
        self.geo = geo_handling.Handling(self.session)
        self.H = None

    def close(self):
        """
        Close the session
        """
        self.session.close()

    def cofa(self):
        cofa = self.geo.cofa()
        return cofa

    def get_dubitable_list(self, date='now', return_full=False):
        """
        Returns start_time and a list with the dubitable antennas.
        If date is supplied, returns for that date, otherwise now.

        Parameters:
        ------------
        date:  something understandable by cm_utils.get_astropytime
        return_full:  boolean to return the full object as opposed to the csv string
        """

        at_date = cm_utils.get_astropytime(date)
        fnd = []
        for dubi in self.session.query(part_connect.Dubitable):
            start_time = cm_utils.get_astropytime(dubi.start_gpstime)
            stop_time = cm_utils.get_astropytime(dubi.stop_gpstime)
            if cm_utils.is_active(at_date, start_time, stop_time):
                fnd.append(dubi)
        if len(fnd) == 0:
            return None
        if len(fnd) == 1:
            if return_full:
                start = Time(fnd[0].start_gpstime, format='gps')
                stop = fnd[0].stop_gpstime
                if stop is not None:
                    stop = Time(stop, format='gps')
                alist = cm_utils.listify(fnd[0].ant_list)
                return (start, stop, alist)
            else:
                return str(fnd[0].ant_list)

        raise ValueError('Too many open dubitable lists ({}).'.format(len(fnd)))

    def get_all_fully_connected_at_date(self, at_date, station_types_to_check=['HH', 'HA', 'HB']):
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
        station_types_to_check:  list of station types to check, or 'all' [default ['HH', 'HA', 'HB']]
                                 it can either be the prefix or the "Name" (e.g. 'herahexe')
        """
        at_date = cm_utils.get_astropytime(at_date)
        self.H = cm_hookup.Hookup(at_date, self.session)
        self.geo.get_station_types()
        station_types_to_check = self.geo.parse_station_types_to_check(station_types_to_check, add_stations=True)
        station_conn = []
        for st in station_types_to_check:
            for stn in self.geo.station_types[st]['Stations']:
                station_dict = self.get_fully_connected_location_at_date(stn=stn, at_date=at_date)
                if len(station_dict.keys()) > 0:
                    station_conn.append(station_dict)
        self.H = None  # Reset back in case gets called again outside of this method.
        return station_conn

    def get_fully_connected_location_at_date(self, stn, at_date):
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
        """
        if self.H is not None:
            H = self.H
        else:
            H = cm_hookup.Hookup(at_date, self.session)
        hud = H.get_hookup(hpn_list=[stn], exact_match=True)
        station_dict = {}
        fc = cm_revisions.get_full_revision(stn, hud)
        if len(fc) == 1:
            k = fc[0].hukey
            p = fc[0].pkey
            ant_num = hud['hookup'][k][p][0].downstream_part
            # ant_num here is unicode with an A in front of the number (e.g. u'A22').
            # But we just want an integer, so we strip the A and cast it to int
            ant_num = int(ant_num[1:])
            stn_name = hud['parts_epoch']['path'][0]
            stn = cm_hookup.get_parts_from_hookup(stn_name, hud)[k][p]
            corr_name = hud['parts_epoch']['path'][-1]
            corr = cm_hookup.get_parts_from_hookup(corr_name, hud)[k]
            fnd_list = self.geo.get_location([stn[0]], at_date)
            if not len(fnd_list):
                return {}
            if len(fnd_list) > 1:
                print("More than one part found:  ", str(fnd))
                print("Setting to first to continue.")
            fnd = fnd_list[0]

            strtd = hud['timing'][k][p][0]
            ended = hud['timing'][k][p][1]
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
                            'correlator_input_x': str(corr['e'][1]),
                            'correlator_input_y': str(corr['n'][1]),
                            'start_date': strtd,
                            'stop_date': ended}
        return station_dict

    def get_cminfo_correlator(self):
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
        stations_conn = self.get_all_fully_connected_at_date(at_date='now', station_types_to_check=['HH', 'HA', 'HB'])
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

    def get_pam_info(self, stn, at_date, pam_name='post-amp'):
        """
        input:
            stn: antenna number of format HHi where i is antenna number
            at_date: date at which connection is true, format 'YYYY-M-D' or 'now'
        returns:
            dict of {pol:(rcvr location,pam #)}
        """
        pams = {}
        H = cm_hookup.Hookup(at_date, self.session)
        hud = H.get_hookup(hpn_list=[stn], exact_match=True)
        fc = cm_revisions.get_full_revision(stn, hud)
        if len(fc) == 1:
            k = fc[0].hukey
            p = fc[0].pkey
            pams = cm_hookup.get_parts_from_hookup(pam_name, hud)[k]
        return pams

    def publish_summary(self, hlist=['HH'], rev='A', exact_match=False,
                        hookup_cols=['station', 'front-end', 'cable-post-amp(in)', 'post-amp', 'cable-container', 'f-engine', 'level'],
                        force_new_hookup_dict=False):
        import os.path
        output_file = os.path.expanduser('~/.hera_mc/sys_conn_tmp.html')
        location_on_paper1 = 'paper1:/home/davidm/local/src/rails-paper/public'
        H = cm_hookup.Hookup('now', self.session)
        hookup_dict = H.get_hookup(hpn_list=hlist, rev=rev, port_query='all',
                                   exact_match=exact_match, show_levels=True,
                                   force_new=force_new_hookup_dict, force_specific=False)

        with open(output_file, 'w') as f:
            H.show_hookup(hookup_dict=hookup_dict, cols_to_show=hookup_cols, show_levels=True, show_ports=False,
                          show_revs=False, show_state='full', file=f, output_format='html')
        import subprocess
        from hera_mc import cm_transfer
        if cm_transfer.check_if_main():
            sc_command = 'scp -i ~/.ssh/id_rsa_qmaster {} {}'.format(output_file, location_on_paper1)
            subprocess.call(sc_command, shell=True)
            return 'OK'
        else:
            return 'Not on "main"'

    def system_comments(self, system_kw='System', kword='all'):
        col = {'key': ['Keyword'], 'date': ['Posting'], 'comment': ['Comment  <file/url>']}
        for k, v in col.iteritems():
            col[k].append(len(v[0]))
        found_entries = []
        for x in self.session.query(part_connect.PartInfo).filter((func.upper(part_connect.PartInfo.hpn) == system_kw.upper())):
            if kword.lower() == 'all' or x.hpn_rev.lower() == kword.lower():
                commlib = '{}  <{}>'.format(x.comment, x.library_file)
                display_time = cm_utils.get_time_for_display(x.posting_gpstime)
                sys_comm = {'key': x.hpn_rev, 'date': display_time, 'comment': commlib}
                found_entries.append(sys_comm)
                for k, v in sys_comm.iteritems():
                    if len(v) > col[k][1]:
                        col[k][1] = len(v)
        if not len(found_entries):
            return 'None'
        rows = ["\n{:{tkw}s} | {:{pt}s} | {}".format(col['key'][0], col['date'][0], col['comment'][0], tkw=col['key'][1], pt=col['date'][1])]
        rows.append("{}+{}+{}".format((col['key'][1] + 1) * '-', (col['date'][1] + 2) * '-', (col['comment'][1] + 1) * '-'))
        for fnd in found_entries:
            rows.append("{:{tkw}s} | {:{pt}s} | {}".format(fnd['key'], fnd['date'], fnd['comment'],
                                                           tkw=col['key'][1], pt=col['date'][1]))
        comments = '\n'.join(rows)

        return comments
