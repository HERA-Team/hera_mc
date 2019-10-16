#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This is meant to hold helpful modules for parts and connections scripts contained
within the Handling class.

"""
from __future__ import absolute_import, division, print_function

from tabulate import tabulate
import sys
import copy
import six
from astropy.time import Time
from sqlalchemy import func, desc

from . import mc, cm_utils, cm_dossier, cm_active
from . import cm_partconnect as partconn


class Handling:
    """
    Class to allow various manipulations of parts, connections and their properties etc.

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

    def close(self):  # pragma: no cover
        self.session.close()

    def add_cm_version(self, time, git_hash):
        """
        Add a new cm_version row to the M&C database.

        Parameters
        ----------
        time : astropy time object
            Time of this cm_update
        git_hash : str
            Git hash of the hera_cm_db_updates repo
        """
        from .cm_transfer import CMVersion
        self.session.add(CMVersion.create(time, git_hash))

    def get_cm_version(self, at_date='now'):
        """
        Get the cm_version git_hash active at a particular time (default: now)

        Parameters
        ----------
        at_date : str, int
            time to get active cm_version for (passed to cm_utils.get_astropytime).
            Anything intelligible to cm_utils.get_astropytime.

        Returns
        -------
        str
            Git hash of the cm_version active at 'at_date'
        """
        from .cm_transfer import CMVersion

        # make sure at_date is an astropy time object
        at_date = cm_utils.get_astropytime(at_date)

        # get last row before at_date
        result = self.session.query(CMVersion).filter(CMVersion.update_time < at_date.gps).order_by(
            desc(CMVersion.update_time)).limit(1).all()
        return result[0].git_hash

    def get_part_type_for(self, hpn):
        """
        Provides the signal path part type for a supplied part number.

        Parameters
        ----------
        hpn : str
            HERA part number.

        Returns
        -------
        str
            The associated part type.
        """
        part_query = self.session.query(partconn.Parts).filter(
            (func.upper(partconn.Parts.hpn) == hpn.upper())).first()
        return part_query.hptype

    def get_part_from_hpnrev(self, hpn, rev):
        """
        Returns a Part object for the supplied part number and revisions.

        Parameters
        ----------
        hpn : str
            HERA part number
        rev : str
            Part revision designator

        Returns
        -------
        Part object
        """
        return self.session.query(partconn.Parts).filter(
            (func.upper(partconn.Parts.hpn) == hpn.upper())
            & (func.upper(partconn.Parts.hpn_rev) == rev.upper())).first()

    def get_hpn_list(self, hpn, rev, active, exact_match):
        match_list = cm_utils.match_list(hpn, rev, upper=True)
        if not exact_match:
            all_hpn = []
            all_rev = []
            for h_hpn, h_rev in match_list:
                for key in active.parts.keys():
                    if key.upper().startswith(h_hpn):
                        k_hpn, k_rev = cm_utils.split_part_key(key)
                        all_hpn.append(k_hpn.upper())
                        all_rev.append(h_rev)
            match_list = cm_utils.match_list(all_hpn, all_rev, upper=True)
        return match_list

    def get_part_dossier(self, hpn, rev=None, at_date='now', notes_start_date='<', exact_match=True):
        """
        Return information on a part or parts.

        Parameters
        -----------
        hpn : str, list
            Hera part number [string or list-of-strings] (whole or first part thereof)
        rev : str, list, None
            Specific revision(s) or None (which yields all). If list, must match length of hpn
        at_date : str, int, datetime, Time
            Reference date of dossier (and stop_date for displaying notes)
        notes_start_date : str, int, datetime, Time
            Start_date for displaying notes
        exact_match : bool
            Flag to enforce full part number match, or "startswith"

        Returns
        -------
        dict
            dictionary keyed on the part_number containing PartEntry dossier classes
        """

        active = cm_active.ActiveData(self.session, at_date=at_date)
        active.load_parts()
        active.load_connections()
        active.load_info()
        active.load_geo()
        part_dossier = {}

        hpn_list = self.get_hpn_list(hpn, rev, active, exact_match)

        for h_hpn, h_rev in hpn_list:
            if h_rev is None:
                h_rev = active.revs(h_hpn)
            elif isinstance(h_rev, six.string_types):
                h_rev = [x.strip().upper() for x in h_rev.split(',')]
            for rev in h_rev:
                key = cm_utils.make_part_key(h_hpn, rev)
                if key in active.parts.keys():
                    this_part = cm_dossier.PartEntry(hpn=h_hpn, rev=rev, at_date=at_date, notes_start_date=notes_start_date)
                    this_part.get_entry(active)
                    part_dossier[key] = this_part
        return part_dossier

    def show_parts(self, part_dossier, notes_only=False):
        """
        Print out part information.  Uses tabulate package.

        Parameter
        ---------
        part_dossier : dict
            Input dictionary of parts, generated by self.get_part_dossier
        notes_only : bool
            Flag to print out only the notes of a part as opposed to the standard table.
            This also includes the note post date and library file (if in database)
        """

        pd_keys = sorted(list(part_dossier.keys()))
        if len(pd_keys) == 0:
            print('Part not found')
            return
        table_data = []
        if notes_only:
            if len(pd_keys) == 1 and pd_keys[0] == cm_utils.system_wide_key:
                columns = ['part_info', 'post_date', 'lib_file']
            else:
                columns = ['hpn', 'hpn_rev', 'part_info', 'post_date', 'lib_file']
        else:
            columns = ['hpn', 'hpn_rev', 'hptype', 'manufacturer_number', 'start_date', 'stop_date',
                       'input_ports', 'output_ports', 'part_info', 'geo']
        headers = part_dossier[pd_keys[0]].get_header_titles(columns)
        for hpnr in pd_keys:
            new_rows = part_dossier[hpnr].table_entry_row(columns)
            for nr in new_rows:
                table_data.append(nr)
        print('\n' + tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n')

    def get_physical_connections(self, at_date=None):
        """
        Finds and returns a list of "physical" connections, as opposed to "hookup" connections.
            In this context "hookup" refers to all signal path connections that uniquely determine
            the path from station to correlator input.
            "Physical" refers to other connections that we wish to track, such as power or rack location.
            The leading character of physical ports is '@'.
        If at_date is of type Time, it will only return connections valid at that time.  Otherwise
        it ignores at_date (i.e. it will return any such connection over all time.)

        Returns a list of connections (class)

        Parameters
        ----------
        at_date : Astropy Time
            Time to check epoch.  If None is ignored.

        Returns
        -------
        list
            List of Connections
        """
        if not isinstance(at_date, Time):
            at_date = cm_utils.get_astropytime(at_date)
        part_connection_dossier = {}
        for conn in self.session.query(partconn.Connections).filter(
                (partconn.Connections.upstream_output_port.ilike('@%'))
                | (partconn.Connections.downstream_input_port.ilike('@%'))):
            conn.gps2Time()
            include_this_one = True
            if isinstance(at_date, Time) and not cm_utils.is_active(at_date, conn.start_date, conn.stop_date):
                include_this_one = False
            if include_this_one:
                this_connect = cm_dossier.PartConnectionEntry(conn.upstream_part, conn.up_part_rev, conn.upstream_output_port)
                this_connect.make_entry_from_connection(conn)
                part_connection_dossier[this_connect.entry_key] = this_connect
        return part_connection_dossier

    def get_specific_connection(self, cobj, at_date=None):
        """
        Finds and returns a list of connections matching the supplied components of the query.
        At the very least upstream_part and downstream_part must be included -- revisions and
        ports are ignored unless they are of type string.
        If at_date is of type Time, it will only return connections valid at that time.  Otherwise
        it ignores at_date (i.e. it will return any such connection over all time.)

        Returns a list of connections (class)

        Parameters
        ----------
        cobj : object
            Connection class containing the query
        at_date : Astropy Time
            Time to check epoch.  If None is ignored.

        Returns
        -------
        list
            List of Connections
        """
        fnd = []
        for conn in self.session.query(partconn.Connections).filter(
                (func.upper(partconn.Connections.upstream_part) == cobj.upstream_part.upper())
                & (func.upper(partconn.Connections.downstream_part) == cobj.downstream_part.upper())):
            conn.gps2Time()
            include_this_one = True
            if isinstance(cobj.up_part_rev, str) and \
                    cobj.up_part_rev.lower() != conn.up_part_rev.lower():
                include_this_one = False
            if isinstance(cobj.down_part_rev, str) and \
                    cobj.down_part_rev.lower() != conn.down_part_rev.lower():
                include_this_one = False
            if isinstance(cobj.upstream_output_port, str) and \
                    cobj.upstream_output_port.lower() != conn.upstream_output_port.lower():
                include_this_one = False
            if isinstance(cobj.downstream_input_port, str) and \
                    cobj.downstream_input_port.lower() != conn.downstream_input_port.lower():
                include_this_one = False
            if isinstance(at_date, Time) and \
                    not cm_utils.is_active(at_date, conn.start_date, conn.stop_date):
                include_this_one = False
            if include_this_one:
                fnd.append(copy.copy(conn))
        return fnd

    def get_part_types(self, port, at_date):
        """
        Goes through database and pulls out part types and some other info to
        display in a table.

        Returns part_type_dict, a dictionary keyed on part type

        Parameters
        -----------
        port : str
            If port == '[phy]sical' show only "physical" ports"
            If port == '[sig]nal' show only "signal" ports
            If port == 'all' shows all
        at_date : str, int
            Date for part_types to be shown

        Returns
        -------
        dict
            part_type_dict, a dictionary keyed on part type
        """

        self.part_type_dict = {}
        for part in self.session.query(partconn.Parts).all():
            key = cm_utils.make_part_key(part.hpn, part.hpn_rev)
            if part.hptype not in self.part_type_dict.keys():
                self.part_type_dict[part.hptype] = {'part_list': [key],
                                                    'connections': 0,
                                                    'input_ports': set(),
                                                    'output_ports': set(),
                                                    'revisions': set()}
            else:
                self.part_type_dict[part.hptype]['part_list'].append(key)
        port = port.lower()[:3]
        chk_conn = cm_dossier.PartConnectionEntry('type', 'type', 'type')
        for k, v in six.iteritems(self.part_type_dict):
            for pa in v['part_list']:
                hpn, rev = cm_utils.split_part_key(pa)
                chk_conn.__init__(hpn, rev, 'all')
                chk_conn.get_entry(self.session)
                for iop in ['input_ports', 'output_ports']:
                    for p in getattr(chk_conn, iop):
                        if p is not None:
                            v['connections'] += 1
                            show_it = (port == 'all') or\
                                      (port == 'sig' and p[0] != '@') or\
                                      (port == 'phy' and p[0] == '@')
                            if show_it:
                                v[iop].add(p)
                v['revisions'].add(rev)

        return self.part_type_dict

    def show_part_types(self):
        """
        Displays the part_types dictionary
        """

        headers = ['Part type', '# dbase', '# connect', 'Input ports', 'Output ports',
                   'Revisions']
        table_data = []
        for k in sorted(self.part_type_dict.keys()):
            td = [k, len(self.part_type_dict[k]['part_list']),
                  self.part_type_dict[k]['connections']]
            td.append(', '.join(sorted(self.part_type_dict[k]['input_ports'])))
            td.append(', '.join(sorted(self.part_type_dict[k]['output_ports'])))
            td.append(', '.join(sorted(self.part_type_dict[k]['revisions'])))
            table_data.append(td)
        print()
        print(tabulate(table_data, headers=headers, tablefmt='orgtbl'))
        print()
