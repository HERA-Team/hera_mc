#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This is computes and displays part hookups.

"""
from __future__ import absolute_import, division, print_function
from tabulate import tabulate
import sys

from hera_mc import mc, geo_location, correlator_levels, cm_utils, cm_handling
from hera_mc import part_connect as PC
import copy
from difflib import SequenceMatcher


def _make_hookup_key(hpn, rev, port, sn):
    return ":".join([hpn, rev, port, sn])


class Hookup:
    """
    Class to find and display the hookup.
    """

    def __init__(self, session=None):
        """
        Hookup traces parts and connections through the signal path (as defined by the connections).
        Generally will only call _.get_hookup()
        """

        if session is None:
            db = mc.connect_to_mc_db()
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.handling = cm_handling.Handling(session)

    def __get_connection(self, direction, part, rev, port):
        """
        Get next parts going the given direction.
        """
        options = []
        if direction == 'up':      # Going upstream
            for conn in self.session.query(PC.Connections).filter((PC.Connections.downstream_part == part) &
                                                                  (PC.Connections.down_part_rev == rev)):
                conn.gps2Time()
                if cm_utils._is_active(self.at_date, conn.start_date, conn.stop_date):
                    options.append(copy.copy(conn))
        elif direction == 'down':  # Going downstream
            for conn in self.session.query(PC.Connections).filter((PC.Connections.upstream_part == part) &
                                                                  (PC.Connections.up_part_rev == rev)):
                conn.gps2Time()
                if cm_utils._is_active(self.at_date, conn.start_date, conn.stop_date):
                    options.append(copy.copy(conn))
        use_this = self.__wade_through_the_messy_stuff(options, direction=direction)
        return use_this

    def __wade_through_the_messy_stuff(self, options, how_many=False, direction=None):
        """
        For now put all of the messy, system specific, ad hoc ugly stuff here -- hopefully make it elegant later
        """
        if how_many:  # Return how many streams to do.  Is here to keep the ugly together - and make it even uglier!
            inp = len(options['input_ports'])
            outp = len(options['output_ports'])
            if inp == 0:  # it is a station
                rv = 2
            elif options['part'].hpn[-1] in ['E', 'N']:
                rv = 1
            elif inp == 1 and outp > 0:  # they are different since in get_hookup we loop over input ports unless it's a station
                rv = 2
            else:
                rv = 1
            self.__how_many = rv
        else:
            if options is None or len(options) == 0:
                rv = None
            elif len(options) == 1:
                rv = options[0]
            else:  # Figures out which port to use.  This sort of works for now, not guaranteed
                if self.__how_many == 1:
                    srn = -1
                    ports_ratio = []
                    for i, optn in enumerate(options):
                        if direction == 'up':
                            ports_ratio.append(SequenceMatcher(None, optn.upstream_output_port, self.__first_port).ratio())
                            if optn.downstream_input_port[0] == self.__first_port[0]:
                                srn = i
                        elif direction == 'down':
                            ports_ratio.append(SequenceMatcher(None, optn.downstream_input_port, self.__first_port).ratio())
                            if optn.upstream_output_port[0] == self.__first_port[0]:
                                srn = i
                    if srn == -1:
                        srn = ports_ratio.index(max(ports_ratio))
                else:
                    srn = self.__series_number
                rv = options[srn]
        return rv

    def __recursive_go(self, direction, part, rev, port):
        """
        Find the next connection up the signal chain.
        """
        conn = self.__get_connection(direction, part, rev, port)
        if conn is not None:
            if direction == 'up':
                self.upstream.append(conn)
                part = conn.upstream_part
                rev = conn.up_part_rev
                port = conn.upstream_output_port
            else:
                self.downstream.append(conn)
                part = conn.downstream_part
                rev = conn.down_part_rev
                port = conn.downstream_input_port
            self.__recursive_go(direction, part, rev, port)

    def __follow_hookup_stream(self, part, rev, port, sn):
        self.__series_number = sn
        self.__first_port = port
        self.upstream = []
        self.downstream = []
        self.__recursive_go('up', part, rev, port)
        self.__recursive_go('down', part, rev, port)

        hu = []
        for pn in reversed(self.upstream):
            hu.append(pn)
        for pn in self.downstream:
            hu.append(pn)
        return hu

    def get_hookup(self, hpn, rev, port, at_date, state_args, exact_match=False):
        """
        Return the full hookup.
        Returns hookup_dict, a dictionary keyed on derived key of hpn:port.
        This only gets the contemporary hookups (unlike parts and connections, which get all.)

        Parameters
        -----------
        hpn:  the input hera part number (whole or first part thereof)
        rev_:  the revision number
        port_:  a specifiable port name,  default is 'all'.  Unverified.
        at_date:  date for hookup validity
        state_args:  keyword dictionary specifying parameters for hookup
        exact_match:  boolean for either exact_match or partial
        """

        self.at_date = cm_utils._get_datetime(at_date)

        # Get all the appropriate parts
        parts = self.handling.get_part_dossier(hpn=hpn, rev=rev, at_date=self.at_date, exact_match=exact_match)
        hookup_dict = {'hookup':{}}
        col_len_max = [0, '-']

        for hpnr in parts.keys():
            if not cm_utils._is_active(self.at_date, parts[hpnr]['part'].start_date, parts[hpnr]['part'].stop_date):
                continue
            if len(parts[hpnr]['connections']['ordered-pairs'][0]) == 0:
                continue
            how_many_to_do = self.__wade_through_the_messy_stuff(parts[hpnr], True)

            parts[hpnr]['input_ports'].sort()
            parts[hpnr]['output_ports'].sort()
            if type(port) == str and port.lower() == 'all':
                port_query_loop = parts[hpnr]['input_ports']
                if len(port_query_loop) == 0:
                    port_query_loop = parts[hpnr]['output_ports']
            else:  # This to handle range of port_query possibilities outside of 'all'
                print("Not really supported.  Need a way to check if upstream or downstream port etcetc")
                if type(port) != list:
                    port_query_loop = [port]

            for i, p in enumerate(port_query_loop):
                for sn in range(how_many_to_do):
                    hukey = _make_hookup_key(parts[hpnr]['part'].hpn, parts[hpnr]['part'].hpn_rev, p, str(sn))
                    hookup_dict['hookup'][hukey] = self.__follow_hookup_stream(parts[hpnr]['part'].hpn, parts[hpnr]['part'].hpn_rev, p, sn)
                    if len(hookup_dict['hookup'][hukey]) > col_len_max[0]:
                        col_len_max[0] = len(hookup_dict['hookup'][hukey])
                        col_len_max[1] = hukey
        if len(hookup_dict['hookup'].keys()) == 0:
            print(hpn, rev, 'not active')
            return None

        hookup_dict['columns'] = self.__get_column_header(hookup_dict['hookup'][col_len_max[1]])
        if state_args['show-levels']:
            hookup_dict = self.__hookup_add_correlator_levels(hookup_dict, state_args['levels_testing'])

        return hookup_dict

    def __get_column_header(self, hup0):
        parts_col = []
        for hu in hup0:
            get_part_type = self.handling.get_part_dossier(hpn=hu.upstream_part, rev=hu.up_part_rev,
                                                           at_date=self.at_date, exact_match=True)
            pr_key = cm_utils._make_part_key(hu.upstream_part, hu.up_part_rev)
            parts_col.append(get_part_type[pr_key]['part'].hptype)
        hu = hup0[-1]
        get_part_type = self.handling.get_part_dossier(hpn=hu.downstream_part, rev=hu.down_part_rev,
                                                       at_date=self.at_date, exact_match=True)
        pr_key = cm_utils._make_part_key(hu.downstream_part, hu.down_part_rev)
        parts_col.append(get_part_type[pr_key]['part'].hptype)
        return parts_col

    def __hookup_add_correlator_levels(self, hookup_dict, testing):
        hookup_dict['columns'].append('levels')
        hookup_dict['levels'] = {}
        pf_input = []
        for k in sorted(hookup_dict['hookup'].keys()):
            f_engine = hookup_dict['hookup'][k][-1].downstream_part
            pf_input.append(f_engine)
        levels = correlator_levels.get_levels(pf_input, testing)
        for i, k in enumerate(sorted(hookup_dict['hookup'].keys())):
            lstr = '%s' % (levels[i])
            hookup_dict['levels'][k] = lstr
        return hookup_dict

    def __header_entry_name_adjust(self, col):
        if col[-2:] == '_e' or col[-2:] == '_n':  # Makes these specific pol parts generic
            colhead = col[:-2]
        else:
            colhead = col
        return colhead

    def show_hookup(self, hookup_dict, cols_to_show, show_levels):
        """
        Print out the hookup table -- uses tabulate package.

        Parameters
        -----------
        hookup_dict:  generated in self.get_hookup
        cols_to_show:  list of columns to include in hookup listing
        show_levels:  boolean to either show the correlator levels or not
        """

        headers, show_flag = self.__make_header_row(hookup_dict['columns'], cols_to_show, show_levels)

        table_data = []
        for hukey in sorted(hookup_dict['hookup'].keys()):
            if show_levels:
                level = hookup_dict['levels'][hukey]
            else:
                level = False
            td = self.__make_table_row(hookup_dict['hookup'][hukey], headers, show_flag, level)
            table_data.append(td)
        print('\n')
        print(tabulate(table_data, headers=headers, tablefmt='orgtbl'))
        print('\n')

    def __make_header_row(self, header_col, cols_to_show, show_levels):
        headers = []
        show_flag = []
        if cols_to_show != 'all':
            cols_to_show = cols_to_show.split(',')
        for col in header_col:
            colhead = self.__header_entry_name_adjust(col)
            if cols_to_show == 'all' or colhead in cols_to_show:
                show_flag.append(True)
                headers.append(colhead)
            else:
                show_flag.append(False)
        return headers, show_flag

    def __make_table_row(self, hup, headers, show_flag, show_level):
        nc = '-'
        td = []
        if show_flag[0]:
            pn = hup[0]
            prpn = pn.upstream_part + ':' + pn.up_part_rev + ' <' + pn.upstream_output_port
            td.append(prpn)
        for i in range(1, len(hup)):
            if show_flag[i]:
                pn = hup[i - 1]
                prpn = pn.downstream_input_port + '> ' + pn.downstream_part + ':' + pn.down_part_rev
                pn = hup[i]
                prpn += ' <' + pn.upstream_output_port
                td.append(prpn)
        if show_flag[-1]:
            pn = hup[-1]
            prpn = pn.downstream_input_port + '> ' + pn.downstream_part + ':' + pn.down_part_rev
            td.append(prpn)
        if show_level:
            td.append(show_level)
        if len(td) != len(headers):
            new_hup = []
            nc = '-'
            for hdr in headers:
                if hdr == 'levels':
                    continue
                for hu in hup:
                    get_part_type = self.handling.get_part(hpn_query=hu.upstream_part, rev_query=hu.up_part_rev,
                                                           exact_match=True, return_dictionary=True, show_part=False)
                    pr_key = cm_handling._make_part_key(hu.upstream_part, hu.up_part_rev)
                    part_col = get_part_type[pr_key]['part'].hptype
                    if self.__header_entry_name_adjust(part_col) == hdr:
                        new_hup.append(hu)
                        break
                else:
                    get_part_type = self.handling.get_part(hpn_query=hu.downstream_part, rev_query=hu.down_part_rev,
                                                           exact_match=True, return_dictionary=True, show_part=False)
                    pr_key = cm_handling._make_part_key(hu.downstream_part, hu.down_part_rev)
                    part_col = get_part_type[pr_key]['part'].hptype
                    if self.__header_entry_name_adjust(part_col) == hdr:
                        continue
                    else:
                        new_hup.append(PC.Connections(upstream_part=nc, up_part_rev=nc, upstream_output_port=nc,
                                                      downstream_part=nc, down_part_rev=nc, downstream_input_port=nc))
            td = self.__make_table_row(new_hup, headers, show_flag, show_level)
        return td
