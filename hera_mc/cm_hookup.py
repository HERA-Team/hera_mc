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
import warnings
from argparse import Namespace
from sqlalchemy import func


class Hookup:
    """
    Class to find and display the signal path hookup.
    """

    def __init__(self, session=None):
        """
        Hookup traces parts and connections through the signal path (as defined
            by the connections).
        The only external method is get_hookup(...)
        """

        if session is None:
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.handling = cm_handling.Handling(session)
        self.part_type_cache = {}

    def get_hookup(self, hpn_list, rev, port, at_date, exact_match=False,
                   show_levels=False, levels_testing=False):
        """
        Return the full hookup to the supplied part/rev/port in the form of a dictionary
        Returns hookup_dict, a dictionary with the following entries:
            'hookup': another dictionary keyed on part then pol (e/n)
            'columns': names of parts that are used in displaying the hookup as column headers
            'timing':  valid times for the corresponding hookup in dictionary
            'parts_epoch':  either ['parts_paper', full_path_list] or ['parts_hera', full_path_list]
            'fully_connected':  flags whether it is a full connection for corresponding hookup
            'levels':  correlator levels, if desired
        This only gets the contemporary hookups (unlike parts and connections,
            which get all.)  That is, only hookups valid at_date are returned.
            They are therefore only within one parts_epoch

        Parameters
        -----------
        hpn_list:  list of input hera part numbers (whole or first part thereof)
        rev:  the revision number
        port:  a specifiable port name,  default is 'all'.  Unverified.
        at_date:  date for hookup validity
        exact_match:  boolean for either exact_match or partial
        show_levels:  boolean to include correlator levels
        levels_testing:  if present and not False will pull levels from
                                     the file given in levels_testing
        """

        self.at_date = cm_utils._get_astropytime(at_date)

        # Get all the appropriate parts
        parts = self.handling.get_part_dossier(hpn_list=hpn_list, rev=rev,
                                               at_date=self.at_date,
                                               exact_match=exact_match,
                                               full_version=False)
        hookup_dict = {'hookup': {}, 'fully_connected': {}, 'parts_epoch': []}
        pols_to_do = self.__get_pols_to_do(hpn_list[0], port, check_pol=False)

        part_types_found = []
        for k, part in parts.iteritems():
            if not cm_utils._is_active(self.at_date, part['part'].start_date, part['part'].stop_date):
                continue
            hookup_dict['hookup'][k] = {}
            for pol in pols_to_do:
                hookup_dict['hookup'][k][pol] = self.__follow_hookup_stream(part['part'].hpn, part['part'].hpn_rev, pol)
                part_types_found = self.__get_part_types_found(hookup_dict['hookup'][k][pol], part_types_found)
        # Add other information in to the hookup_dict
        hookup_dict['columns'], hookup_dict['parts_epoch'] = self.__get_column_headers(part_types_found)
        if len(hookup_dict['columns']):
            hookup_dict = self.__add_hookup_timing_and_flags(hookup_dict)
            if show_levels:
                hookup_dict = self.__hookup_add_correlator_levels(hookup_dict, levels_testing)
        return hookup_dict

    def __get_part_types_found(self, huco, part_types_found):
        if not len(huco):
            return part_types_found
        for c in huco:
            part_type = self.handling.get_part_type_for(c.upstream_part).lower()
            self.part_type_cache[c.upstream_part] = part_type
            if part_type not in part_types_found:
                part_types_found.append(part_type)
        part_type = self.handling.get_part_type_for(huco[-1].downstream_part).lower()
        self.part_type_cache[huco[-1].downstream_part] = part_type
        if part_type not in part_types_found:
            part_types_found.append(part_type)
        return part_types_found

    def __get_pols_to_do(self, part, port, check_pol=False):
        all_pols = ['e', 'n']
        if port[0].lower() in all_pols:
            pols = [port[0].lower()]
        elif port.lower() in ['a', 'b']:
            pols = [part[-1].lower()]
        else:
            pols = all_pols
        if check_pol is not False:
            if check_pol in pols:
                pols = True
            else:
                pols = False
        return pols

    def __follow_hookup_stream(self, part, rev, pol):
        self.upstream = []
        self.downstream = []
        self.__recursive_go('up', part, rev, pol)
        self.__recursive_go('down', part, rev, pol)

        hu = []
        for pn in reversed(self.upstream):
            hu.append(pn)
        for pn in self.downstream:
            hu.append(pn)
        return hu

    def __recursive_go(self, direction, part, rev, pol):
        """
        Find the next connection up the signal chain.
        """
        conn = self.__get_next_connection(direction, part, rev, pol)
        if conn is not None:
            if direction == 'up':
                self.upstream.append(conn)
                part = conn.upstream_part
                rev = conn.up_part_rev
            else:
                self.downstream.append(conn)
                part = conn.downstream_part
                rev = conn.down_part_rev
            self.__recursive_go(direction, part, rev, pol)

    def __get_next_connection(self, direction, part, rev, pol):
        """
        Get next connected part going the given direction.
        """
        options = []
        if direction.lower() == 'up':      # Going upstream
            for conn in self.session.query(PC.Connections).filter(
                    (func.upper(PC.Connections.downstream_part) == part.upper()) &
                    (func.upper(PC.Connections.down_part_rev) == rev.upper())):
                conn.gps2Time()
                if cm_utils._is_active(self.at_date, conn.start_date, conn.stop_date):
                    nppart = conn.upstream_part
                    npport = conn.upstream_output_port
                    options.append(copy.copy(conn))
        elif direction.lower() == 'down':  # Going downstream
            for conn in self.session.query(PC.Connections).filter(
                    (func.upper(PC.Connections.upstream_part) == part.upper()) &
                    (func.upper(PC.Connections.up_part_rev) == rev.upper())):
                conn.gps2Time()
                if cm_utils._is_active(self.at_date, conn.start_date, conn.stop_date):
                    nppart = conn.downstream_part
                    npport = conn.downstream_input_port
                    options.append(copy.copy(conn))
        next_one = None
        if len(options) == 0:
            next_one = None
        elif len(options) == 1:
            next_one = options[0]
        else:
            for opc in options:
                if direction.lower() == 'up':
                    if self.__get_pols_to_do(opc.upstream_part, opc.upstream_output_port, check_pol=pol):
                        next_one = opc
                        break
                else:
                    if self.__get_pols_to_do(opc.downstream_part, opc.downstream_input_port, check_pol=pol):
                        next_one = opc
                        break
        return next_one

    def __add_hookup_timing_and_flags(self, hookup_dict):
        full_hookup_length = len(hookup_dict['parts_epoch']['path']) - 1
        hookup_dict['timing'] = {}
        hookup_dict['fully_connected'] = {}
        for akey, hk in hookup_dict['hookup'].iteritems():
            hookup_dict['timing'][akey] = {}
            hookup_dict['fully_connected'][akey] = {}
            for pkey, pol in hk.iteritems():
                latest_start = 0
                earliest_stop = None
                for c in pol:
                    if c.start_gpstime > latest_start:
                        latest_start = c.start_gpstime
                    if c.stop_gpstime is None:
                        pass
                    elif earliest_stop is None:
                        earliest_stop = c.stop_gpstime
                    elif c.stop_gpstime < earliest_stop:
                        earliest_stop = c.stop_gpstime
                hookup_dict['timing'][akey][pkey] = [latest_start, earliest_stop]
                hookup_dict['fully_connected'][akey][pkey] = (len(hookup_dict['hookup'][akey][pkey]) ==
                                                              full_hookup_length)
        hookup_dict['columns'].append('start')
        hookup_dict['columns'].append('stop')
        return hookup_dict

    def __get_column_headers(self, part_types_found):
        """
        The columns in the hookup_dict contain parts in the hookup chain and the column headers are
        the part types contained in that column.  This returns the headers for the retrieved hookup.

        It just checks which era the parts are in (parts_paper or parts_hera) and keeps however many
        parts are used.

        Parameters:
        -------------
        part_types_found:  list of the part types that were found
        """
        if len(part_types_found) == 0:
            return [], {}
        for sp in PC.full_connection_path.keys():
            is_this_one = sp
            for part_type in part_types_found:
                if part_type not in PC.full_connection_path[sp]:
                    is_this_one = False
                    break
        colhead = []
        if not is_this_one:
            raise ValueError('Parts did not conform to any parts epoch')
        else:
            parts_epoch = {'epoch': is_this_one, 'path': PC.full_connection_path[is_this_one]}
            for c in PC.full_connection_path[is_this_one]:
                if c in part_types_found:
                    colhead.append(c)

        return colhead, parts_epoch

    def __hookup_add_correlator_levels(self, hookup_dict, testing):
        warnings.warn("Warning:  correlator levels don't work with new pol hookup scheme yet (CM_HOOKUP[210]).")
        return hookup_dict
        hookup_dict['columns'].append('level')
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

    def get_correlator_input_from_hookup(self, hookup_dict):
        """
        Retrieve the correlator inputs from a hookup_dictionary.  This currently
        only allows for one entry in hookup_dict.  Need to rationalize.
        """
        if len(hookup_dict['hookup'].keys()) > 1:
            raise RuntimeError('Too many hookups provided to give e/n correlator inputs.')
        corr_input = {}
        corr_type_name = hookup_dict['parts_epoch']['path'][-1]
        if corr_type_name in hookup_dict['columns']:
            for k, h in hookup_dict['hookup'].iteritems():
                for j, p in h.iteritems():
                    corr_input[j] = p[-1].downstream_part
        return corr_input

    def get_station_from_hookup(self, hookup_dict):
        """
        Retrieve the station from a hookup_dictionary.  This currently
        only allows for one entry in hookup_dict.  Need to rationalize.
        """
        if len(hookup_dict['hookup'].keys()) > 1:
            raise RuntimeError('Too many hookups provided to give unique station.')
        station_name = None
        station_type_name = hookup_dict['parts_epoch']['path'][0]
        if station_type_name in hookup_dict['columns']:
            for k, h in hookup_dict['hookup'].iteritems():
                for j, p in h.iteritems():
                    station_name = p[0].upstream_part
        return station_name

    def is_fully_connected(self, hookup_dict, any_or_all='all'):
        num_fully_connected = 0
        num_in_dict = 0
        for akey, hk in hookup_dict['hookup'].iteritems():
            for pkey, pol in hk.iteritems():
                num_in_dict += 1
                if akey in hookup_dict['fully_connected'].keys() and \
                        hookup_dict['fully_connected'][akey][pkey]:
                    num_fully_connected += 1
        if any_or_all == 'all':
            return num_fully_connected == num_in_dict
        else:
            return num_fully_connected > 0

    def show_hookup(self, hookup_dict, cols_to_show='all', show_levels=False):
        """
        Print out the hookup table -- uses tabulate package.

        Parameters
        -----------
        hookup_dict:  generated in self.get_hookup
        cols_to_show:  list of columns to include in hookup listing
        show_levels:  boolean to either show the correlator levels or not
        """
        headers = self.__make_header_row(hookup_dict['columns'], cols_to_show)
        table_data = []
        for hukey in sorted(hookup_dict['hookup'].keys()):
            for pol in sorted(hookup_dict['hookup'][hukey].keys()):
                if len(hookup_dict['hookup'][hukey][pol]):
                    timing = hookup_dict['timing'][hukey][pol]
                    if show_levels:
                        level = hookup_dict['levels'][hukey][pol]
                    else:
                        level = False
                    td = self.__make_table_row(hookup_dict['hookup'][hukey][pol],
                                               headers, timing, level)
                    table_data.append(td)
        print('\n')
        print(tabulate(table_data, headers=headers, tablefmt='orgtbl'))
        print('\n')

    def __make_header_row(self, header_col_list, cols_to_show):
        headers = []
        show_flag = []
        for col in header_col_list:
            if cols_to_show[0].lower() == 'all' or col in cols_to_show:
                headers.append(col)
        return headers

    def __make_table_row(self, hup_list, headers, timing, show_level):
        td = ['-'] * len(headers)
        dip = ''
        j = 0  # This catches potentially duplicated part_type names
        for d in hup_list:
            part_type = self.part_type_cache[d.upstream_part]
            if part_type == headers[0]:
                td[0] = d.upstream_part + ':' + d.up_part_rev + ' <' + d.upstream_output_port
                dip = d.downstream_input_port + '> '
                j += 1
            else:
                if part_type in headers:
                    td[headers.index(part_type, j)] = dip + d.upstream_part + ':' + d.up_part_rev + ' <' + d.upstream_output_port
                    j += 1
                dip = d.downstream_input_port + '> '
        part_type = self.part_type_cache[d.downstream_part]
        if part_type in headers:
            td[headers.index(part_type, j)] = dip + d.downstream_part + ':' + d.down_part_rev
        if 'start' in headers:
            td[headers.index('start')] = timing[0]
        if 'stop' in headers:
            td[headers.index('stop')] = timing[1]
        if show_level:
            if 'level' in headers:
                td[headers.index('level')] = show_level
        return td
