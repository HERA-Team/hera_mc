# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Methods for handling locating correlator and various system aspects."""

from __future__ import absolute_import, division, print_function

import six
from sqlalchemy import func, and_, or_
import numpy as np

from . import mc, cm_partconnect, cm_utils, cm_sysdef, cm_hookup
from . import geo_handling


class SystemInfo:
    """
    Object containing system information, a convenience for the system info methods below.

    Parameters
    ----------
    stn : None or geo_handling object.  If None, it initializes a class with empty lists.
        Otherwise, it initializes based on the geo_handling object class.
        Anything else will generate an error.

    """

    sys_info = ['station_name', 'station_type_name', 'tile', 'datum', 'easting',
                'northing', 'lon', 'lat',
                'elevation', 'antenna_number', 'correlator_input', 'start_date',
                'stop_date', 'epoch']

    def __init__(self, stn=None):
        if stn is None:
            for s in self.sys_info:
                setattr(self, s, [])
        else:
            for s in self.sys_info:
                setattr(self, s, None)
                try:
                    a = getattr(stn, s)
                except AttributeError:
                    continue
                setattr(self, s, a)

    def update_arrays(self, stn):
        """
        Will update the object based on the supplied station information.

        Parameters
        ----------
        stn : geo_handling object or None
            Contains the init station information.  If None, it will initial a blank object.
        """
        if stn is None:
            return
        for s in self.sys_info:
            try:
                arr = getattr(self, s)
            except AttributeError:  # pragma: no cover
                continue
            arr.append(getattr(stn, s))


