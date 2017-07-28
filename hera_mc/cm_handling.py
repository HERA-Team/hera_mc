#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This is meant to hold helpful modules for parts and connections scripts contained within the Handling class.

"""
from __future__ import absolute_import, division, print_function
from tabulate import tabulate
import sys
import copy
from astropy.time import Time

from hera_mc import mc, geo_handling, correlator_levels, cm_utils
from hera_mc import part_connect as PC
from hera_mc import cm_part_revisions as cmpr


def _make_part_key(hpn, rev):
    return ":".join([hpn, rev])


def _split_part_key(key):
    return key.split(':')[0], key.split(':')[1]


def _make_connection_key(hpn, rev, port, direction, next_part, next_rev, next_port, start_gpstime):
    return ":".join([hpn, rev, port, direction, next_part, str(start_gpstime)])


class Handling:
    """
    Class to allow various manipulations of parts and their properties etc.  Things are 
    manipulated/passed as dictionaries currently.
    """
    no_connection_designator = '-X-'
    non_class_connections_dict_entries = ['ordered_pairs', no_connection_designator]

    def __init__(self, session=None):
        """
        session: session on current database. If session is None, a new session
                 on the default database is created and used.
        """
        if session is None:
            db = mc.connect_to_mc_db()
            self.session = db.sessionmaker()
        else:
            self.session = session

    def close(self):
        self.session.close()

    def is_in_connections(self, hpn_query, rev_query='ACTIVE', return_active=False):
        """
        checks to see if a part is in the connections database (which means it is also in parts)

        returns True/False, unless return_active True (return list of active connections)
        """

        connection_dict = self.get_connections(hpn_query, rev_query, port_query='all', exact_match=True,
                                               return_dictionary=True, show_connection=False)
        num_connections = len(connection_dict.keys())
        if num_connections == len(self.non_class_connections_dict_entries):
            found_connected = False
        else:
            found_connected = True
            if return_active:
                connections_found = []
                current = cm_utils._get_datetime(self.args.date, self.args.time)
                for c in connection_dict.keys():
                    if c in self.non_class_connections_dict_entries:
                        continue
                    if cm_utils._is_active(current, connection_dict[c].start_date, connection_dict[c].stop_date):
                        connections_found.append(c)
                if len(connections_found) > 0:
                    found_connected = connections_found
        return found_connected

    def get_part_dossier(self, hpn_query, rev_query, exact_match=False):
        """
        Return information on a part.  It will return all matching first characters unless exact_match==True.
        It gets all parts, the receiving module should filter on e.g. date if desired.

        Returns part_dossier: {'part':CLASS , 'part_info':CLASS, 
                               'connections':CLASS, 'geo':CLASS,
                               'input_ports':[],'output_ports':[]}

        Parameters
        -----------
        hpn_query:  the input hera part number (whole or first part thereof)
        rev_query:  specific revision or category.
        exact_match:  boolean to enforce full part number match
        """

        if not exact_match and hpn_query[-1] != '%':
            hpn_query = hpn_query + '%'

        part_dossier = {}
        rev_part = {}
        for part in self.session.query(PC.Parts).filter(PC.Parts.hpn.like(hpn_query)):
            rev_part[part.hpn] = cmpr.get_revisions_of_type(rev_query, part.hpn, self.session)

        # Now get unique part/revs and put into dictionary
        for hpn in rev_part.keys():
            if rev_part[hpn] is None:
                continue
            for rev in rev_part[hpn]:
                this_rev = rev[0]
                part_query = self.session.query(PC.Parts).filter((PC.Parts.hpn == hpn) &
                                                                 (PC.Parts.hpn_rev == this_rev))
                part_cnt = part_query.count()
                if part_cnt == 0:
                    continue
                elif part_cnt == 1:
                    part = copy.copy(part_query.all()[0])
                    part.gps2Time()
                    pr_key = _make_part_key(part.hpn, part.hpn_rev)
                    part_dossier[pr_key] = {'part': part,        'part_info': None,
                                            'input_ports': [],   'output_ports': [],
                                            'connections': None, 'geo': None}
                    for part_info in self.session.query(PC.PartInfo).filter((PC.PartInfo.hpn == part.hpn) &
                                                                            (PC.PartInfo.hpn_rev == part.hpn_rev)):
                        part_info.gps2Time()
                        part_dossier[pr_key]['part_info'] = part_info
                    connections = self.get_connections(hpn_query=part.hpn, rev_query=part.hpn_rev, port_query='all',
                                                       exact_match=True, return_dictionary=True, show_connection=False)
                    part_dossier[pr_key]['connections'] = connections
                    if part.hptype == 'station':
                        part_dossier[pr_key]['geo'] = geo_handling.get_location([part.hpn], query_date, show_location=False)
                    part_dossier[pr_key]['input_ports'], part_dossier[pr_key]['output_ports'] = \
                                                          self.find_ports(part_dossier[pr_key]['connections'])
                else:
                    print("cm_handling[135]:  Warning: should only be one part/rev.", part.hpn, part.hpn_rev)
        return part_dossier

    def find_ports(self, connections_dict):
        input_ports = []
        output_ports = []
        for k, v in connections_dict.iteritems():
            if k in self.non_class_connections_dict_entries:
                continue
            if ':up:' in k and v.downstream_input_port not in input_ports:
                input_ports.append(v.downstream_input_port)
            elif ':down:' in k and v.upstream_output_port not in output_ports:
                output_ports.append(v.upstream_output_port)
            else:
                print("cm_handling[149]: Warning: Connection key not compliant, so ignoring ", k)
        input_ports.sort()
        output_ports.sort()
        return input_ports, output_ports

    def show_part(self, part_dossier):
        """
        Print out part information.  Uses tabulate package.

        Parameters
        -----------
        part_dossier:  input dictionary of parts, generated by self.get_part
        """
        if len(part_dossier.keys()) == 0:
            print('Part not found')
            return
        table_data = []
        if self.args.verbosity == 'm':
            headers = ['HERA P/N', 'Rev', 'Part Type', 'Mfg #', 'Start', 'Stop', 'Active']
        elif self.args.verbosity == 'h':
            headers = ['HERA P/N', 'Rev', 'Part Type', 'Mfg #', 'Start', 'Stop', 'Active', 'Input', 'Output', 'Info', 'Geo']
        for hpnr in sorted(part_dossier.keys()):
            pdpart = part_dossier[hpnr]['part']
            is_active = cm_utils._is_active(part_dossier['date'], pdpart.start_date, pdpart.stop_date)
            is_connected = 'Yes' if (is_active and len(part_dossier[hpnr]['connections']) > 0) else 'N/C' if is_active else 'No'
            if self.args.verbosity == 'l':
                print(pdpart)
            else:
                tdata = [pdpart.hpn, pdpart.hpn_rev, pdpart.hptype, pdpart.manufacturer_number,
                         cm_utils._get_displayTime(pdpart.start_date), cm_utils._get_displayTime(pdpart.stop_date), is_connected]
                if self.args.verbosity == 'h':
                    ptsin = ''
                    ptsout = ''
                    for k in part_dossier[hpnr]['input_ports']:
                        ptsin += k + ', '
                    for k in part_dossier[hpnr]['output_ports']:
                        ptsout += k + ', '
                    tdata.append(ptsin.strip().strip(','))
                    tdata.append(ptsout.strip().strip(','))
                    comment = part_dossier[hpnr]['part_info'].comment if (part_dossier[hpnr]['part_info'] is not None) else None
                    tdata.append(comment)
                    if part_dossier[hpnr]['geo'] is not None:
                        tdata.append("{:.1f}E, {:.1f}N, {:.1f}m".format(part_dossier[hpnr]['geo'].easting,
                                                                        part_dossier[hpnr]['geo'].northing, 
                                                                        part_dossier[hpnr]['geo'].elevation))
                    else:
                        tdata.append(None)
                    table_data.append(tdata)
        print('\n' + tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n')

    def get_connections(self, hpn_query=None, rev_query=None, port_query=None, exact_match=False,
                        return_dictionary=True, show_connection=False):
        """
        Return information on parts connected to hpn_query (args.connection)
        It should get connections immediately adjacent to one part (upstream and downstream).
        It does not filter on date but gets all.  The receiving (or showing module) should filter
           on date if desired.

        Returns connection_dict, a dictionary keyed on part number of adjacent connections

        Parameters
        -----------
        args:  arguments as per mc and parts argument parser
        hpn_query:  the input hera part number (whole or first part thereof)
        port_query:  a specifiable port name,  default is 'all'
        exact_match:  boolean to enforce full part number match
        show_connection:  boolean to call show_part or not
        """
        args = self.args
        if hpn_query is None:
            hpn_query = args.connection
            exact_match = args.exact_match
        if rev_query is None:
            rev_query = args.revision
        if not exact_match and hpn_query[-1] != '%':
            hpn_query = hpn_query + '%'
        if port_query is None:
            port_query = args.specify_port
        current = cm_utils._get_datetime(args.date, args.time)
        connection_dict = {'ordered_pairs': []}
        db = mc.connect_to_mc_db(args)
        with db.sessionmaker() as session:
            rev_part = {}
            for part in session.query(PC.Parts).filter(PC.Parts.hpn.like(hpn_query)):
                rev_part[part.hpn] = cmpr.get_revisions_of_type(args, rev_query, part.hpn)
            for hpn in rev_part.keys():
                if rev_part[hpn] is None:
                    continue
                for rev in rev_part[hpn]:
                    up_parts = []
                    down_parts = []
                    this_rev = rev[0]
                    # Find where the part is in the upward position, so identify its downward connection
                    for conn in session.query(PC.Connections).filter((PC.Connections.upstream_part == hpn) &
                                                                               (PC.Connections.up_part_rev == this_rev)):
                        if port_query.lower() == 'all' or conn.upstream_output_port.lower() == port_query.lower():
                            conn.gps2Time()
                            prc_key = _make_connection_key(hpn, this_rev, conn.upstream_output_port, 'down',
                                                           conn.downstream_part, conn.down_part_rev, conn.downstream_input_port,
                                                           conn.start_gpstime)
                            connection_dict[prc_key] = copy.copy(conn)
                            if cm_utils._is_active(current, conn.start_date, conn.stop_date):
                                down_parts.append(prc_key)
                    # Find where the part is in the downward position, so identify its upward connection
                    for conn in session.query(PC.Connections).filter((PC.Connections.downstream_part == hpn) &
                                                                               (PC.Connections.down_part_rev == this_rev)):
                        if port_query.lower() == 'all' or conn.downstream_input_port.lower() == port_query.lower():
                            conn.gps2Time()
                            prc_key = _make_connection_key(hpn, this_rev, conn.downstream_input_port, 'up',
                                                           conn.upstream_part, conn.up_part_rev, conn.upstream_output_port,
                                                           conn.start_gpstime)
                            connection_dict[prc_key] = copy.copy(conn)
                            if cm_utils._is_active(current, conn.start_date, conn.stop_date):
                                up_parts.append(prc_key)
                    if len(up_parts) == 0:
                        up_parts = [self.no_connection_designator]
                    if len(down_parts) == 0:
                        down_parts = [self.no_connection_designator]
                    up_parts.sort()
                    down_parts.sort()
                    if len(up_parts) > len(down_parts):
                        down_parts = (down_parts + len(up_parts) * [down_parts[-1]])[:len(up_parts)]
                    elif len(down_parts) > len(up_parts):
                        up_parts = (up_parts + len(down_parts) * [up_parts[-1]])[:len(down_parts)]
                    connection_dict['ordered_pairs'].append([sorted(up_parts), sorted(down_parts)])
        ###I forget why I did this
        nc = self.no_connection_designator
        connection_dict[nc] = PC.Connections(upstream_part=nc, upstream_output_port=nc, up_part_rev=nc,
                                                       downstream_part=nc, downstream_input_port=nc, down_part_rev=nc,
                                                       start_gpstime=cm_utils._get_datetime('<', '<').gps,
                                                       stop_gpstime=cm_utils._get_datetime('>', '>').gps)
        if show_connection:
            already_shown = self.show_active_connections(connection_dict)
            if not args.active:
                self.show_other_connections(connection_dict, already_shown)
        if return_dictionary:
            return connection_dict

    def show_active_connections(self, connection_dict):
        """
        Print out active connection information.  Uses tabulate package.

        Parameters
        -----------
        connection_dict:  input dictionary of parts, generated by self.get_connection
        """
        print("ACTIVE")
        current = cm_utils._get_datetime(self.args.date, self.args.time)
        table_data = []
        already_shown = []
        vb = self.args.verbosity
        if vb == 'm':
            headers = ['Upstream', '<Output:', ':Input>', 'Part', '<Output:', ':Input>', 'Downstream']
        elif vb == 'h':
            headers = ['uStart', 'uStop', 'Upstream', '<Output:', ':Input>', 'Part', '<Output:', ':Input>', 'Downstream', 'dStart', 'dStop']
        for ordered_pairs in connection_dict['ordered_pairs']:
            for up, dn in zip(ordered_pairs[0], ordered_pairs[1]):
                if self.no_connection_designator in up and self.no_connection_designator in dn:
                    continue
                already_shown.append(up)
                already_shown.append(dn)
                tdata = range(0, len(headers))
                # Do upstream
                connup = connection_dict[up]
                uup = connup.upstream_part + ':' + connup.up_part_rev
                if self.no_connection_designator in uup:
                    start_date = self.no_connection_designator
                    stop_date = self.no_connection_designator
                else:
                    start_date = connup.start_date
                    stop_date = connup.stop_date
                udn = connup.downstream_part + ':' + connup.down_part_rev
                pos = {'uStart': {'h': 0, 'm': -1}, 'uStop': {'h': 1, 'm': -1}, 'Upstream': {'h': 2, 'm': 0},
                       'Output': {'h': 3, 'm': 1},  'Input': {'h': 4, 'm': 2},      'Part': {'h': 5, 'm': 3}}
                if pos['uStart'][vb] > -1:
                    del tdata[pos['uStart'][vb]]
                    tdata.insert(pos['uStart'][vb], cm_utils._get_displayTime(start_date))
                if pos['uStop'][vb] > -1:
                    del tdata[pos['uStop'][vb]]
                    tdata.insert(pos['uStop'][vb], cm_utils._get_displayTime(stop_date))
                if pos['Upstream'][vb] > -1:
                    del tdata[pos['Upstream'][vb]]
                    tdata.insert(pos['Upstream'][vb], uup)
                if pos['Output'][vb] > -1:
                    del tdata[pos['Output'][vb]]
                    tdata.insert(pos['Output'][vb], connup.upstream_output_port)
                if pos['Input'][vb] > -1:
                    del tdata[pos['Input'][vb]]
                    tdata.insert(pos['Input'][vb], connup.downstream_input_port)
                if pos['Part'][vb] > -1:
                    del tdata[pos['Part'][vb]]
                    tdata.insert(pos['Part'][vb], '[' + udn + ']')
                # Do downstream
                conndn = connection_dict[dn]
                dup = conndn.upstream_part + ':' + conndn.up_part_rev
                ddn = conndn.downstream_part + ':' + conndn.down_part_rev
                if self.no_connection_designator in ddn:
                    start_date = self.no_connection_designator
                    stop_date = self.no_connection_designator
                else:
                    start_date = conndn.start_date
                    stop_date = conndn.stop_date
                pos = {'Part': {'h': 5, 'm': 3}, 'Output': {'h': 6, 'm': 4}, 'Input': {'h': 7, 'm': 5}, 'Downstream': {'h': 8, 'm': 6},
                       'dStart': {'h': 9, 'm': -1}, 'dStop': {'h': 10, 'm': -1}}
                if self.no_connection_designator in udn:
                    if pos['Part'][vb] > -1:
                        del tdata[pos['Part'][vb]]
                        tdata.insert(pos['Part'][vb], '[' + dup + ']')
                if pos['Output'][vb] > -1:
                    del tdata[pos['Output'][vb]]
                    tdata.insert(pos['Output'][vb], conndn.upstream_output_port)
                if pos['Input'][vb] > -1:
                    del tdata[pos['Input'][vb]]
                    tdata.insert(pos['Input'][vb], conndn.downstream_input_port)
                if pos['Downstream'][vb] > -1:
                    del tdata[pos['Downstream'][vb]]
                    tdata.insert(pos['Downstream'][vb], ddn)
                if pos['dStart'][vb] > -1:
                    del tdata[pos['dStart'][vb]]
                    tdata.insert(pos['dStart'][vb], cm_utils._get_displayTime(start_date))
                if pos['dStop'][vb] > -1:
                    del tdata[pos['dStop'][vb]]
                    tdata.insert(pos['dStop'][vb], cm_utils._get_displayTime(stop_date))
                if vb == 'h' or vb == 'm':
                    table_data.append(tdata)
                else:
                    print("Connections")
        if vb == 'm' or vb == 'h':
            print(tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n')
        return already_shown

    def show_other_connections(self, connection_dict, already_shown):
        print("OTHER")
        for k, v in connection_dict.iteritems():
            if k in self.non_class_connections_dict_entries:
                continue
            elif k in already_shown:
                continue
            else:
                print(v, v.start_date, v.stop_date)

    def get_part_types(self, show_hptype=False):
        """
        Goes through database and pulls out part types and some other info to display in a table.

        Returns part_type_dict, a dictionary keyed on part type

        Parameters
        -----------
        args:  arguments as per mc and parts argument parser
        show_hptype:  boolean variable to print it out
        """

        self.part_type_dict = {}
        db = mc.connect_to_mc_db(self.args)
        with db.sessionmaker() as session:
            for part in session.query(PC.Parts).all():
                key = _make_part_key(part.hpn, part.hpn_rev)
                if part.hptype not in self.part_type_dict.keys():
                    self.part_type_dict[part.hptype] = {'part_list': [key], 'input_ports': [], 'output_ports': [], 'revisions': []}
                else:
                    self.part_type_dict[part.hptype]['part_list'].append(key)
        if show_hptype:
            headers = ['Part type', '# in dbase', 'Input ports', 'Output ports', 'Revisions']
            table_data = []
        for k in self.part_type_dict.keys():
            found_connection = False
            found_revisions = []
            input_ports = []
            output_ports = []
            for pa in self.part_type_dict[k]['part_list']:
                hpn, rev = _split_part_key(pa)
                if rev not in found_revisions:
                    found_revisions.append(rev)
                if not found_connection:
                    pd = self.get_part(hpn, rev, show_part=False)
                    if len(pd[pa]['input_ports']) > 0 or len(pd[pa]['output_ports']) > 0:
                        input_ports = pd[pa]['input_ports']
                        output_ports = pd[pa]['output_ports']
                        found_connection = True
            if len(input_ports) == 0:
                input_ports = [self.no_connection_designator]
            if len(output_ports) == 0:
                output_ports = [self.no_connection_designator]
            self.part_type_dict[k]['input_ports'] = input_ports
            self.part_type_dict[k]['output_ports'] = output_ports
            self.part_type_dict[k]['revisions'] = sorted(found_revisions)
            if show_hptype:
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
        if show_hptype:
            print('\n', tabulate(table_data, headers=headers, tablefmt='orgtbl'))
        print()
        return self.part_type_dict
