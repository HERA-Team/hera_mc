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
import warnings
from astropy.time import Time
from sqlalchemy import func, desc

from hera_mc import mc, correlator_levels, cm_utils
from hera_mc import part_connect as PC
from hera_mc import cm_revisions as cmrev


class PartDossierEntry():
    col_hdr = {'hpn': 'HERA P/N', 'hpn_rev': 'Rev', 'hptype': 'Part Type',
               'manufacturer_number': 'Mfg #', 'start_date': 'Start', 'stop_date': 'Stop',
               'input_ports': 'Input', 'output_ports': 'Output',
               'part_info': 'Info', 'geo': 'Geo'}

    def __init__(self, hpn, rev, at_date):
        self.hpn = hpn.upper()
        self.rev = rev.upper()
        self.entry_key = cm_utils.make_part_key(hpn, rev)
        self.time = at_date
        self.part = None  # This is the part_connect.Parts class
        self.part_info = []  # This is a list of part_connect.PartInfo class entries
        self.connections = None  # This is the PartConnectionDossierEntry class
        self.geo = None  # This is the geo_location.GeoLocation class

    def get_entry(self, session, full_version=True):
        part_query = session.query(PC.Parts).filter(
            (func.upper(PC.Parts.hpn) == self.hpn) &
            (func.upper(PC.Parts.hpn_rev) == self.rev))
        self.part = copy.copy(part_query.first())  # There should be only one.
        self.part.gps2Time()
        if full_version:
            self.get_part_info(session)
            self.get_geo(session)
            self.connections = PartConnectionDossierEntry(self.hpn, self.rev, 'all', self.time)
            self.connections.get_entry(session)

    def get_part_info(self, session):
        for part_info in session.query(PC.PartInfo).filter(
                (func.upper(PC.PartInfo.hpn) == self.hpn) &
                (func.upper(PC.PartInfo.hpn_rev) == self.rev)):
            self.part_info.append(part_info)

    def get_geo(self, session):
        if self.part.hptype == 'station':
            from hera_mc import geo_handling
            gh = geo_handling.get_location([self.part.hpn], self.time, session=session)
            if len(gh) == 1:
                self.geo = gh[0]

    def get_header_titles(self, headers):
        header_titles = []
        for h in headers:
            header_titles.append(self.col_hdr[h])
        return header_titles

    def table_entry_row(self, columns):
        tdata = []
        for c in columns:
            try:
                x = getattr(self, c)
            except AttributeError:
                try:
                    x = getattr(self.part, c)
                except AttributeError:
                    x = getattr(self.connections, c)
            if c == 'part_info' and len(x):
                x = ', '.join(pi.comment for pi in x)
            elif c == 'geo' and x:
                x = "{:.1f}E, {:.1f}N, {:.1f}m".format(x.easting, x.northing, x.elevation)
            elif c in ['start_date', 'stop_date']:
                x = cm_utils.get_time_for_display(x)
            elif isinstance(x, (list, set)):
                x = ', '.join(x)
            tdata.append(x)
        return tdata


