# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Methods for handling locating correlator and various system aspects.
"""

from __future__ import absolute_import, division, print_function

import six
from astropy.time import Time, TimeDelta
from sqlalchemy import func, asc
import numpy as np

from . import mc, part_connect, cm_utils, cm_hookup, cm_revisions
from . import geo_location, geo_handling


class StationInfo:
    stn_info = ['station_name', 'station_type_name', 'tile', 'datum', 'easting', 'northing', 'lon', 'lat',
                'elevation', 'antenna_number', 'correlator_input', 'start_date', 'stop_date', 'epoch']

    def __init__(self, stn=None):
        if isinstance(stn, six.string_types) and stn == 'init_arrays':
            for s in self.stn_info:
                setattr(self, s, [])
        else:
            for s in self.stn_info:
                setattr(self, s, None)
            if stn is not None:
                self.update_stn(stn)

    def update_stn(self, stn):
        if stn is None:
            return
        for s in self.stn_info:
            try:
                a = getattr(stn, s)
            except AttributeError:
                continue
            setattr(self, s, a)

    def update_arrays(self, stn):
        if stn is None:
            return
        for s in self.stn_info:
            try:
                arr = getattr(self, s)
            except AttributeError:
                continue
            arr.append(getattr(stn, s))


class Handling:
    """
    Class to allow various manipulations of correlator inputs etc
    """

    def __init__(self, session=None):
        """
        session: session on current database. If session is None, a new session
                 on the default database is created and used.
        """
        if session is None:  # pragma: no cover
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

    def get_all_fully_connected_at_date(self, at_date, station_types_to_check='default'):
        """
        Returns a list of class StationInfo of all of the locations fully connected at_date
        have station_types in station_types_to_check.

        Each location is returned class StationInfo.  Attributes are:
            'station_name': name of station (string, e.g. 'HH27')
            'station_type_name': type of station (type 'herahexe', etc)
            'tile': UTM tile name (string, e.g. '34J'
            'datum': UTM datum (string, e.g. 'WGS84')
            'easting': station UTM easting (float)
            'northing': station UTM northing (float)
            'lon': station longitude (float)
            'lat': station latitude (float)
            'elevation': station elevation (float)
            'antenna_number': antenna number (integer)
            'correlator_input': correlator input for x (East) pol and y (North) pol (string tuple-pair)
            'start_date': start of connection in gps seconds (long)
            'stop_date': end of connection in gps seconds (long or None no end time)

        Parameters
        -----------
        at_date:  date to check for connections
        station_types_to_check:  list of station types to check, or 'all' ['default']]
                                 it can either be the prefix or the "Name" (e.g. 'herahexe')
        """
        at_date = cm_utils.get_astropytime(at_date)
        self.H = cm_hookup.Hookup(at_date, self.session)
        self.geo.get_station_types()
        station_types_to_check = self.geo.parse_station_types_to_check(station_types_to_check)
        station_conn = []
        for st in station_types_to_check:
            for stn in self.geo.station_types[st]['Stations']:
                station_info = self.get_fully_connected_location_at_date(stn=stn, at_date=at_date)
                if station_info is not None:
                    station_conn.append(station_info)
        self.H = None  # Reset back in case gets called again outside of this method.
        return station_conn

    def get_fully_connected_location_at_date(self, stn, at_date):
        """
        Returns StationInfo class

        Attributes are:
            'station_name': name of station (string, e.g. 'HH27')
            'station_type_name': type of station (type 'herahexe', etc)
            'tile': UTM tile name (string, e.g. '34J'
            'datum': UTM datum (string, e.g. 'WGS84')
            'easting': station UTM easting (float)
            'northing': station UTM northing (float)
            'lon': station longitude (float)
            'lat': station latitude (float)
            'elevation': station elevation (float)
            'antenna_number': antenna number (integer)
            'correlator_input': correlator input for x (East) pol and y (North) pol (string tuple-pair)
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
        station_info = None
        fully_connected = cm_revisions.get_full_revision(stn, hud)
        fully_connected_keys = set()
        fctime = {'start': 0.0, 'end': 1.0E10}
        for i, fc in enumerate(fully_connected):
            if cm_utils.is_active(at_date, fc.started, fc.ended):
                fully_connected_keys.add(fc.hukey)
                if fc.started > fctime['start']:
                    fctime['start'] = fc.started
                if fc.ended is not None:
                    if fc.ended < fctime['end']:
                        fctime['end'] = fc.ended
        if len(fully_connected_keys) == 1:
            k = fully_connected_keys.pop()
            current_hookup = hud[k].hookup
            p = list(current_hookup.keys())[0]
            stn = current_hookup[p][0].upstream_part
            ant_num = current_hookup[p][0].downstream_part
            # ant_num here is unicode with an A in front of the number (e.g. u'A22').
            # But we just want an integer, so we strip the A and cast it to int
            ant_num = int(ant_num[1:])
            corr = {}
            pe = {}
            for p, hu in six.iteritems(current_hookup):
                pe[p] = hud[k].parts_epoch[p]
                cind = part_connect.epoch_corr_huind[pe[p]]
                try:
                    corr[p] = "{}>{}".format(hu[cind].downstream_input_port, hu[cind].downstream_part)
                except IndexError:
                    corr[p] = 'None'
            fnd_list = self.geo.get_location([stn], at_date)
            if not len(fnd_list):
                return None
            if len(fnd_list) > 1:
                print("More than one part found:  ", str(fnd))
                print("Setting to first to continue.")
            fnd = fnd_list[0]
            station_info = StationInfo(fnd)
            station_info.antenna_number = ant_num
            station_info.correlator_input = (str(corr['e']), str(corr['n']))
            station_info.epoch = 'e:{}, n:{}'.format(pe['e'], pe['n'])
            if pe['e'] == pe['n']:
                station_info.epoch = str(pe['e'])
            station_info.start_date = fctime['start']
            station_info.stop_date = fctime['end']
        return station_info

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
        from . import cm_handling

        cm_h = cm_handling.Handling(session=self.session)
        cm_version = cm_h.get_cm_version()
        cofa_loc = self.geo.cofa()[0]
        stations_conn = self.get_all_fully_connected_at_date(
            at_date='now', station_types_to_check=cm_utils.default_station_prefixes)
        stn_arrays = StationInfo('init_arrays')
        for stn in stations_conn:
            stn_arrays.update_arrays(stn)
        # latitudes, longitudes output by get_all_fully_connected_at_date are in degrees
        # XYZ_from_LatLonAlt wants radians
        ecef_positions = uvutils.XYZ_from_LatLonAlt(np.array(stn_arrays.lat) * np.pi / 180.,
                                                    np.array(stn_arrays.lon) * np.pi / 180.,
                                                    stn_arrays.elevation)
        rotecef_positions = uvutils.rotECEF_from_ECEF(ecef_positions,
                                                      cofa_loc.lon * np.pi / 180.)

        return {'antenna_numbers': stn_arrays.antenna_number,
                # This is actually station names, not antenna names,
                # but antenna_names is what it's called in pyuvdata
                'antenna_names': stn_arrays.station_name,
                'station_types': stn_arrays.station_type_name,
                'epoch': stn_arrays.epoch,
                # this is a tuple giving the f-engine names for x, y
                'correlator_inputs': stn_arrays.correlator_input,
                'antenna_utm_datum_vals': stn_arrays.datum,
                'antenna_utm_tiles': stn_arrays.tile,
                'antenna_utm_eastings': stn_arrays.easting,
                'antenna_utm_northings': stn_arrays.northing,
                'antenna_positions': rotecef_positions,
                'cm_version': cm_version,
                'cofa_lat': cofa_loc.lat,
                'cofa_lon': cofa_loc.lon,
                'cofa_alt': cofa_loc.elevation}

    def get_part_at_station_from_type(self, stn, at_date, part_type='post-amp', include_revs=False, include_ports=False):
        """
        input:
            stn: antenna number of format HHi where i is antenna number (string or list of strings)
            at_date: date at which connection is true, format 'YYYY-M-D' or 'now'
        returns:
            dict of {pol:(location, #)}
        """
        parts = {}
        H = cm_hookup.Hookup(at_date, self.session)
        if isinstance(stn, six.string_types):
            stn = [stn]
        hud = H.get_hookup(hpn_list=stn, exact_match=True)
        for k, hu in six.iteritems(hud):
            parts[k] = hu.get_part_in_hookup_from_type(part_type, include_revs=include_revs, include_ports=include_ports)
        return parts

    def publish_summary(self, hlist='default', rev='ACTIVE', exact_match=False,
                        hookup_cols='all', force_new_hookup_dict=True):
        import os.path
        if isinstance(hlist, six.string_types) and hlist.lower() == 'default':
            hlist = cm_utils.default_station_prefixes
        output_file = os.path.expanduser('~/.hera_mc/sys_conn_tmp.html')
        H = cm_hookup.Hookup('now', self.session)
        hookup_dict = H.get_hookup(hpn_list=hlist, rev=rev, port_query='all',
                                   exact_match=exact_match, levels=False,
                                   force_new=force_new_hookup_dict, force_specific=False)
        with open(output_file, 'w') as f:
            H.show_hookup(hookup_dict=hookup_dict, cols_to_show=hookup_cols, levels=False, ports=True,
                          revs=True, state='full', file=f, output_format='html')

        from . import cm_transfer
        if cm_transfer.check_if_main(self.session):
            import subprocess
            location_on_paper1 = 'paper1:/home/davidm/local/src/rails-paper/public'
            sc_command = 'scp -i ~/.ssh/id_rsa_qmaster {} {}'.format(output_file, location_on_paper1)
            subprocess.call(sc_command, shell=True)
            return 'OK'
        else:
            return 'Not on "main"'

    def system_comments(self, system_kw='System', kword='all'):
        col = {'key': ['Keyword'], 'date': ['Posting'], 'comment': ['Comment  <file/url>']}
        for k, v in six.iteritems(col):
            col[k].append(len(v[0]))
        found_entries = []
        for x in self.session.query(part_connect.PartInfo).filter((func.upper(part_connect.PartInfo.hpn) == system_kw.upper())):
            if kword.lower() == 'all' or x.hpn_rev.lower() == kword.lower():
                commlib = '{}  <{}>'.format(x.comment, x.library_file)
                display_time = cm_utils.get_time_for_display(x.posting_gpstime)
                sys_comm = {'key': x.hpn_rev, 'date': display_time, 'comment': commlib}
                found_entries.append(sys_comm)
                for k, v in six.iteritems(sys_comm):
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