class Handling:
    """
    Class to allow various manipulations of correlator inputs etc.

    Parameters
    ----------
    session : object
        session on current database. If session is None, a new session
        on the default database is created and used.

    """

    def __init__(self, session=None):
        if session is None:  # pragma: no cover
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.geo = geo_handling.Handling(self.session)
        self.H = None
        self.sysdef = cm_sysdef.Sysdef()
        self.apriori_status_set = None

    def close(self):  # pragma: no cover
        """Close the session."""
        self.session.close()

    def cofa(self):
        """
        Return the geographic information for the center-of-array.

        Returns
        -------
        object
            Geo object for the center-of-array (cofa)

        """
        cofa = self.geo.cofa()
        return cofa

    def get_connected_stations(self, at_date, hookup_type=None):
        """
        Return a list of class SystemInfo of all of the stations connected at_date.

        Each location is returned class SystemInfo.  Attributes are:
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
            'correlator_input': correlator input for x (East) pol and y (North) pol
                (string tuple-pair)
            'timing': start and stop gps seconds for both pols

        Parameters
        ----------
        at_date : str, int
            Date to check for connections.  Anything intelligible by cm_utils.get_astropytime
        hookup_type : str
            Type of hookup to use (current observing system is 'parts_hera').
            If 'None' it will determine which system it thinks it is based on
            the part-type.  The order in which it checks is specified in cm_sysdef.
            Only change if you know you want a different system (like 'parts_paper').

        Returns
        -------
        list
            List of stations connected.

        """
        at_date = cm_utils.get_astropytime(at_date)
        HU = cm_hookup.Hookup(self.session)
        hud = HU.get_hookup(hpn=cm_sysdef.hera_zone_prefixes, pol='all', at_date=at_date,
                            exact_match=False, use_cache=False, hookup_type=hookup_type)
        station_conn = []
        found_keys = list(hud.keys())
        found_stations = [x.split(':')[0] for x in found_keys]
        station_geo = self.geo.get_location(found_stations, at_date)
        for i, key in enumerate(found_keys):
            stn, rev = cm_utils.split_part_key(key)
            ant_num = int(stn[2:])
            station_info = SystemInfo(station_geo[i])
            station_info.antenna_number = ant_num
            current_hookup = hud[key].hookup
            corr = {}
            pe = {}
            station_info.timing = {}
            for ppkey, hu in six.iteritems(current_hookup):
                pol = ppkey[0].lower()
                pe[pol] = hud[key].hookup_type[ppkey]
                cind = self.sysdef.corr_index[pe[pol]] - 1  # The '- 1' makes it the downstream_part
                try:
                    corr[pol] = "{}>{}".format(
                        hu[cind].downstream_input_port, hu[cind].downstream_part)
                except IndexError:  # pragma: no cover
                    corr[pol] = 'None'
                station_info.timing[pol] = hud[key].timing[ppkey]
            if corr['e'] == 'None' and corr['n'] == 'None':
                continue
            station_info.correlator_input = (str(corr['e']), str(corr['n']))
            station_info.epoch = 'e:{}, n:{}'.format(pe['e'], pe['n'])
            station_conn.append(station_info)
        return station_conn

    def get_cminfo_correlator(self, hookup_type=None):
        """
        Return a dict with info needed by the correlator.

        Note: This method requires pyuvdata

        Parameters
        ----------
        hookup_type : str or None
            Type of hookup to use (current observing system is 'parts_hera').
            If 'None' it will determine which system it thinks it is based on
            the part-type.  The order in which it checks is specified in cm_sysdef.
            Only change if you know you want a different system (like 'parts_paper').
            Default is None.

        Returns
        -------
        dict
            cm info formatted for the correlator.
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

        """
        from pyuvdata import utils as uvutils
        from . import cm_handling

        cm_h = cm_handling.Handling(session=self.session)
        cm_version = cm_h.get_cm_version()
        cofa_loc = self.geo.cofa()[0]
        cofa_xyz = uvutils.XYZ_from_LatLonAlt(cofa_loc.lat * np.pi / 180.,
                                              cofa_loc.lon * np.pi / 180.,
                                              cofa_loc.elevation)
        stations_conn = self.get_connected_stations(at_date='now', hookup_type=hookup_type)
        stn_arrays = SystemInfo()
        for stn in stations_conn:
            stn_arrays.update_arrays(stn)
        # latitudes, longitudes output by get_connected_stations are in degrees
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
                'cofa_alt': cofa_loc.elevation,
                'cofa_X': cofa_xyz[0],
                'cofa_Y': cofa_xyz[1],
                'cofa_Z': cofa_xyz[2]}

    def get_part_at_station_from_type(self, stn, at_date, part_type, include_revs=False,
                                      include_ports=False, hookup_type=None):
        """
        Get the part number at a given station of a given part type.

        E.g. find the 'post-amp' at station 'HH68'.

        Parameters
        ----------
        stn : str, list
            Antenna number of format HHi where i is antenna number (string or list of strings)
        at_date : str
            Date at which connection is true, format 'YYYY-M-D' or 'now'
        part_type : str
            Part type to look for
        include_revs : bool
            Flag whether to include all revisions.  Default is False
        include_ports : bool
            Flag whether to include ports.  Default is False
        hookup_type : str
            Type of hookup to use (current observing system is 'parts_hera').
            If 'None' it will determine which system it thinks it is based on
            the part-type.  The order in which it checks is specified in cm_sysdef.
            Only change if you know you want a different system (like 'parts_paper').
            Default is None.

        Returns
        -------
        dict
            {pol:(location, #)}

        """
        parts = {}
        H = cm_hookup.Hookup(self.session)
        if isinstance(stn, six.string_types):
            stn = [stn]
        hud = H.get_hookup(hpn=stn, at_date=at_date, exact_match=True, hookup_type=hookup_type)
        for k, hu in six.iteritems(hud):
            parts[k] = hu.get_part_from_type(
                part_type, include_revs=include_revs, include_ports=include_ports)
        return parts

    def publish_summary(self, hlist=['default'], exact_match=False, hookup_cols='all',
                        sortby='node,station'):
        """
        Publish the hookup on hera.today.

        Parameters
        ----------
        hlist : list
            List of prefixes or stations to use in summary.
            Default is the "default" prefix list in cm_utils.
        exact_match : bool
            Flag for exact_match or included characters.
        hookup_cols : str, list
            List of hookup columns to use, or 'all'.

        Returns
        -------
        str
            Status string.  "OK" or "Not on 'main'"

        """
        import os.path
        if hlist[0].lower() == 'default':
            hlist = cm_sysdef.hera_zone_prefixes
        output_file = os.path.expanduser('~/.hera_mc/sys_conn_tmp.html')
        H = cm_hookup.Hookup(self.session)
        hookup_dict = H.get_hookup(hpn=hlist, pol='all', at_date='now',
                                   exact_match=exact_match, hookup_type=None)
        H.show_hookup(hookup_dict=hookup_dict, cols_to_show=hookup_cols,
                      state='full', ports=True, revs=True,
                      sortby=sortby, filename=output_file, output_format='html')

    def get_apriori_status_for_antenna(self, antenna, at_date='now'):
        """
        Get the "apriori" status of an antenna station (e.g. HH12) at a date.

        The status enum list may be found by module
        cm_partconnect.get_apriori_antenna_status_enum().

        Parameters
        ----------
        ant : str
            Antenna station designator (e.g. HH12, HA330) it is a single string
        at_date : str or int
            Date to look for. Anything intelligible by cm_utils.get_astropytime.

        Returns
        -------
        str
            The apriori antenna status as a string.  Returns None if not in table.

        """
        ant = antenna.upper()
        at_date = cm_utils.get_astropytime(at_date).gps
        cmapa = cm_partconnect.AprioriAntenna
        apa = self.session.query(cmapa).filter(
            or_(and_(func.upper(cmapa.antenna) == ant, cmapa.start_gpstime <= at_date,
                     cmapa.stop_gpstime.is_(None)),
                and_(func.upper(cmapa.antenna) == ant, cmapa.start_gpstime <= at_date,
                     cmapa.stop_gpstime > at_date))).first()
        if apa is not None:
            return apa.status

    def get_apriori_antennas_with_status(self, status, at_date='now'):
        """
        Get a list of all antennas with the provided status query at_date.

        Parameters
        ----------
        status : str
            Apriori antenna status type (see cm_partconnect.get_apriori_antenna_status_enum())
        at_date : str or int
            Date for which to get apriori state -- anything
            cm_utils.get_astropytime can handle.

        Returns
        -------
        list of str
            List of the antenna station designators with the specified status.

        """
        at_date = cm_utils.get_astropytime(at_date).gps
        ap_ants = []
        cmapa = cm_partconnect.AprioriAntenna
        for apa in self.session.query(cmapa).filter(
            or_(and_(cmapa.status == status, cmapa.start_gpstime <= at_date,
                     cmapa.stop_gpstime.is_(None)),
                and_(cmapa.status == status, cmapa.start_gpstime <= at_date,
                     cmapa.stop_gpstime > at_date))):
            ap_ants.append(apa.antenna)
        return ap_ants

    def get_apriori_antenna_status_set(self, at_date='now'):
        """
        Get a dictionary with the antennas for each apriori status type.

        Parameters
        ----------
        at_date : str or int
            Date for which to get apriori state -- anything
            cm_utils.get_astropytime can handle.

        Returns
        -------
        dict
            dictionary of antennas, keyed on the apriori antenna status value
            containing the antennas with that status value

        """
        ap_stat = {}
        for _status in cm_partconnect.get_apriori_antenna_status_enum():
            ap_stat[_status] = self.get_apriori_antennas_with_status(_status, at_date=at_date)
        return ap_stat

    def get_apriori_antenna_status_for_rtp(self, status, at_date='now'):
        """
        Get a csv-string of all antennas for an apriori status for RTP.

        Parameters
        ----------
        status : str
            Apriori antenna status type (see cm_partconnect.get_apriori_antenna_status_enum())
        at_date : str or int
            Date for which to get apriori state -- anything
            cm_utils.get_astropytime can handle.  Default is 'now'

        Returns
        -------
        str
            csv string of antennas of a given apriori status

        """
        return ','.join(self.get_apriori_antennas_with_status(status=status, at_date=at_date))