class PartConnectionDossierEntry:
    def __init__(self, hpn, rev, port, at_date):
        self.hpn = hpn.upper()
        self.rev = rev.upper()
        self.port = port.lower()
        self.entry_key = cm_utils.make_part_key(hpn, rev)
        self.time = at_date
        self.up = {}
        self.down = {}
        self.keys_up = []  # These are ordered/paired keys
        self.keys_down = []  # "
        self.input_ports = set()
        self.output_ports = set()

    def __repr__(self):
        return ("\n\tkeys_up:  {self.keys_up}\n\tkeys_down:  {self.keys_down}\n".format(self=self))

    def get_entry(self, session):
        """
        Gets a PartConnectionDossierEntry class object
        """
        # Find where the part is in the upward position, so identify its downward connection
        tmp = {}
        for i, conn in enumerate(session.query(PC.Connections).filter(
                (func.upper(PC.Connections.upstream_part) == self.hpn) &
                (func.upper(PC.Connections.up_part_rev) == self.rev))):
            if self.port == 'all' or conn.upstream_output_port.lower() == self.port:
                conn.gps2Time()
                ckey = cm_utils.make_connection_key(conn.downstream_part,
                                                    conn.down_part_rev,
                                                    conn.downstream_input_port,
                                                    conn.start_gpstime)
                self.down[ckey] = copy.copy(conn)
                tmp[conn.upstream_output_port + '{:03d}'.format(i)] = ckey
        self.keys_down = [tmp[x] for x in sorted(tmp.keys())]

        # Find where the part is in the downward position, so identify its upward connection
        tmp = {}
        for i, conn in enumerate(session.query(PC.Connections).filter(
                (func.upper(PC.Connections.downstream_part) == self.hpn) &
                (func.upper(PC.Connections.down_part_rev) == self.rev))):
            if self.port == 'all' or conn.downstream_input_port.lower() == self.port:
                conn.gps2Time()
                ckey = cm_utils.make_connection_key(conn.upstream_part,
                                                    conn.up_part_rev,
                                                    conn.upstream_output_port,
                                                    conn.start_gpstime)
                self.up[ckey] = copy.copy(conn)
                tmp[conn.downstream_input_port + '{:03d}'.format(i)] = ckey
        self.keys_up = [tmp[x] for x in sorted(tmp.keys())]

        # Equi-pair upstream/downstream ports for this part - note that the signal port names have a
        # convention that allows this somewhat brittle scheme to work for signal path parts
        self.get_ports()
        pad = len(self.keys_down) - len(self.keys_up)
        if pad < 0:
            self.keys_down.extend([None] * abs(pad))
        elif pad > 0:
            self.keys_up.extend([None] * abs(pad))

    def get_ports(self):
        """
        Finds sets of input_ports and output_ports
        """
        for c in self.up.values():
            self.input_ports.add(c.downstream_input_port)
        for c in self.down.values():
            self.output_ports.add(c.upstream_output_port)

    def table_entry_row(self, headers):
        tdata = []
        show_conn_dict = {'Part': self.entry_key}

        for u, d in zip(self.keys_up, self.keys_down):
            if u is None:
                for h in ['Upstream', 'uStart', 'uStop', '<uOutput:', ':uInput>']:
                    show_conn_dict[h] = ' '
            else:
                c = self.up[u]
                show_conn_dict['Upstream'] = cm_utils.make_part_key(c.upstream_part, c.up_part_rev)
                show_conn_dict['uStart'] = cm_utils.get_time_for_display(c.start_date)
                show_conn_dict['uStop'] = cm_utils.get_time_for_display(c.stop_date)
                show_conn_dict['<uOutput:'] = c.upstream_output_port
                show_conn_dict[':uInput>'] = c.downstream_input_port
            if d is None:
                for h in ['Downstream', 'dStart', 'dStop', '<dOutput:', ':dInput>']:
                    show_conn_dict[h] = ' '
            else:
                c = self.down[d]
                show_conn_dict['Downstream'] = cm_utils.make_part_key(c.downstream_part, c.down_part_rev)
                show_conn_dict['dStart'] = cm_utils.get_time_for_display(c.start_date)
                show_conn_dict['dStop'] = cm_utils.get_time_for_display(c.stop_date)
                show_conn_dict['<dOutput:'] = c.upstream_output_port
                show_conn_dict[':dInput>'] = c.downstream_input_port
            r = []
            for h in headers:
                r.append(show_conn_dict[h])
            tdata.append(r)

        return tdata


