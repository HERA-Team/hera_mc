#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This finds and displays part hookups.

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
    close_enough = 2.0  # Seconds within which the dates are close enough

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

    def is_data_current(self, data_type, at_date):
        """
        Determines if the class data of type data_type is current at at_date.

        Parameters
        ----------
        data_type : str
            One of the allowed data_types:  parts, connections, info, apriori
        at_date : astropytime.Time or None
            Date for which to check.  If none, assumes match to self.at_date

        Returns
        -------
        bool
            True if current
        """

        if getattr(self, data_type) is None:
            return False
        if at_date is None or abs(at_date.gps - self.at_date.gps) < self.close_enough:
            return True
        return False

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
        Sets this object's at_date and loads the active parts on to the object.
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
        if self.is_data_current('parts', at_date):
            return
        gps_time = self.set_times(at_date)
        self.parts = {}
        for prt in self.session.query(partconn.Parts).filter((partconn.Parts.start_gpstime <= gps_time)
                                                             & ((partconn.Parts.stop_gpstime >= gps_time)
                                                             | (partconn.Parts.stop_gpstime == None))):  # noqa
            key = cm_utils.make_part_key(prt.hpn, prt.hpn_rev)
            self.parts[key] = prt

    def load_connections(self, at_date=None):
        """
        Retrieves all active connections for a given at_date.  If a part:rev:port
        connection already exists, it will generate an error.
        If at_date is None, uses self.at_date.  If not, will redefine self.at_date

        Writes class dictionary:
                self.connections - has keys 'up' and 'down', each of which
                                   is a dictionary keyed on part:rev for
                                   upstream_part and downstream_part respectively.
        Parameters
        ----------
        at_date : str, int, float, Time, datetime (optional)
            The date for which to check as active, given as anything comprehensible
            to get_astropytime.  If not present uses self.at_date
        """

        at_date = cm_utils.get_astropytime(at_date)
        if self.is_data_current('connections', at_date):
            return
        gps_time = self.set_times(at_date)
        self.connections = {'up': {}, 'down': {}}
        check_keys = {'up': [], 'down': []}
        for cnn in self.session.query(partconn.Connections).filter((partconn.Connections.start_gpstime <= gps_time)
                                                                   & ((partconn.Connections.stop_gpstime >= gps_time)
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

    def get_info(self, at_date=None):
        """
        Retrieves all current part infomation (ie. before date).
        If at_date is None, uses class at_date

        Writes class dictionary:
                self.info - keyed on part:rev

        Parameters
        ----------
        at_date : str, int, float, Time, datetime (optional)
            The date for which to check as active, given as anything comprehensible
            to get_astropytime
        """
        at_date = cm_utils.get_astropytime(at_date)
        if self.is_data_current('info', at_date):
            return
        gps_time = self.set_times(at_date)
        self.info = {}
        for info in self.session.query(partconn.PartInfo).filter((partconn.PartInfo.posting_gpstime <= gps_time)):
            key = cm_utils.make_part_key(info.hpn, info.hpn_rev)
            self.info.setdefault(key, [])
            self.info[key].append(info)

    def load_apriori(self, at_date=None, rev='A'):
        """
        Retrieves apriori status for a given at_date.
        If at_date is None, uses self.at_date.  If not, will redefine self.at_date

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
        if self.is_data_current('apriori', at_date):
            return
        gps_time = self.set_times(at_date)
        self.apriori = {}
        for astat in self.session.query(partconn.AprioriAntenna).filter((partconn.AprioriAntenna.start_gpstime <= gps_time)
                                                                        & ((partconn.AprioriAntenna.stop_gpstime >= gps_time)
                                                                        | (partconn.AprioriAntenna.stop_gpstime == None))):  # noqa
            key = cm_utils.make_part_key(astat.antenna, rev)
            self.apriori[key] = astat.status

    def check(self, at_date=None):
        """
        Checks self.parts and self.connections to make sure that all connections have an
        associated active part.  Reads in data or connections if not current. Prints out a
        message if not true.

        Parameters
        ----------
        at_date : str, int, float, Time, datetime (optional)
            The date for which to check as active if either all_parts or all_connections are None,
            given as anything comprehensible to get_astropytime
        """
        at_date = cm_utils.get_astropytime(at_date)
        if at_date is None:
            at_date = self.at_date
        if not self.is_data_current('parts', at_date):
            self.load_parts(at_date=at_date)
        if not self.is_data_current('connections', at_date):
            self.load_connections(at_date=at_date)
        full_part_set = list(self.parts.keys())
        full_conn_set = set(list(self.connections['up']) + list(self.connections['down']))
        missing_parts = []
        for key in full_conn_set:
            if key not in full_part_set:
                missing_parts.append(key)
        if len(missing_parts):
            for key in missing_parts:
                print("{} is not listed as an active part even though listed in an active connection.".format(key))
