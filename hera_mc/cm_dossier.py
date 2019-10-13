#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This contains the Entry classes which serves as a "dossier" for part entries,
connections entries, and hookup entries.
"""
from __future__ import absolute_import, division, print_function

import six
import copy

from . import cm_sysdef, cm_utils
from . import cm_partconnect as partconn
from sqlalchemy import func


class PartEntry():
    """
    This class holds all of the information on a given part:rev, including connections
    (contained in the included PartConnectionEntry(s)), part_info, and, if applicable,
    geo_location.

    It contains the modules to format the dossier for use in the parts display matrix.

    Parameters
    ----------
    hpn : str
        HERA part number - for a single part, not list.  Note: only looks for exact matches.
    rev : str
        HERA revision - this is for a specific revision, not a class of revisions.
    at_date : astropy.Time
        Date after which the part is active.  If inactive, the part will still be included,
        but things like notes, geo etc may exclude on that basis.
    notes_start_date : astropy.Time
        Start date on which to filter notes.  The stop date is at_date above.
    sort_notes_by : str {'part', 'time'}
        Sort notes display by 'part' or 'time'
    """

    col_hdr = {'hpn': 'HERA P/N', 'hpn_rev': 'Rev', 'hptype': 'Part Type',
               'manufacturer_number': 'Mfg #', 'start_date': 'Start', 'stop_date': 'Stop',
               'input_ports': 'Input', 'output_ports': 'Output',
               'part_info': 'Note', 'geo': 'Geo', 'post_date': 'Date', 'lib_file': 'File'}

    def __init__(self, hpn, rev, at_date, notes_start_date, sort_notes_by='part'):
        if isinstance(hpn, six.string_types):
            hpn = hpn.upper()
        self.hpn = hpn
        if isinstance(rev, six.string_types):
            rev = rev.upper()
        self.rev = rev
        self.entry_key = cm_utils.make_part_key(self.hpn, self.rev)
        self.at_date = at_date
        self.part_type = None
        self.notes_start_date = notes_start_date
        self.sort_notes_by = sort_notes_by
        self.part = None  # This is the cm_partconnect.Parts class
        self.part_info = []  # This is a list of cm_partconnect.PartInfo class entries
        self.connections = None  # This is the PartConnectionEntry class
        self.geo = None  # This is the geo_location.GeoLocation class

    def __repr__(self):
        return("{}:{} -- {} -- <{}>".format(self.hpn, self.rev, self.part, self.connections))

    def get_entry(self, session, full_version=True):
        """
        This retrieves one part_dossier entry.

        Parameters
        ----------
        session : object
            A database session instance
        full_version : bool
            Flag to retrieve a full version.  If False, a truncated version leaving off
            part_info, geo and connections information is returned.
        """
        part_query = session.query(partconn.Parts).filter(
            (func.upper(partconn.Parts.hpn) == self.hpn) & (func.upper(partconn.Parts.hpn_rev) == self.rev))
        self.part = copy.copy(part_query.first())  # There should be only one.
        self.part.gps2Time()
        if full_version:
            self.get_part_info(session=session)
            self.get_geo(session=session)
            self.connections = PartConnectionEntry(self.hpn, self.rev, 'all')
            self.connections.get_entry(session)

    def get_part_info(self, session):
        """
        Retrieves the part_info for the part in self.hpn.

        Parameter
        ---------
        session : object
            A database session instance
        """
        pi_dict = {}
        if self.hpn is None:
            for part_info in session.query(partconn.PartInfo).all():
                if self.sort_notes_by == 'part':
                    pdkey = '{}{}{}'.format(part_info.hpn, part_info.hpn_rev, part_info.posting_gpstime)
                else:
                    pdkey = '{}{}{}'.format(part_info.posting_gpstime, part_info.hpn, part_info.hpn_rev)
                pi_dict[pdkey] = part_info
        else:
            for part_info in session.query(partconn.PartInfo).filter(
                    (func.upper(partconn.PartInfo.hpn) == self.hpn) & (func.upper(partconn.PartInfo.hpn_rev) == self.rev)):
                pi_dict[part_info.posting_gpstime] = part_info
        for x in sorted(pi_dict.keys(), reverse=True):
            if cm_utils.is_active(pi_dict[x].posting_gpstime, self.notes_start_date, self.at_date):
                self.part_info.append(pi_dict[x])

    def get_geo(self, session):
        """
        Retrieves the geographical information for the part in self.hpn

        Parameter
        ---------
        session : object
            A database session instance
        """
        if self.part.hptype == 'station':
            from . import geo_handling
            gh = geo_handling.get_location([self.part.hpn], self.at_date, session=session)
            if len(gh) == 1:
                self.geo = gh[0]

    def get_header_titles(self, headers):
        """
        Generates the header titles for the given header names.  The returned header_titles are
        used in the tabulate display.

        Parameters
        ----------
        headers : list
            List of header names.

        Returns
        -------
        list
            The list of the associated header titles.
        """
        header_titles = []
        for h in headers:
            header_titles.append(self.col_hdr[h])
        return header_titles

    def table_entry_row(self, columns):
        """
        Converts the part_dossier column information to a row for the tabulate display.

        Parameters
        ----------
        columns : list
            List of the desired header columns to use.

        Returns
        -------
        list
            A row for the tabulate display.
        """
        tdata = []
        if 'lib_file' in columns:  # notes only version
            for i, pi in enumerate(self.part_info):
                if not i:
                    x = [self.hpn, self.rev]
                else:
                    x = ['', '']
                if self.hpn is None:
                    x = []
                    hr = '{}:{}'.format(pi.hpn, pi.hpn_rev)
                    pi.comment = "{:10s} > {}".format(hr, pi.comment)
                tdata.append(x + [pi.comment, cm_utils.get_time_for_display(pi.posting_gpstime),
                             pi.library_file])
        else:
            for c in columns:
                try:
                    x = getattr(self, c)
                except AttributeError:
                    try:
                        x = getattr(self.part, c)
                    except AttributeError:
                        x = getattr(self.connections, c)
                if c == 'part_info' and len(x):
                    x = '\n'.join(pi.comment for pi in x)
                elif c == 'geo' and x:
                    x = "{:.1f}E, {:.1f}N, {:.1f}m".format(x.easting, x.northing, x.elevation)
                elif c in ['start_date', 'stop_date']:
                    x = cm_utils.get_time_for_display(x)
                elif isinstance(x, (list, set)):
                    x = ', '.join(x)
                tdata.append(x)
            tdata = [tdata]
        return tdata


class PartConnectionEntry:
    """
    This class holds connections to a specific part.  It only includes immediately
    upstream and downstream of that part (use 'hookup' for cascaded parts.)  This
    class gets incorporated into the PartDossier, but can also be used separately.
    It does not filter by time -- the receiving module can do that if desired.
    This class does include a module to filter on time that can be called with an at_date.

    It contains the modules to format the dossier for use in the connection display matrix.

    It is only/primarily used within confines of cm (called by 'get_part_connection_dossier'
    in the Handling class below).

    Parameters:
    ------------
    hpn : str
        hera part number - for a single part, not list.  Note only looks for exact matches.
    rev : str
        hera revision - this is for a specific revision, not a class of revisions.
    port : str
        connection port - this is either for a specific port name or may use 'all' (default)
    """
    def __init__(self, hpn, rev, port='all', at_date=None):
        self.hpn = hpn.upper()
        self.rev = rev.upper()
        self.port = port.lower()
        self.entry_key = cm_utils.make_part_key(hpn, rev)
        self.at_date = at_date
        self.up = {}
        self.down = {}
        self.keys_up = []  # These are ordered/paired keys
        self.keys_down = []  # "
        self.input_ports = set()
        self.output_ports = set()

    def __repr__(self):
        return ("{self.hpn}:{self.rev}\n\tkeys_up:  {self.keys_up}\n\tkeys_down:  {self.keys_down}\n".format(self=self))

    def make_entry_from_connection(self, conn):
        """
        Given a connection object it will populate a connection dossier class.

        Parameters
        ----------
        conn : object
            An object of type Connections.
        """
        self.keys_up = [self.entry_key]
        self.keys_down = [self.entry_key]
        self.up[self.entry_key] = copy.copy(conn)
        self.down[self.entry_key] = copy.copy(conn)
        self.input_ports.add(conn.downstream_input_port)
        self.output_ports.add(conn.upstream_output_port)

    def get_entry(self, session):
        """
        Gets a PartConnectionEntry class object

        Parameters
        ----------
        session : object
            A database session instance
        """
        # Find where the part is in the upward position, so identify its downward connection
        tmp = {}
        for i, conn in enumerate(session.query(partconn.Connections).filter(
                (func.upper(partconn.Connections.upstream_part) == self.hpn)
                & (func.upper(partconn.Connections.up_part_rev) == self.rev))):
            if self.port == 'all' or conn.upstream_output_port.lower() == self.port:
                conn.gps2Time()
                if cm_utils.is_active(self.at_date, conn.start_gpstime, conn.stop_gpstime):
                    ckey = cm_utils.make_connection_key(conn.downstream_part,
                                                        conn.down_part_rev,
                                                        conn.downstream_input_port,
                                                        conn.start_gpstime)
                    self.down[ckey] = copy.copy(conn)
                    tmp[conn.upstream_output_port + '{:03d}'.format(i)] = ckey
        self.keys_down = [tmp[x] for x in sorted(tmp.keys())]

        # Find where the part is in the downward position, so identify its upward connection
        tmp = {}
        for i, conn in enumerate(session.query(partconn.Connections).filter(
                (func.upper(partconn.Connections.downstream_part) == self.hpn)
                & (func.upper(partconn.Connections.down_part_rev) == self.rev))):
            if self.port == 'all' or conn.downstream_input_port.lower() == self.port:
                conn.gps2Time()
                if cm_utils.is_active(self.at_date, conn.start_gpstime, conn.stop_gpstime):
                    ckey = cm_utils.make_connection_key(conn.upstream_part,
                                                        conn.up_part_rev,
                                                        conn.upstream_output_port,
                                                        conn.start_gpstime)
                    self.up[ckey] = copy.copy(conn)
                    tmp[conn.downstream_input_port + '{:03d}'.format(i)] = ckey
        self.keys_up = [tmp[x] for x in sorted(tmp.keys())]

        # Pull out ports and make equi-pair upstream/downstream ports for this part -
        # note that the signal port names have a convention that allows this somewhat
        # brittle scheme to work for signal path parts
        for c in self.up.values():
            self.input_ports.add(c.downstream_input_port)
        for c in self.down.values():
            self.output_ports.add(c.upstream_output_port)
        pad = len(self.keys_down) - len(self.keys_up)
        if pad < 0:
            self.keys_down.extend([None] * abs(pad))
        elif pad > 0:
            self.keys_up.extend([None] * abs(pad))

    def table_entry_row(self, columns):
        """
        Converts the connections_dossier column information to a row for the tabulate display.

        Parameters
        ----------
        columns : list
            List of the desired header columns to use.

        Returns
        -------
        list
            A row for the tabulate display.
        """
        tdata = []
        show_conn_dict = {'Part': self.entry_key}

        for u, d in zip(self.keys_up, self.keys_down):
            if u is None:
                use_upward_connection = False
                for h in ['Upstream', 'uStart', 'uStop', '<uOutput:', ':uInput>']:
                    show_conn_dict[h] = ' '
            else:
                use_upward_connection = True
                c = self.up[u]
                show_conn_dict['Upstream'] = cm_utils.make_part_key(c.upstream_part, c.up_part_rev)
                show_conn_dict['uStart'] = cm_utils.get_time_for_display(c.start_date)
                show_conn_dict['uStop'] = cm_utils.get_time_for_display(c.stop_date)
                show_conn_dict['<uOutput:'] = c.upstream_output_port
                show_conn_dict[':uInput>'] = c.downstream_input_port
            if d is None:
                use_downward_connection = False
                for h in ['Downstream', 'dStart', 'dStop', '<dOutput:', ':dInput>']:
                    show_conn_dict[h] = ' '
            else:
                use_downward_connection = True
                c = self.down[d]
                show_conn_dict['Downstream'] = cm_utils.make_part_key(c.downstream_part, c.down_part_rev)
                show_conn_dict['dStart'] = cm_utils.get_time_for_display(c.start_date)
                show_conn_dict['dStop'] = cm_utils.get_time_for_display(c.stop_date)
                show_conn_dict['<dOutput:'] = c.upstream_output_port
                show_conn_dict[':dInput>'] = c.downstream_input_port
            if use_upward_connection or use_downward_connection:
                r = []
                for h in columns:
                    r.append(show_conn_dict[h])
                tdata.append(r)

        return tdata


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
            for port, conn_list in six.iteritems(input_dict['hookup']):
                new_conn_list = []
                for conn_dict in conn_list:
                    new_conn_list.append(partconn.get_connection_from_dict(conn_dict))
                hookup_connections_dict[port] = new_conn_list
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
        for port, conn_list in six.iteritems(self.hookup):
            new_conn_list = []
            for conn in conn_list:
                new_conn_list.append(conn._to_dict())
            hookup_connections_dict[port] = new_conn_list
        return {'entry_key': self.entry_key, 'hookup': hookup_connections_dict,
                'fully_connected': self.fully_connected,
                'hookup_type': self.hookup_type, 'columns': self.columns,
                'timing': self.timing, 'sysdef': self.sysdef._to_dict()}

    def get_hookup_type_and_column_headers(self, port, part_types_found):
        """
        The columns in the hookup contain parts in the hookup chain and the column headers are
        the part types contained in that column.  This returns the headers for the retrieved hookup.

        It just checks which hookup_type the parts are in and keeps however many
        parts are used.

        Parameters
        ----------
        port : str
            Part port to get, of the form 'POL<port', e.g. 'E<ground'
        part_types_found : list
            List of the part types that were found
        """
        self.hookup_type[port] = None
        self.columns[port] = []
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
            self.hookup_type[port] = is_this_one
            for c in self.sysdef.full_connection_path[is_this_one]:
                if c in part_types_found:
                    self.columns[port].append(c)

    def add_timing_and_fully_connected(self, port):
        """
        Method to add the timing and fully_connected flag for the hookup.

        Parameters
        ----------
        port : str
            Part port to get, of the form 'POL<port', e.g. 'E<ground'
        """
        if self.hookup_type[port] is not None:
            full_hookup_length = len(self.sysdef.full_connection_path[self.hookup_type[port]]) - 1
        else:
            full_hookup_length = -1
        latest_start = 0
        earliest_stop = None
        for c in self.hookup[port]:
            if c.start_gpstime > latest_start:
                latest_start = c.start_gpstime
            if c.stop_gpstime is None:
                pass
            elif earliest_stop is None:
                earliest_stop = c.stop_gpstime
            elif c.stop_gpstime < earliest_stop:
                earliest_stop = c.stop_gpstime
        self.timing[port] = [latest_start, earliest_stop]
        self.fully_connected[port] = len(self.hookup[port]) == full_hookup_length
        self.columns[port].append('start')
        self.columns[port].append('stop')

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
        for port, names in six.iteritems(self.columns):
            if part_type not in names:
                parts[port] = None
                continue
            iend = 1
            for ec in extra_cols:
                if ec in self.columns[port]:
                    iend += 1
            part_ind = names.index(part_type)
            is_first_one = (part_ind == 0)
            is_last_one = (part_ind == len(names) - iend)
            # Get part number
            if is_last_one:
                part_number = self.hookup[port][part_ind - 1].downstream_part
            else:
                part_number = self.hookup[port][part_ind].upstream_part
            # Get rev
            rev = ''
            if include_revs:
                if is_last_one:
                    rev = ':' + self.hookup[port][part_ind - 1].down_part_rev
                else:
                    rev = ':' + self.hookup[port][part_ind].up_part_rev
            # Get ports
            in_port = ''
            out_port = ''
            if include_ports:
                if is_first_one:
                    out_port = '<' + self.hookup[port][part_ind].upstream_output_port
                elif is_last_one:
                    in_port = self.hookup[port][part_ind - 1].downstream_input_port + '>'
                else:
                    out_port = '<' + self.hookup[port][part_ind].upstream_output_port
                    in_port = self.hookup[port][part_ind - 1].downstream_input_port + '>'
            # Finish
            parts[port] = "{}{}{}{}".format(in_port, part_number, rev, out_port)
        return parts

    def table_entry_row(self, port, columns, part_types, show):
        """
        Produces the hookup table row for given parameters.

        Parameters
        ----------
        port : str
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
        timing = self.timing[port]
        td = ['-'] * len(columns)
        # Get the first N-1 parts
        dip = ''
        for d in self.hookup[port]:
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
