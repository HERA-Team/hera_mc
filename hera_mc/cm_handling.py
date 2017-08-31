#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
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
from hera_mc import cm_revisions as cmpr


class Handling:
    """
    Class to allow various manipulations of parts and their properties etc.
    Things are manipulated/passed as dictionaries currently.
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
        time: time to get active cm_version for (passed to cm_utils._get_astropytime).
            Default is 'now'

        Returns:
        --------
        git hash (string) of the cm_version active at
        """
        from .cm_transfer import CMVersion

        # make sure at_date is an astropy time object
        at_date = cm_utils._get_astropytime(at_date)

        # get last row before at_date
        result = self.session.query(CMVersion).filter(CMVersion.update_time < at_date.gps).order_by(
            desc(CMVersion.update_time)).limit(1).all()

        return result[0].git_hash

    def is_in_connections(self, hpn, rev='ACTIVE', at_date='now'):
        """
        checks to see if a part is in the connections database (which means it
            is also in parts)

        returns True/False

        Parameters:
        ------------
        hpn:  hera part number, string for part number
        rev:  revision of part number, string for rev or rev type
        """
        at_date = cm_utils._get_astropytime(at_date)
        connection_dossier = self.get_connection_dossier([hpn], rev, port='all',
                                                         at_date=at_date, exact_match=True)
        num_connections = len(connection_dossier['connections'].keys())
        if num_connections == 0:
            found_connected = False
        else:
            found_connected = True
        return found_connected

    def get_part_type_for(self, hpn):
        part_query = self.session.query(PC.Parts).filter(
            (func.upper(PC.Parts.hpn) == hpn.upper())).first()
        return part_query.hptype

    def get_part_dossier(self, hpn_list, rev, at_date, exact_match=False, full_version=True):
        """
        Return information on a part.  It will return all matching first
        characters unless exact_match==True.
        It gets all parts, the receiving module should filter on e.g. date if desired.

        Returns part_dossier: {'Time':Time, 'part':CLASS , 'part_info':CLASS,
                               'connections':CLASS, 'geo':CLASS,
                               'input_ports':[],'output_ports':[]}

        Parameters
        -----------
        hpn_list:  the input hera part number [list of strings] (whole or first part thereof)
        rev:  specific revision or category [string, currently not a list]
        at_date:  reference date of dossier [something _get_astropytime can handle]
        exact_match:  boolean to enforce full part number match
        full_version:  flag whether to populate the full_version or truncated version
        """

        at_date = cm_utils._get_astropytime(at_date)

        part_dossier = {}
        rev_part = {}
        for xhpn in hpn_list:
            if not exact_match and xhpn[-1] != '%':
                xhpn = xhpn + '%'
            for part in self.session.query(PC.Parts).filter(PC.Parts.hpn.ilike(xhpn)):
                rev_part[part.hpn] = cmpr.get_revisions_of_type(part.hpn, rev, at_date=at_date,
                                                                session=self.session)

        # Now get unique part/revs and put into dictionary
        for xhpn in rev_part.keys():
            if rev_part[xhpn] is None:
                continue
            for xrev in rev_part[xhpn]:
                this_rev = xrev.rev
                part_query = self.session.query(PC.Parts).filter(
                    (func.upper(PC.Parts.hpn) == xhpn.upper()) &
                    (func.upper(PC.Parts.hpn_rev) == this_rev.upper()))
                part_cnt = part_query.count()
                if part_cnt == 0:
                    continue
                elif part_cnt == 1:
                    part = copy.copy(part_query.all()[0])
                    part.gps2Time()
                    pr_key = cm_utils._make_part_key(part.hpn, part.hpn_rev)
                    part_dossier[pr_key] = {'Time': at_date, 'part': part}
                    if full_version:
                        part_dossier[pr_key]['part_info'] = None
                        part_dossier[pr_key]['connections'] = None
                        part_dossier[pr_key]['geo'] = None
                        part_dossier[pr_key]['input_ports'] = []
                        part_dossier[pr_key]['output_ports'] = []
                        for part_info in self.session.query(PC.PartInfo).filter(
                                (func.upper(PC.PartInfo.hpn) == part.hpn.upper()) &
                                (func.upper(PC.PartInfo.hpn_rev) == part.hpn_rev.upper())):
                            # part_info.gps2Time()
                            part_dossier[pr_key]['part_info'] = part_info
                        connections = self.get_connection_dossier(
                            hpn_list=[part.hpn], rev=part.hpn_rev, port='all',
                            at_date=at_date, exact_match=True)
                        part_dossier[pr_key]['connections'] = connections
                        if part.hptype == 'station':
                            from hera_mc import geo_handling
                            part_dossier[pr_key]['geo'] = geo_handling.get_location(
                                [part.hpn], at_date, session=self.session)
                        part_dossier[pr_key]['input_ports'], part_dossier[pr_key]['output_ports'] = \
                            self.find_ports(part_dossier[pr_key]['connections'])
                else:
                    msg = "Should only be one part/rev for {}:{}.".format(part.hpn, part.hpn_rev)
                    warnings.warn(msg)
        return part_dossier

    def find_ports(self, connection_dossier):
        """
        Given a connection_dossier dictionary, it will return all of the ports.

        Returns lists of input_ports and output_ports

        Parameters:
        ------------
        connection_dossier:  dictionary as returned from get_connections.
        """

        input_ports = []
        output_ports = []
        for k, c in connection_dossier['connections'].iteritems():
            if c.downstream_input_port not in input_ports:
                input_ports.append(c.downstream_input_port)
            if c.upstream_output_port not in output_ports:
                output_ports.append(c.upstream_output_port)
        input_ports.sort()
        output_ports.sort()
        return input_ports, output_ports

    def show_parts(self, part_dossier, verbosity='h'):
        """
        Print out part information.  Uses tabulate package.

        Parameters
        -----------
        part_dossier:  input dictionary of parts, generated by self.get_part_dossier
        verbosity:  'l','m' or 'h'
        """

        if len(part_dossier.keys()) == 0:
            print('Part not found')
            return
        table_data = []
        if verbosity == 'm':
            headers = ['HERA P/N', 'Rev', 'Part Type', 'Mfg #', 'Start', 'Stop',
                       'Active']
        elif verbosity == 'h':
            headers = ['HERA P/N', 'Rev', 'Part Type', 'Mfg #', 'Start', 'Stop',
                       'Active', 'Input', 'Output', 'Info', 'Geo']
        for hpnr in sorted(part_dossier.keys()):
            pdpart = part_dossier[hpnr]['part']
            is_active = cm_utils._is_active(part_dossier[hpnr]['Time'],
                                            pdpart.start_date, pdpart.stop_date)
            if (is_active and len(part_dossier[hpnr]['connections']) > 0):
                is_connected = 'Yes'
            elif is_active:
                is_connected = 'N/C'
            else:
                is_connected = 'No'
            if verbosity == 'l':
                print(pdpart)
            else:
                tdata = [pdpart.hpn,
                         pdpart.hpn_rev,
                         pdpart.hptype,
                         pdpart.manufacturer_number,
                         cm_utils._get_displayTime(pdpart.start_date),
                         cm_utils._get_displayTime(pdpart.stop_date),
                         is_connected]
                if verbosity == 'h':
                    ptsin = ''
                    ptsout = ''
                    for k in part_dossier[hpnr]['input_ports']:
                        ptsin += k + ', '
                    for k in part_dossier[hpnr]['output_ports']:
                        ptsout += k + ', '
                    tdata.append(ptsin.strip().strip(','))
                    tdata.append(ptsout.strip().strip(','))
                    if (part_dossier[hpnr]['part_info'] is not None):
                        comment = part_dossier[hpnr]['part_info'].comment
                    else:
                        comment = None
                    tdata.append(comment)
                    if part_dossier[hpnr]['geo'] is not None:
                        tdata.append("{:.1f}E, {:.1f}N, {:.1f}m"
                                     .format(part_dossier[hpnr]['geo'][0].easting,
                                             part_dossier[hpnr]['geo'][0].northing,
                                             part_dossier[hpnr]['geo'][0].elevation))
                    else:
                        tdata.append(None)
                    table_data.append(tdata)
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
                    not cm_utils._is_active(at_date, conn.start_date, conn.stop_date):
                include_this_one = False
            if include_this_one:
                fnd.append(copy.copy(conn))
        return fnd

    def get_connection_dossier(self, hpn_list, rev, port, at_date, exact_match=False):
        """
        Return information on parts connected to hpn
        It should get connections immediately adjacent to one part (upstream and
            downstream).
        It does not filter on date but gets all.  The receiving (or showing module)
            should filter on date if desired.

        Returns connection_dossier dictionary

        Parameters
        -----------
        hpn_list:  the input hera part number [list of strings] (whole or first part thereof)
        rev:  revision of part [string, not a list]
        port:  a specifiable port name [string, not a list],  default is 'all'
        at_date: reference date of dossier [anything _get_astropytime can handle]
        exact_match:  boolean to enforce full part number match
        """

        at_date = cm_utils._get_astropytime(at_date)
        connection_dossier = {'ordered-pairs': [], 'Time': at_date,
                              'connected-to': (hpn_list, rev, port), 'connections': {}}

        rev_part = {}
        for xhpn in hpn_list:
            if not exact_match and xhpn[-1] != '%':
                xhpn = xhpn + '%'
            for part in self.session.query(PC.Parts).filter(PC.Parts.hpn.ilike(xhpn)):
                rev_part[part.hpn] = cmpr.get_revisions_of_type(part.hpn, rev, session=self.session)
        for xhpn in rev_part.keys():
            if rev_part[xhpn] is None:
                continue
            for xrev in rev_part[xhpn]:
                up_parts = []
                down_parts = []
                this_rev = xrev.rev
                # Find where the part is in the upward position, so identify its downward connection
                for conn in self.session.query(PC.Connections).filter(
                        (func.upper(PC.Connections.upstream_part) == xhpn.upper()) &
                        (func.upper(PC.Connections.up_part_rev) == this_rev.upper())):
                    if (port.lower() == 'all' or
                            conn.upstream_output_port.lower() == port.lower()):
                        conn.gps2Time()
                        ckey = cm_utils._make_connection_key(conn.downstream_part,
                                                             conn.down_part_rev,
                                                             conn.downstream_input_port,
                                                             conn.start_gpstime)
                        connection_dossier['connections'][ckey] = copy.copy(conn)
                        down_parts.append(ckey)
                # Find where the part is in the downward position, so identify its upward connection
                for conn in self.session.query(PC.Connections).filter(
                        (func.upper(PC.Connections.downstream_part) == xhpn.upper()) &
                        (func.upper(PC.Connections.down_part_rev) == this_rev.upper())):
                    if (port.lower() == 'all' or
                            conn.downstream_input_port.lower() == port.lower()):
                        conn.gps2Time()
                        ckey = cm_utils._make_connection_key(conn.upstream_part,
                                                             conn.up_part_rev,
                                                             conn.upstream_output_port,
                                                             conn.start_gpstime)
                        connection_dossier['connections'][ckey] = copy.copy(conn)
                        up_parts.append(ckey)
                if len(up_parts) == 0:
                    up_parts = [PC.no_connection_designator]
                if len(down_parts) == 0:
                    down_parts = [PC.no_connection_designator]
                up_parts.sort()
                down_parts.sort()
                if len(up_parts) > len(down_parts):
                    down_parts = (down_parts + len(up_parts) * [down_parts[-1]])[:len(up_parts)]
                elif len(down_parts) > len(up_parts):
                    up_parts = (up_parts + len(down_parts) * [up_parts[-1]])[:len(down_parts)]
                connection_dossier['ordered-pairs'].append([sorted(up_parts),
                                                            sorted(down_parts)])
        return connection_dossier

    def show_connections(self, connection_dossier, verbosity='h'):
        """
        Print out active connection information.  Uses tabulate package.

        Returns list of already_shown connections.

        Parameters
        -----------
        connection_dossier:  input dictionary of parts, generated by self.get_connection
        verbosity:  'l','m','h' verbosity level
        """

        table_data = []
        already_shown = []
        if verbosity == 'm':
            headers = ['Upstream', '<Output:', ':Input>', 'Part', '<Output:',
                       ':Input>', 'Downstream']
        elif verbosity == 'h':
            headers = ['uStart', 'uStop', 'Upstream', '<Output:', ':Input>',
                       'Part', '<Output:', ':Input>', 'Downstream', 'dStart', 'dStop']
        for ordered_pairs in connection_dossier['ordered-pairs']:
            for up, dn in zip(ordered_pairs[0], ordered_pairs[1]):
                if (PC.no_connection_designator in up and
                        PC.no_connection_designator in dn):
                    continue
                already_shown.append(up)
                already_shown.append(dn)
                tdata = range(0, len(headers))
                # Do upstream
                if up == PC.no_connection_designator:
                    connup = PC.get_null_connection()
                else:
                    connup = connection_dossier['connections'][up]
                uup = connup.upstream_part + ':' + connup.up_part_rev
                if PC.no_connection_designator in uup:
                    start_date = PC.no_connection_designator
                    stop_date = PC.no_connection_designator
                else:
                    start_date = connup.start_date
                    stop_date = connup.stop_date
                udn = connup.downstream_part + ':' + connup.down_part_rev
                pos = {'uStart': {'h': 0, 'm': -1}, 'uStop': {'h': 1, 'm': -1},
                       'Upstream': {'h': 2, 'm': 0},
                       'Output': {'h': 3, 'm': 1}, 'Input': {'h': 4, 'm': 2},
                       'Part': {'h': 5, 'm': 3}}
                if pos['uStart'][verbosity] > -1:
                    del tdata[pos['uStart'][verbosity]]
                    tdata.insert(pos['uStart'][verbosity], cm_utils._get_displayTime(start_date))
                if pos['uStop'][verbosity] > -1:
                    del tdata[pos['uStop'][verbosity]]
                    tdata.insert(pos['uStop'][verbosity], cm_utils._get_displayTime(stop_date))
                if pos['Upstream'][verbosity] > -1:
                    del tdata[pos['Upstream'][verbosity]]
                    tdata.insert(pos['Upstream'][verbosity], uup)
                if pos['Output'][verbosity] > -1:
                    del tdata[pos['Output'][verbosity]]
                    tdata.insert(pos['Output'][verbosity], connup.upstream_output_port)
                if pos['Input'][verbosity] > -1:
                    del tdata[pos['Input'][verbosity]]
                    tdata.insert(pos['Input'][verbosity], connup.downstream_input_port)
                if pos['Part'][verbosity] > -1:
                    del tdata[pos['Part'][verbosity]]
                    tdata.insert(pos['Part'][verbosity], '[' + udn + ']')
                # Do downstream
                if dn == PC.no_connection_designator:
                    conndn = PC.get_null_connection()
                else:
                    conndn = connection_dossier['connections'][dn]
                dup = conndn.upstream_part + ':' + conndn.up_part_rev
                ddn = conndn.downstream_part + ':' + conndn.down_part_rev
                if PC.no_connection_designator in ddn:
                    start_date = PC.no_connection_designator
                    stop_date = PC.no_connection_designator
                else:
                    start_date = conndn.start_date
                    stop_date = conndn.stop_date
                pos = {'Part': {'h': 5, 'm': 3}, 'Output': {'h': 6, 'm': 4},
                       'Input': {'h': 7, 'm': 5}, 'Downstream': {'h': 8, 'm': 6},
                       'dStart': {'h': 9, 'm': -1}, 'dStop': {'h': 10, 'm': -1}}
                if PC.no_connection_designator in udn:
                    if pos['Part'][verbosity] > -1:
                        del tdata[pos['Part'][verbosity]]
                        tdata.insert(pos['Part'][verbosity], '[' + dup + ']')
                if pos['Output'][verbosity] > -1:
                    del tdata[pos['Output'][verbosity]]
                    tdata.insert(pos['Output'][verbosity], conndn.upstream_output_port)
                if pos['Input'][verbosity] > -1:
                    del tdata[pos['Input'][verbosity]]
                    tdata.insert(pos['Input'][verbosity], conndn.downstream_input_port)
                if pos['Downstream'][verbosity] > -1:
                    del tdata[pos['Downstream'][verbosity]]
                    tdata.insert(pos['Downstream'][verbosity], ddn)
                if pos['dStart'][verbosity] > -1:
                    del tdata[pos['dStart'][verbosity]]
                    tdata.insert(pos['dStart'][verbosity], cm_utils._get_displayTime(start_date))
                if pos['dStop'][verbosity] > -1:
                    del tdata[pos['dStop'][verbosity]]
                    tdata.insert(pos['dStop'][verbosity], cm_utils._get_displayTime(stop_date))
                if verbosity == 'h' or verbosity == 'm':
                    table_data.append(tdata)
                else:
                    print("Connections")
        if verbosity == 'm' or verbosity == 'h':
            print(tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n')
        return already_shown

    def show_other_connections(self, connection_dossier, already_shown):
        """
        Shows the connections that are not active (the ones in connection_dossier
            but not in already_shown)

        Parameters
        -----------
        connection_dossier:  dictionary of connections from get_connections
        already_shown: list of shown connections from show_connections
        """

        for k, v in connection_dossier['connections'].iteritems():
            if k not in already_shown:
                print(v, v.start_date, v.stop_date)

    def get_part_types(self, at_date):
        """
        Goes through database and pulls out part types and some other info to
            display in a table.

        Returns part_type_dict, a dictionary keyed on part type

        Parameters
        -----------
        at_date:  date for part_types to be shown
        """

        self.part_type_dict = {}
        for part in self.session.query(PC.Parts).all():
            key = cm_utils._make_part_key(part.hpn, part.hpn_rev)
            if part.hptype not in self.part_type_dict.keys():
                self.part_type_dict[part.hptype] = {'part_list': [key],
                                                    'input_ports': [],
                                                    'output_ports': [],
                                                    'revisions': []}
            else:
                self.part_type_dict[part.hptype]['part_list'].append(key)
        for k in self.part_type_dict.keys():
            found_connection = False
            found_revisions = []
            input_ports = []
            output_ports = []
            for pa in self.part_type_dict[k]['part_list']:
                hpn, rev = cm_utils._split_part_key(pa)
                if rev not in found_revisions:
                    found_revisions.append(rev)
                if not found_connection:
                    pd = self.get_part_dossier([hpn], rev, at_date, exact_match=True, full_version=True)
                    if len(pd[pa]['input_ports']) > 0 or len(pd[pa]['output_ports']) > 0:
                        input_ports = pd[pa]['input_ports']
                        output_ports = pd[pa]['output_ports']
                        found_connection = True
            if len(input_ports) == 0:
                input_ports = [PC.no_connection_designator]
            if len(output_ports) == 0:
                output_ports = [PC.no_connection_designator]
            self.part_type_dict[k]['input_ports'] = input_ports
            self.part_type_dict[k]['output_ports'] = output_ports
            self.part_type_dict[k]['revisions'] = sorted(found_revisions)
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
            pts = ''
            for a in self.part_type_dict[k]['input_ports']:
                pts += (a + ', ')
            td.append(pts.strip().strip(','))
            pts = ''
            for b in self.part_type_dict[k]['output_ports']:
                pts += (b + ', ')
            td.append(pts.strip().strip(','))
            revs = ''
            for r in self.part_type_dict[k]['revisions']:
                revs += (r + ', ')
            td.append(revs.strip().strip(','))
            table_data.append(td)
        print('\n', tabulate(table_data, headers=headers, tablefmt='orgtbl'))
        print()
