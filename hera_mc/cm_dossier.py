#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This finds and displays part hookups.

"""
from __future__ import absolute_import, division, print_function

import six

from . import cm_sysdef, cm_utils
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

    def get_parts(self, at_date=None):
        """
        Retrieves all active parts for a given at_date.
        If at_date is None, uses self.at_date.  If not, will redefine self.at_date

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
                                                             | (partconn.Parts.stop_gpstime == None))):
            key = cm_utils.make_part_key(prt.hpn, prt.hpn_rev)
            self.parts[key] = prt

    def get_connections(self, at_date=None):
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
                                                                   | (partconn.Connections.stop_gpstime == None))):
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

    def get_apriori(self, at_date=None, rev='A'):
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
                                                                        | (partconn.AprioriAntenna.stop_gpstime == None))):
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
            self.get_parts(at_date=at_date)
        if not self.is_data_current('connections', at_date):
            self.get_connections(at_date=at_date)
        full_part_set = list(self.parts.keys())
        full_conn_set = set(list(self.connections['up']) + list(self.connections['down']))
        missing_parts = []
        for key in full_conn_set:
            if key not in full_part_set:
                missing_parts.append(key)
        if len(missing_parts):
            for key in missing_parts:
                print("{} is not listed as an active part even though listed in an active connection.".format(key))


