#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Methods to load all active data for a given date.

"""
from __future__ import absolute_import, division, print_function

import six

from . import cm_utils
from . import cm_partconnect as partconn


class ActiveData:
    """
    Object containing the active parts and connections for a given date.

    Parameters
    ----------
    at_date : str, int, float, Time, datetime
    """

    def __init__(self, session=None, at_date='now'):
        if session is None:  # pragma: no cover
            from . import mc
            db = mc.connect_to_mc_db(None)
            session = db.sessionmaker()
        self.session = session
        self.at_date = cm_utils.get_astropytime(at_date)
        self.parts = None
        self.connections = None
        self.info = None
        self.apriori = None
        self.geo = None

    def set_times(self, at_date):
        """
        Makes sure that at_date and self.at_date are synced and supplies gps time

        Parameters
        ----------
        at_date : astropytime.Time or None
            Date for which to check.  If none, assumes self.at_date


        Returns
        -------
        int
            gps seconds of at_date
        """
        if at_date is not None:
            self.at_date = at_date
        return self.at_date.gps

    def load_parts(self, at_date=None):
        """
        Retrieves all active parts for a given at_date.

        Loads the active parts onto the class and sets the class at_date.
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.parts - keyed on part:rev

        Parameters
        ----------
        at_date : str, int, float, Time, datetime (optional)
            The date for which to check as active, given as anything comprehensible
            to get_astropytime.  If not present uses self.at_date
        """
        at_date = cm_utils.get_astropytime(at_date)
        gps_time = self.set_times(at_date)
        self.parts = {}
        for prt in self.session.query(partconn.Parts).filter((partconn.Parts.start_gpstime <= gps_time)
                                                             & ((partconn.Parts.stop_gpstime > gps_time)
                                                             | (partconn.Parts.stop_gpstime == None))):  # noqa
            key = cm_utils.make_part_key(prt.hpn, prt.hpn_rev)
            self.parts[key] = prt

    def load_connections(self, at_date=None):
        """
        Retrieves all active connections for a given at_date.

        Loads the active parts onto the class and sets the class at_date.
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.connections - has keys 'up' and 'down', each of which
                                   is a dictionary keyed on part:rev for
                                   upstream_part and downstream_part respectively.
        Parameters
        ----------
        at_date : str, int, float, Time, datetime (optional)
            The date for which to check as active, given as anything comprehensible
            to get_astropytime.  If not present uses self.at_date

        Raises
        ------
        ValueError
            If a duplicate is found.
        """

        at_date = cm_utils.get_astropytime(at_date)
        gps_time = self.set_times(at_date)
        self.connections = {'up': {}, 'down': {}}
        check_keys = {'up': [], 'down': []}
        for cnn in self.session.query(partconn.Connections).filter((partconn.Connections.start_gpstime <= gps_time)
                                                                   & ((partconn.Connections.stop_gpstime > gps_time)
                                                                   | (partconn.Connections.stop_gpstime == None))):  # noqa
            chk = cm_utils.make_part_key(cnn.upstream_part, cnn.up_part_rev, cnn.upstream_output_port)
            if chk in check_keys['up']:
                raise ValueError("Duplicate active port {}".format(chk))
            check_keys['up'].append(chk)
            chk = cm_utils.make_part_key(cnn.downstream_part, cnn.down_part_rev, cnn.downstream_input_port)
            if chk in check_keys['down']:
                raise ValueError("Duplicate active port {}".format(chk))
            check_keys['down'].append(chk)
            key = cm_utils.make_part_key(cnn.upstream_part, cnn.up_part_rev)
            self.connections['up'].setdefault(key, {})
            self.connections['up'][key][cnn.upstream_output_port.upper()] = cnn
            key = cm_utils.make_part_key(cnn.downstream_part, cnn.down_part_rev)
            self.connections['down'].setdefault(key, {})
            self.connections['down'][key][cnn.downstream_input_port.upper()] = cnn

    def load_info(self, at_date=None):
        """
        Retrieves all current part infomation (ie. before date).

        Loads the part information up to at_date onto the class and sets the class at_date
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.info - keyed on part:rev

        Parameters
        ----------
        at_date : str, int, float, Time, datetime (optional)
            The date for which to check as active, given as anything comprehensible
            to get_astropytime
        """
        at_date = cm_utils.get_astropytime(at_date)
        gps_time = self.set_times(at_date)
        self.info = {}
        for info in self.session.query(partconn.PartInfo).filter((partconn.PartInfo.posting_gpstime <= gps_time)):
            key = cm_utils.make_part_key(info.hpn, info.hpn_rev)
            self.info.setdefault(key, [])
            self.info[key].append(info)

    def load_apriori(self, at_date=None, rev='A'):
        """
        Retrieves all active apriori status for a given at_date.

        Loads the active apriori data onto the class and sets the class at_date.
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.apriori - keyed on part:rev

        Parameters
        ----------
        at_date : str, int, float, Time, datetime (optional)
            The date for which to check as active, given as anything comprehensible
            to get_astropytime.  If not present uses self.at_date
        rev : str
            Revision of antenna-station (always A)
        """
        at_date = cm_utils.get_astropytime(at_date)
        gps_time = self.set_times(at_date)
        self.apriori = {}
        apriori_keys = []
        for astat in self.session.query(partconn.AprioriAntenna).filter((partconn.AprioriAntenna.start_gpstime <= gps_time)
                                                                        & ((partconn.AprioriAntenna.stop_gpstime > gps_time)
                                                                        | (partconn.AprioriAntenna.stop_gpstime == None))):  # noqa
            key = cm_utils.make_part_key(astat.antenna, rev)
            if key in apriori_keys:
                raise ValueError("{} already has an active apriori state.".format(key))
            apriori_keys.append(key)
            self.apriori[key] = astat

    def load_geo(self, at_date=None):
        """
        Retrieves all current geo_location data (ie. before date).

        Loads the geo data at_date onto the class and sets the class at_date.
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.geo - keyed on part

        Parameters
        ----------
        at_date : str, int, float, Time, datetime (optional)
            The date for which to check as active, given as anything comprehensible
            to get_astropytime
        """
        from . import geo_location
        at_date = cm_utils.get_astropytime(at_date)
        gps_time = self.set_times(at_date)
        self.geo = {}
        for ageo in self.session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.created_gpstime <= gps_time):
            key = cm_utils.make_part_key(ageo.station_name, None)
            self.geo[key] = ageo

    def revs(self, hpn, exact_match=False):
        """
        Returns a list of active revisions for the provided hpn list.  The returned
        list is the concatentated set of revisions found for the provided list.

        The purpose is to find out what active revisions are present in the database.
        E.g., to check for all active revisions for all PAMs, call with hpn='PAM'.  To check
        for revisions for a particular one, call with 'PAM123'.  To guarantee only one part
        one should also set exact_match=True.

        Parameters
        ----------
        hpn : str or list
            HERA part number or list.  Checks equality or startswith, depending on below.
        exact_match : bool
            Flag to look for exact matches to part numbers or not.

        Returns
        -------
        list
            List of revision Namespaces for supplied hpn.  Can show with cm_revisions.show_revisions
        """
        from argparse import Namespace
        hpn = [x.upper() for x in cm_utils.listify(hpn)]
        rev_dict = {}
        for hloop in hpn:
            rev_dict[hloop] = {}
            for part in self.parts.values():
                phup = part.hpn.upper()
                use_this_one = (phup == hloop) if exact_match else phup.startswith(hloop)
                if use_this_one:
                    prup = part.hpn_rev.upper()
                    rev_dict[hloop].setdefault(prup, Namespace(hpn=hloop, rev=prup, number=0,
                                               started=part.start_gpstime, ended=part.stop_gpstime))
                    rev_dict[hloop][prup].number += 1
                    if part.start_gpstime < rev_dict[hloop][prup].started:
                        rev_dict[hloop][prup].started = part.start_gpstime
                    if rev_dict[hloop][prup].ended is not None:
                        if part.stop_gpstime is None or part.stop_gpstime > rev_dict[hloop][prup].ended:
                            rev_dict[hloop][prup].ended = part.stop_gpstime
        hpn_rev = []
        for hloop in sorted(list(rev_dict.keys())):
            for rev in sorted(list(rev_dict[hloop].keys())):
                hpn_rev.append(rev_dict[hloop][rev])
        return hpn_rev
