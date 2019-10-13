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

from . import mc, cm_utils, cm_dossier
from . import cm_partconnect as partconn
from . import cm_revisions as cmrev


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

    def get_rev_part_dictionary(self, hpn, rev, at_date, exact_match):
        """
        This gets the list of hpn that match the rev -- the resulting dictionary
        is used to get the part and connection "dossiers"

        Parameters
        ----------
        hpn : list, str
            The input hera part number [string or list-of-strings] (whole or first part thereof)
        rev : list, str
            Specific revision(s) or category(ies) ('LAST', 'ACTIVE', 'ALL', 'FULL')
            if list must match length of hpn
        at_date : str, int
            Reference date of dossier [something get_astropytime can handle]
        exact_match :  bool
            If True, will enforce full part number match

        Returns
        -------
        dict
            Dictionary containing the revision part information.
        """

        at_date = cm_utils.get_astropytime(at_date)
        hpn = cm_utils.listify(hpn)
        if isinstance(rev, six.string_types):
            rev = len(hpn) * [rev]
        rev_part = {}
        for i, xhpn in enumerate(hpn):
            if not exact_match and xhpn[-1] != '%':
                xhpn = xhpn + '%'
            for part in self.session.query(partconn.Parts).filter(partconn.Parts.hpn.ilike(xhpn)):
                rev_part[part.hpn] = cmrev.get_revisions_of_type(part.hpn, rev[i],
                                                                 at_date=at_date,
                                                                 session=self.session)
        return rev_part

    def get_part_dossier(self, hpn, rev, at_date, notes_start_date='<', sort_notes_by='part',
                         exact_match=False, full_version=True):
        """
        Return information on a part.  It will return all matching first
        characters unless exact_match==True.  It gets parts as specified under 'rev'.

        Returns part_dossier: a dictionary keyed on the part_number containing PartEntry dossier classes

        Parameters
        -----------
        hpn : str, list
            The input hera part number [string or list-of-strings] (whole or first part thereof)
        rev : str, list
            Specific revision(s) or category(ies) ('LAST', 'ACTIVE', 'ALL', 'FULL', specific). If list, must match length of hpn
        at_date : str, int
            Reference date of dossier (and stop_date for displaying notes)
        notes_start_date : str, int
            Start_date for displaying notes
        sort_notes_by : str
            For all notes (hpn=None) can sort by 'part' or 'post' ['part']
        exact_match : bool
            Flag to enforce full part number match
        full_version : bool
            Flag whether to populate the full_version or truncated version of the dossier

        Returns
        -------
        dict
            dictionary keyed on the part_number containing PartEntry dossier classes
        """

        part_dossier = {}
        if hpn is None:
            allinfo = cm_dossier.PartEntry(hpn=None, rev=None, at_date=at_date, notes_start_date=notes_start_date,
                                           sort_notes_by=sort_notes_by)
            allinfo.get_part_info(session=self.session)
            part_dossier[allinfo.entry_key] = allinfo
        else:
            rev_part = self.get_rev_part_dictionary(hpn=hpn, rev=rev, at_date=at_date, exact_match=exact_match)
            # Now get unique part/revs and put into dictionary
            for xhpn in rev_part:
                if len(rev_part[xhpn]) == 0:
                    continue
                for xrev in rev_part[xhpn]:
                    this_rev = xrev.rev
                    this_part = cm_dossier.PartEntry(hpn=xhpn, rev=this_rev, at_date=at_date, notes_start_date=notes_start_date)
                    this_part.get_entry(session=self.session, full_version=full_version)
                    this_part.part_type = self.get_part_type_for(xhpn)
                    part_dossier[this_part.entry_key] = this_part
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

    def get_part_connection_dossier(self, hpn, rev, port, at_date=None, exact_match=False):
        """
        Return information on parts connected to hpn.  It should get connections immediately
        adjacent to one part (upstream and downstream).

        Returns connection dictionary with PartConnectionEntry dossier classes

        Parameters
        ----------
        hpn : str, list
            The input hera part number [string or list-of-strings] (whole or first part thereof)
        rev : str, list
            Specific revision(s) or category(ies) ('LAST', 'ACTIVE', 'ALL', 'FULL', specific).
            If list, must match length of hpn
        port : str
            A specifiable port name [string, not a list],  default is 'all'
        at_date : str, int
            Feference date of dossier, only used if rev==ACTIVE (and for now FULL...)
        exact_match : bool
            Flag to enforce full part number match

        Returns
        -------
        dict
            dict connection dictionary with PartConnectionEntry classes
        """

        at_date = cm_utils.get_astropytime(at_date)
        rev_part = self.get_rev_part_dictionary(hpn, rev, at_date, exact_match)
        part_connection_dossier = {}
        for i, xhpn in enumerate(rev_part):
            if len(rev_part[xhpn]) == 0:
                continue
            for xrev in rev_part[xhpn]:
                this_rev = xrev.rev
                this_connect = cm_dossier.PartConnectionEntry(xhpn, this_rev, port, at_date)
                this_connect.get_entry(self.session)
                part_connection_dossier[this_connect.entry_key] = this_connect
        return part_connection_dossier

    def show_connections(self, connection_dossier, headers=None, verbosity=3):
        """
        Print out active connection information.  Uses tabulate package.

        Parameter
        ---------
        connection_dossier : dict
            Input dictionary of connections, generated by self.get_connection
        verbosity : int
            Integer 1, 2, 3 for low, medium, high
        """
        table_data = []
        if headers is None:
            if verbosity == 1:
                headers = ['Upstream', 'Part', 'Downstream']
            elif verbosity == 2:
                headers = ['Upstream', '<uOutput:', ':uInput>', 'Part', '<dOutput:',
                           ':dInput>', 'Downstream']
            elif verbosity > 2:
                headers = ['uStart', 'uStop', 'Upstream', '<uOutput:', ':uInput>',
                           'Part', '<dOutput:', ':dInput>', 'Downstream', 'dStart', 'dStop']
        for k in sorted(connection_dossier.keys()):
            conn = connection_dossier[k]
            if len(conn.up) == 0 and len(conn.down) == 0:
                continue
            r = conn.table_entry_row(headers)
            for tdata in r:
                table_data.append(tdata)

        print(tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n')

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