class HookupEntry(object):
    """
    This is the structure of the hookup entry.  All are keyed on polarization.

    Parameters
    ----------
    entry_key : str
        Entry key to use for the entry.  Must be None if input_dict is not None.
    sysdef : str
        Name of part type system for the hookup.  Must be None if input_dict is not None.
    input_dict : dict
        Dictionary with seed hookup.  If it is None, entry_key and sysdef must both be provided.
    """
    def __init__(self, entry_key=None, sysdef=None, input_dict=None):
        if input_dict is not None:
            if entry_key is not None:
                raise ValueError('cannot initialize HookupEntry with an '
                                 'entry_key and a dict')
            if sysdef is not None:
                raise ValueError('cannot initialize HookupEntry with an '
                                 'sysdef and a dict')
            self.entry_key = input_dict['entry_key']
            hookup_connections_dict = {}
            for pol, conn_list in six.iteritems(input_dict['hookup']):
                new_conn_list = []
                for conn_dict in conn_list:
                    new_conn_list.append(partconn.get_connection_from_dict(conn_dict))
                hookup_connections_dict[pol] = new_conn_list
            self.hookup = hookup_connections_dict
            self.fully_connected = input_dict['fully_connected']
            self.hookup_type = input_dict['hookup_type']
            self.columns = input_dict['columns']
            self.timing = input_dict['timing']
            self.sysdef = cm_sysdef.Sysdef(input_dict=input_dict['sysdef'])
        else:
            if entry_key is None:
                raise ValueError('Must initialize HookupEntry with an '
                                 'entry_key and sysdef')
            if sysdef is None:
                raise ValueError('Must initialize HookupEntry with an '
                                 'entry_key and sysdef')
            self.entry_key = entry_key
            self.hookup = {}  # actual hookup connection information
            self.fully_connected = {}  # flag if fully connected
            self.hookup_type = {}  # name of hookup_type
            self.columns = {}  # list with the actual column headers in hookup
            self.timing = {}  # aggregate hookup start and stop
            self.sysdef = sysdef

    def __repr__(self):
        s = "<{}:  {}>\n".format(self.entry_key, self.hookup_type)
        s += "{}\n".format(self.hookup)
        s += "{}\n".format(self.fully_connected)
        s += "{}\n".format(self.timing)
        return s

    def _to_dict(self):
        """
        Convert this object to a dict (so it can be written to json)
        """
        hookup_connections_dict = {}
        for pol, conn_list in six.iteritems(self.hookup):
            new_conn_list = []
            for conn in conn_list:
                new_conn_list.append(conn._to_dict())
            hookup_connections_dict[pol] = new_conn_list
        return {'entry_key': self.entry_key, 'hookup': hookup_connections_dict,
                'fully_connected': self.fully_connected,
                'hookup_type': self.hookup_type, 'columns': self.columns,
                'timing': self.timing, 'sysdef': self.sysdef._to_dict()}

    def get_hookup_type_and_column_headers(self, pol, part_types_found):
        """
        The columns in the hookup contain parts in the hookup chain and the column headers are
        the part types contained in that column.  This returns the headers for the retrieved hookup.

        It just checks which hookup_type the parts are in and keeps however many
        parts are used.

        Parameters
        ----------
        pol : str
            Polarization type, 'e' or 'n' for HERA (specified in 'cm_sysdef')
        part_types_found : list
            List of the part types that were found
        """
        self.hookup_type[pol] = None
        self.columns[pol] = []
        if len(part_types_found) == 0:
            return
        is_this_one = False
        for sp in self.sysdef.checking_order:
            for part_type in part_types_found:
                if part_type not in self.sysdef.full_connection_path[sp]:
                    break
            else:
                is_this_one = sp
                break
        if not is_this_one:
            print('Parts did not conform to any hookup_type')
            return
        else:
            self.hookup_type[pol] = is_this_one
            for c in self.sysdef.full_connection_path[is_this_one]:
                if c in part_types_found:
                    self.columns[pol].append(c)

    def add_timing_and_fully_connected(self, pol):
        """
        Method to add the timing and fully_connected flag for the hookup.

        Parameters
        ----------
        pol : str
            Polarization type, 'e' or 'n' for HERA (specified in 'cm_sysdef')
        """
        if self.hookup_type[pol] is not None:
            full_hookup_length = len(self.sysdef.full_connection_path[self.hookup_type[pol]]) - 1
        else:
            full_hookup_length = -1
        latest_start = 0
        earliest_stop = None
        for c in self.hookup[pol]:
            if c.start_gpstime > latest_start:
                latest_start = c.start_gpstime
            if c.stop_gpstime is None:
                pass
            elif earliest_stop is None:
                earliest_stop = c.stop_gpstime
            elif c.stop_gpstime < earliest_stop:
                earliest_stop = c.stop_gpstime
        self.timing[pol] = [latest_start, earliest_stop]
        self.fully_connected[pol] = len(self.hookup[pol]) == full_hookup_length
        self.columns[pol].append('start')
        self.columns[pol].append('stop')

    def get_part_in_hookup_from_type(self, part_type, include_revs=False, include_ports=False):
        """
        Retrieve the part name for a given part_type from a hookup

        Parameters
        ----------
        part_type : str
            String of valid part type in hookup_dict (e.g. 'snap' or 'feed')
        include_revs : bool
            Flag to include revision number
        include_ports : bool
            Flag to include the associated ports to the part

        Returns
        -------
        dict
            Dictionary keyed on polarization for actual installed part number of
            specified type within hookup as a string per pol
                if include_revs part number is e.g. FDV1:A
                if include_ports they are included as e.g. 'input>FDV:A<terminals'
        """
        parts = {}
        extra_cols = ['start', 'stop']
        for pol, names in six.iteritems(self.columns):
            if part_type not in names:
                parts[pol] = None
                continue
            iend = 1
            for ec in extra_cols:
                if ec in self.columns[pol]:
                    iend += 1
            part_ind = names.index(part_type)
            is_first_one = (part_ind == 0)
            is_last_one = (part_ind == len(names) - iend)
            # Get part number
            if is_last_one:
                part_number = self.hookup[pol][part_ind - 1].downstream_part
            else:
                part_number = self.hookup[pol][part_ind].upstream_part
            # Get rev
            rev = ''
            if include_revs:
                if is_last_one:
                    rev = ':' + self.hookup[pol][part_ind - 1].down_part_rev
                else:
                    rev = ':' + self.hookup[pol][part_ind].up_part_rev
            # Get ports
            in_port = ''
            out_port = ''
            if include_ports:
                if is_first_one:
                    out_port = '<' + self.hookup[pol][part_ind].upstream_output_port
                elif is_last_one:
                    in_port = self.hookup[pol][part_ind - 1].downstream_input_port + '>'
                else:
                    out_port = '<' + self.hookup[pol][part_ind].upstream_output_port
                    in_port = self.hookup[pol][part_ind - 1].downstream_input_port + '>'
            # Finish
            parts[pol] = "{}{}{}{}".format(in_port, part_number, rev, out_port)
        return parts

    def table_entry_row(self, pol, columns, part_types, show):
        """
        Produces the hookup table row for given parameters.

        Parameters
        ----------
        pol : str
            Polarization type, 'e' or 'n' for HERA (specified in 'cm_sysdef')
        columns : list
            Desired column headers to display
        part_types : dict
            Dictionary containing part_types
        show : dict
            Dictionary containing flags of what components to show.

        Returns
        -------
        list
            List containing the table entry.
        """
        timing = self.timing[pol]
        td = ['-'] * len(columns)
        # Get the first N-1 parts
        dip = ''
        for d in self.hookup[pol]:
            part_type = part_types[d.upstream_part]
            if part_type in columns:
                new_row_entry = self._build_new_row_entry(
                    dip, d.upstream_part, d.up_part_rev, d.upstream_output_port, show)
                td[columns.index(part_type)] = new_row_entry
            dip = d.downstream_input_port + '> '
        # Get the last part in the hookup
        part_type = part_types[d.downstream_part]
        if part_type in columns:
            new_row_entry = self._build_new_row_entry(
                dip, d.downstream_part, d.down_part_rev, None, show)
            td[columns.index(part_type)] = new_row_entry
        # Add timing
        if 'start' in columns:
            td[columns.index('start')] = timing[0]
        if 'stop' in columns:
            td[columns.index('stop')] = timing[1]
        return td

    def _build_new_row_entry(self, dip, part, rev, port, show):
        """
        Formats the hookup row entry.

        Parameters
        ----------
        dip : str
            Current entry display for the downstream_input_port
        part : str
            Current part name
        rev : str
            Current part revision
        port : str
            Current port name
        show : dict
            Dictionary containing flags of what components to show.

        Returns
        -------
        str
            String containing that row entry.
        """
        new_row_entry = ''
        if show['ports']:
            new_row_entry = dip
        new_row_entry += part
        if show['revs']:
            new_row_entry += ':' + rev
        if port is not None and show['ports']:
            new_row_entry += ' <' + port
        return new_row_entry
