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
            db = mc.connect_to_mc_db()
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.handling = cm_handling.Handling(session)

    def get_hookup(self, hpn, rev, port, at_date, exact_match=False, show_levels=False, levels_testing=False):
        """
        Return the full hookup to the supplied part/rev/port in the form of a dictionary
        Returns hookup_dict, a dictionary with three to four entries:
            'hookup': another dictionary keyed on part:rev then pol (e/n)
            'columns': names of parts that are used in displaying the hookup as
                       column headers
            'timing':  valid times for the corresponding hookup in dictionary
            'levels':  correlator levels, if desired
        This only gets the contemporary hookups (unlike parts and connections,
            which get all.)  That is, only hookups valid at_date are returned.
        Note that this also assumes all hookups returned are connected at the same
            furthest upstream place.  This means that the columns heading won't match
            if valid hookups for a list start at different upstream locations.  The plan
            is to fix that.


        Parameters
        -----------
        hpn:  the input hera part number (whole or first part thereof)
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
        parts = self.handling.get_part_dossier(hpn=hpn, rev=rev,
                                               at_date=self.at_date,
                                               exact_match=exact_match)
        hookup_dict = {'hookup': {}}
        pols_to_do = self.__get_pols_to_do(hpn, port, check_pol=False)

        for k, part in parts.iteritems():
            if not cm_utils._is_active(self.at_date, part['part'].start_date, part['part'].stop_date):
                continue
            hookup_dict['hookup'][k] = {}
            for pol in pols_to_do:
                hookup_dict['hookup'][k][pol] = self.__follow_hookup_stream(part['part'].hpn, part['part'].hpn_rev, pol)
        if len(hookup_dict['hookup'].keys()) == 0:
            hookup_dict['columns'] = []
        else:
            hookup_dict = self.__add_hookup_timing(hookup_dict)
            hookup_dict['columns'] = self.__get_column_headers(hookup_dict['hookup'])
            if show_levels:
                hookup_dict = self.__hookup_add_correlator_levels(hookup_dict, levels_testing)

        return hookup_dict

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
                    (PC.Connections.downstream_part == part) &
                    (PC.Connections.down_part_rev == rev)):
                conn.gps2Time()
                if cm_utils._is_active(self.at_date, conn.start_date, conn.stop_date):
                    nppart = conn.upstream_part
                    npport = conn.upstream_output_port
                    options.append(copy.copy(conn))
        elif direction.lower() == 'down':  # Going downstream
            for conn in self.session.query(PC.Connections).filter(
                    (PC.Connections.upstream_part == part) &
                    (PC.Connections.up_part_rev == rev)):
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

    def __add_hookup_timing(self, hookup_dict):
        really_late = 9999999999
        hookup_dict['timing'] = {}
        for akey, hk in hookup_dict['hookup'].iteritems():
            hookup_dict['timing'][akey] = {}
            for pkey, pol in hk.iteritems():
                latest_start = 0
                earliest_stop = really_late
                for c in pol:
                    if c.start_gpstime > latest_start:
                        latest_start = c.start_gpstime
                    if c.stop_gpstime is not None and c.stop_gpstime < earliest_stop:
                        earliest_stop = c.stop_gpstime
                if earliest_stop == really_late:
                    earliest_stop = None
                hookup_dict['timing'][akey][pkey] = [latest_start, earliest_stop]
        return hookup_dict

    def __get_column_headers(self, huh):
        """
        The columns in the hookup_dict contain parts in the hookup chain and the column headers are 
        the part types contained in that column.  This returns the headers for the retrieved hookup.
        This gets the full set of headers for a future show_hookup that doesn't require the same
        hookup starting point.  

        Returns a single column for now (the one/long_column stuff).

        The method searches all of the hookup chains to find the longest one and returns those
        part-type header names.

        Parameters: 
        -------------
        huh: the 'hookup' part of the hookup_dictionary
        """

        if len(huh) == 0:
            return []
        # This tracks the part and pol keys for the longest hookup
        lc = Namespace(part=huh.keys()[0], pol=huh[huh.keys()[0]].keys()[0], hlen=0)
        hu_col = {}
        return_one_column_for_now = True
        if return_one_column_for_now:  # This is to just not find part_dossiers on everything for now
            for hk, hu in huh.iteritems():
                for pk, pv in hu.iteritems():
                    if len(pv) > lc.hlen:
                        lc.part=hk; lc.pol=pk; lc.hlen=len(pv)
            huh = {hk: {pk: huh[lc.part][lc.pol]}}

        lc.hlen=0
        for hk, hu in huh.iteritems():
            hu_col[hk] = {}
            for pk, pv in hu.iteritems():
                if len(pv) == 0:
                    continue
                hu_col[hk][pk] = []
                for h in pv:
                    get_part_type = self.handling.get_part_dossier(hpn=h.upstream_part,
                                                                   rev=h.up_part_rev,
                                                                   at_date=self.at_date,
                                                                   exact_match=True)
                    pr_key = cm_utils._make_part_key(h.upstream_part, h.up_part_rev)
                    hu_col[hk][pk].append(get_part_type[pr_key]['part'].hptype)
                h = pv[-1]
                get_part_type = self.handling.get_part_dossier(hpn=h.downstream_part,
                                                               rev=h.down_part_rev,
                                                               at_date=self.at_date,
                                                               exact_match=True)
                pr_key = cm_utils._make_part_key(h.downstream_part, h.down_part_rev)
                hu_col[hk][pk].append(get_part_type[pr_key]['part'].hptype)
                hu_col[hk][pk].append('Start')
                hu_col[hk][pk].append('Stop')
                # Next two lines for "one column" solution
                if len(hu_col[hk][pk]) >= lc.hlen:
                    lc.part=hk; lc.pol=pk; lc.hlen=len(hu_col[hk][pk])
        if len(hu_col[lc.part]) == 0:
            return []
        else:
            return hu_col[lc.part][lc.pol]

    def __hookup_add_correlator_levels(self, hookup_dict, testing):
        warnings.warn("Warning:  correlator levels don't work with new pol hookup scheme yet (CM_HOOKUP[210]).")
        return hookup_dict
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
        if col[-2:] == '_e' or col[-2:] == '_n':
            # Makes these specific pol parts generic
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

        headers, show_flag = self.__make_header_row(hookup_dict['columns'],
                                                    cols_to_show, show_levels)
        table_data = []
        for hukey in sorted(hookup_dict['hookup'].keys()):
            for pol in sorted(hookup_dict['hookup'][hukey].keys()):
                timing = hookup_dict['timing'][hukey][pol]
                if show_levels:
                    level = hookup_dict['levels'][hukey][pol]
                else:
                    level = False
                if len(hookup_dict['hookup'][hukey][pol]) > 0:
                    td = self.__make_table_row(hookup_dict['hookup'][hukey][pol], headers,
                                               show_flag, timing, level)
                    table_data.append(td)
        print('\n')
        print(tabulate(table_data, headers=headers, tablefmt='orgtbl'))
        print('\n')

    def __make_header_row(self, header_col, cols_to_show, show_levels):
        headers = []
        show_flag = []
        for col in header_col:
            colhead = self.__header_entry_name_adjust(col)
            if cols_to_show[0].lower() == 'all' or colhead in cols_to_show:
                show_flag.append(True)
                headers.append(colhead)
            else:
                show_flag.append(False)
        return headers, show_flag

    def __make_table_row(self, hup, headers, show_flag, timing, show_level):
        nc = '-'
        td = []
        if show_flag[0]:
            pn = hup[0]
            prpn = (pn.upstream_part + ':' + pn.up_part_rev + ' <' +
                    pn.upstream_output_port)
            td.append(prpn)
        for i in range(1, len(hup)):
            if show_flag[i]:
                pn = hup[i - 1]
                prpn = (pn.downstream_input_port + '> ' + pn.downstream_part + ':' +
                        pn.down_part_rev)
                pn = hup[i]
                prpn += ' <' + pn.upstream_output_port
                td.append(prpn)
        if show_flag[-1]:
            pn = hup[-1]
            prpn = (pn.downstream_input_port + '> ' + pn.downstream_part + ':' +
                    pn.down_part_rev)
            td.append(prpn)
        td.append(str(timing[0]))
        td.append(str(timing[1]))
        if show_level:
            td.append(show_level)
        if len(td) != len(headers):
            new_hup = []
            nc = '-'
            for hdr in headers:
                if hdr == 'levels':
                    continue
                for hu in hup:
                    get_part_type = self.handling.get_part_dossier(
                        hpn=hu.upstream_part, rev=hu.up_part_rev,
                        at_date=None, exact_match=True)
                    pr_key = cm_utils._make_part_key(hu.upstream_part, hu.up_part_rev)
                    part_col = get_part_type[pr_key]['part'].hptype
                    if self.__header_entry_name_adjust(part_col) == hdr:
                        new_hup.append(hu)
                        break
                else:
                    get_part_type = self.handling.get_part_dossier(
                        hpn=hu.downstream_part, rev=hu.down_part_rev,
                        at_date=None, exact_match=True)
                    pr_key = cm_utils._make_part_key(hu.downstream_part, hu.down_part_rev)
                    part_col = get_part_type[pr_key]['part'].hptype
                    if self.__header_entry_name_adjust(part_col) == hdr:
                        continue
                    else:
                        new_hup.append(PC.Connections(upstream_part=nc,
                                                      up_part_rev=nc,
                                                      upstream_output_port=nc,
                                                      downstream_part=nc,
                                                      down_part_rev=nc,
                                                      downstream_input_port=nc))
            td = self.__make_table_row(new_hup, headers, show_flag, show_level)
        return td