class Handling:
    """
    Class to allow various manipulations of parts, connections and their properties etc.
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

    def close(self):
        self.session.close()

    def add_cm_version(self, time, git_hash):
        """
        Add a new cm_version row to the M&C database.

        Parameters:
        ------------
        time: astropy time object
            time of this cm_update
        git_hash: string
            git hash of the cm repo
        """
        from .cm_transfer import CMVersion

        self.session.add(CMVersion.create(time, git_hash))

    def get_cm_version(self, at_date='now'):
        """
        Get the cm_version git_hash active at a particular time (default: now)

        Parameters:
        ------------
        time: time to get active cm_version for (passed to cm_utils.get_astropytime).
            Default is 'now'

        Returns:
        --------
        git hash (string) of the cm_version active at
        """
        from .cm_transfer import CMVersion

        # make sure at_date is an astropy time object
        at_date = cm_utils.get_astropytime(at_date)

        # get last row before at_date
        result = self.session.query(CMVersion).filter(CMVersion.update_time < at_date.gps).order_by(
            desc(CMVersion.update_time)).limit(1).all()

        return result[0].git_hash

    def get_part_type_for(self, hpn):
        part_query = self.session.query(PC.Parts).filter(
            (func.upper(PC.Parts.hpn) == hpn.upper())).first()
        return part_query.hptype

    def get_rev_part_dictionary(self, hpn_list, rev, at_date, exact_match):
        """
        This gets the list of hpn that match the rev -- the resulting dictionary
        is used to get the part and connection "dossiers"

        Parameters
        -----------
        hpn_list:  the input hera part number [list of strings] (whole or first part thereof)
        rev:  specific revision(s) or category(ies) ('LAST', 'ACTIVE', 'ALL', 'FULL')
              if list, must match length of hpn_list
        at_date:  reference date of dossier [something get_astropytime can handle]
        exact_match:  boolean to enforce full part number match
        """
        if isinstance(hpn_list, (str, unicode)):
            hpn_list = [hpn_list]
        if isinstance(rev, (str, unicode)):
            rev_list = len(hpn_list) * [rev]
        else:
            rev_list = rev
        if len(hpn_list) != len(rev_list):
            print("Unmatched hpn and rev lists.")
            return {}
        at_date = cm_utils.get_astropytime(at_date)

        rev_part = {}
        for i, xhpn in enumerate(hpn_list):
            if not exact_match and xhpn[-1] != '%':
                xhpn = xhpn + '%'
            for part in self.session.query(PC.Parts).filter(PC.Parts.hpn.ilike(xhpn)):
                rev_part[part.hpn] = cmrev.get_revisions_of_type(part.hpn, rev_list[i],
                                                                 at_date=at_date,
                                                                 session=self.session)
        return rev_part

    def get_part_dossier(self, hpn_list, rev, at_date, exact_match=False, full_version=True):
        """
        Return information on a part.  It will return all matching first
        characters unless exact_match==True.
        It gets all parts, the receiving module should filter on e.g. date if desired.

        Returns part_dossier: a dictionary keyed on the part_number containing PartDossierEntry classes

        Parameters
        -----------
        hpn_list:  the input hera part number [list of strings] (whole or first part thereof)
        rev:  specific revision(s) or category(ies) ('LAST', 'ACTIVE', 'ALL', 'FULL')
              if list, must match length of hpn_list
        at_date:  reference date of dossier [something get_astropytime can handle]
        exact_match:  boolean to enforce full part number match
        full_version:  flag whether to populate the full_version or truncated version of the dossier
        """

        rev_part = self.get_rev_part_dictionary(hpn_list, rev, at_date, exact_match)

        part_dossier = {}
        # Now get unique part/revs and put into dictionary
        for xhpn in rev_part:
            if len(rev_part[xhpn]) == 0:
                continue
            for xrev in rev_part[xhpn]:
                this_rev = xrev.rev
                this_part = PartDossierEntry(xhpn, this_rev, at_date)
                this_part.get_entry(self.session, full_version)
                part_dossier[this_part.entry_key] = this_part
        return part_dossier

    def show_parts(self, part_dossier):
        """
        Print out part information.  Uses tabulate package.

        Parameters
        -----------
        part_dossier:  input dictionary of parts, generated by self.get_part_dossier
        """

        if len(part_dossier.keys()) == 0:
            print('Part not found')
            return
        table_data = []
        columns = ['hpn', 'hpn_rev', 'hptype', 'manufacturer_number', 'start_date', 'stop_date',
                   'input_ports', 'output_ports', 'part_info', 'geo']
        headers = part_dossier[part_dossier.keys()[0]].get_header_titles(columns)
        for hpnr in sorted(part_dossier.keys()):
            table_data.append(part_dossier[hpnr].table_entry_row(columns))
        print('\n' + tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n')

    def get_specific_connection(self, c, at_date=None):
        """
        Finds and returns a list of connections matching the supplied components of the query.
        At the very least upstream_part and downstream_part must be included -- revisions and
        ports are ignored unless they are of type string.
        If at_date is of type Time, it will only return connections valid at that time.  Otherwise
        it ignores at_date (i.e. it will return any such connection over all time.)

        Returns a list of connections (class)

        Parameters:
        ------------
        c:  connection class containing the query
        at_date:  Astropy Time to check epoch.  If None is ignored.
        """
        fnd = []
        for conn in self.session.query(PC.Connections).filter(
                (func.upper(PC.Connections.upstream_part) == c.upstream_part.upper()) &
                (func.upper(PC.Connections.downstream_part) == c.downstream_part.upper())):
            conn.gps2Time()
            include_this_one = True
            if isinstance(c.up_part_rev, str) and \
                    c.up_part_rev.lower() != conn.up_part_rev.lower():
                include_this_one = False
            if isinstance(c.down_part_rev, str) and \
                    c.down_part_rev.lower() != conn.down_part_rev.lower():
                include_this_one = False
            if isinstance(c.upstream_output_port, str) and \
                    c.upstream_output_port.lower() != conn.upstream_output_port.lower():
                include_this_one = False
            if isinstance(c.downstream_input_port, str) and \
                    c.downstream_input_port.lower() != conn.downstream_input_port.lower():
                include_this_one = False
            if isinstance(at_date, Time) and \
                    not cm_utils.is_active(at_date, conn.start_date, conn.stop_date):
                include_this_one = False
            if include_this_one:
                fnd.append(copy.copy(conn))
        return fnd

    def get_part_connection_dossier(self, hpn_list, rev, port, at_date, exact_match=False):
        """
        Return information on parts connected to hpn
        It should get connections immediately adjacent to one part (upstream and
            downstream).

        Returns connection_dossier dictionary with PartConnectionDossierEntry classes

        Parameters
        -----------
        hpn_list:  the input hera part number [list of strings] (whole or first part thereof)
        rev:  specific revision(s) or category(ies) ('LAST', 'ACTIVE', 'ALL', 'FULL')
              if list, must match length of hpn_list
        port:  a specifiable port name [string, not a list],  default is 'all'
        at_date: reference date of dossier [anything get_astropytime can handle]
        exact_match:  boolean to enforce full part number match
        """

        rev_part = self.get_rev_part_dictionary(hpn_list, rev, at_date, exact_match)

        part_connection_dossier = {}
        for xhpn in rev_part:
            if len(rev_part[xhpn]) == 0:
                continue
            for xrev in rev_part[xhpn]:
                this_rev = xrev.rev
                this_connect = PartConnectionDossierEntry(xhpn, this_rev, port, at_date)
                this_connect.get_entry(self.session)
                part_connection_dossier[this_connect.entry_key] = this_connect
        return part_connection_dossier

    def show_connections(self, connection_dossier, verbosity='h'):
        """
        Print out active connection information.  Uses tabulate package.

        Parameters
        -----------
        connection_dossier:  input dictionary of connections, generated by self.get_connection
        verbosity:  'l','m','h' verbosity level
        """
        table_data = []
        if verbosity == 'l':
            headers = ['Upstream', 'Part', 'Downstream']
        elif verbosity == 'm':
            headers = ['Upstream', '<uOutput:', ':uInput>', 'Part', '<dOutput:',
                       ':dInput>', 'Downstream']
        elif verbosity == 'h':
            headers = ['uStart', 'uStop', 'Upstream', '<uOutput:', ':uInput>',
                       'Part', '<dOutput:', ':dInput>', 'Downstream', 'dStart', 'dStop']
        for k, conn in connection_dossier.iteritems():
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
        port:  if port == '[phy]sical' show only "physical" ports"
               if port == '[sig]nal' show only "signal" ports
               if port == 'all' shows all
        at_date:  date for part_types to be shown
        """

        self.part_type_dict = {}
        for part in self.session.query(PC.Parts).all():
            key = cm_utils.make_part_key(part.hpn, part.hpn_rev)
            if part.hptype not in self.part_type_dict.keys():
                self.part_type_dict[part.hptype] = {'part_list': [key],
                                                    'input_ports': set(),
                                                    'output_ports': set(),
                                                    'revisions': set()}
            else:
                self.part_type_dict[part.hptype]['part_list'].append(key)
        port = port.lower()[:3]
        for k, v in self.part_type_dict.iteritems():
            for pa in v['part_list']:
                hpn, rev = cm_utils.split_part_key(pa)
                chk_conn = PartConnectionDossierEntry(hpn, rev, 'all', at_date)
                chk_conn.get_entry(self.session)
                for iop in ['input_ports', 'output_ports']:
                    for p in getattr(chk_conn, iop):
                        show_it = (port == 'all') or\
                                  (port == 'sig' and p[0] != '@') or\
                                  (port == 'phy' and p[0] == '@')
                        if p is not None and show_it:
                            v[iop].add(copy.copy(p))
                v['revisions'].add(rev)

        return self.part_type_dict

    def show_part_types(self):
        """
        Displays the part_types dictionary
        """

        headers = ['Part type', '# in dbase', 'Input ports', 'Output ports',
                   'Revisions']
        table_data = []
        for k in self.part_type_dict.keys():
            td = [k, len(self.part_type_dict[k]['part_list'])]
            td.append(', '.join(sorted(self.part_type_dict[k]['input_ports'])))
            td.append(', '.join(sorted(self.part_type_dict[k]['output_ports'])))
            td.append(', '.join(sorted(self.part_type_dict[k]['revisions'])))
            table_data.append(td)
        print('\n', tabulate(table_data, headers=headers, tablefmt='orgtbl'))
        print()
