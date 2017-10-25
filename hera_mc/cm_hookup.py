#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This is computes and displays part hookups.

"""
from __future__ import absolute_import, division, print_function
from tabulate import tabulate
import sys
import numpy as np
import os.path

from hera_mc import mc, geo_location, correlator_levels, cm_utils, cm_handling
from hera_mc import part_connect as PC
import copy
from sqlalchemy import func


class Hookup:
    """
    Class to find and display the signal path hookup.
    """

    def __init__(self, session=None, hookup_list_to_cache=['HH']):
        """
        Hookup traces parts and connections through the signal path (as defined
            by the connections).
        """

        if session is None:
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.handling = cm_handling.Handling(session)
        self.part_type_cache = {}
        self.hookup_local_file = os.path.expanduser('~/.hera_mc_hookup_cache.npy')
        self.hookup_list_to_cache = hookup_list_to_cache

    def get_hookup(self, hpn_list, rev, port_query='all', at_date='now',
                   exact_match=False, show_levels=False,
                   force_new=True, force_specific=False):
        """
        Return the full hookup to the supplied part/rev/port in the form of a dictionary.
        Unless force_new is True, it will check a local hookup file and return that if current
        otherwise it will go through the full database to get hookup.
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
        port_query:  a specifiable port name to follow or 'all',  default is 'all'.
        at_date:  date for hookup validity
        exact_match:  boolean for either exact_match or partial
        show_levels:  boolean to include correlator levels
        force_new:  boolean to force a full database read as opposed to checking file
        force_specific:  boolean to force this to read/write the file to use the supplied values
                         Setting this makes get_hookup provide specific hookups (mimicking the
                         action before the file option was instituted)
        """
        if force_specific:
            return self.__get_hookup(hpn_list=hpn_list, rev=rev, port_query=port_query,
                                     at_date=at_date, exact_match=exact_match, show_levels=show_levels)

        if force_new or not self.check_if_hookup_file_is_current():
            hookup_dict = self.__get_hookup(hpn_list=self.hookup_list_to_cache, rev='ACTIVE', port_query='all',
                                            at_date=at_date, exact_match=exact_match, show_levels=show_levels)
            self.write_hookup_to_file(hookup_dict)
        else:
            hookup_dict = self.read_hookup_from_file()
            if show_levels:
                hookup_dict = self.__hookup_add_correlator_levels(hookup_dict)
        # Now we need to delete the ones we don't use since the file (probably) has all of them.
        hpn_list = [x.lower() for x in hpn_list]
        for k in hookup_dict['hookup'].keys():
            hpn = k.split(':')[0].lower()
            if exact_match:
                if hpn not in hpn_list:
                    del hookup_dict['hookup'][k]
            else:
                del_this_one = True
                for p in hpn_list:
                    if hpn[:len(p)] == p.lower():
                        del_this_one = False
                        break
                if del_this_one:
                    del hookup_dict['hookup'][k]
        return hookup_dict

    def __get_hookup(self, hpn_list, rev, port_query, at_date,
                     exact_match=False, show_levels=False):
        """
        This gets called by the get_hookup wrapper if the database is to be read.
        """

        self.at_date = cm_utils._get_astropytime(at_date)

        # Get all the appropriate parts
        parts = self.handling.get_part_dossier(hpn_list=hpn_list, rev=rev,
                                               at_date=self.at_date,
                                               exact_match=exact_match,
                                               full_version=False)
        hookup_dict = {'hookup': {}, 'fully_connected': {}, 'parts_epoch': {}}
        part_types_found = []
        for k, part in parts.iteritems():
            if not cm_utils._is_active(self.at_date, part['part'].start_date, part['part'].stop_date):
                continue
            hookup_dict['hookup'][k] = {}
            pols_to_do = self.__get_pols_to_do(part, port_query)
            for pol in pols_to_do:
                hookup_dict['hookup'][k][pol] = self.__follow_hookup_stream(part['part'].hpn, part['part'].hpn_rev, pol)
                part_types_found = self.__get_part_types_found(hookup_dict['hookup'][k][pol], part_types_found)
        # Add other information in to the hookup_dict
        hookup_dict['columns'], hookup_dict['parts_epoch'] = self.__get_column_headers(part_types_found)
        if len(hookup_dict['columns']):
            hookup_dict = self.__add_hookup_timing_and_flags(hookup_dict)
            if show_levels:
                hookup_dict = self.__hookup_add_correlator_levels(hookup_dict)
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

    def __get_pols_to_do(self, part, port_query):
        """
        Given the current part and port_query (which is either 'all', 'e', or 'n')
        this figures out which pols to do.  Basically, given 'all' and part it
        figures out whether to return ['e'], ['n'], ['e', 'n']

        Parameter:
        -----------
        part:  current part dossier
        port_query:  the ports that were requested.
        """
        single_pol_parts_paper = ['RI', 'RO', 'CR']
        port_query = port_query.lower()
        if port_query == 'all':  # Need to figure out if return 'e', 'n' or both
            if part['part'].hpn[:2].upper() in single_pol_parts_paper:
                pols = [part['part'].hpn[-1].lower()]
            else:
                pols = PC.both_pols
        elif port_query in PC.both_pols:
            pols = [port_query]
        else:
            raise ValueError('Invalid port_query')
        return pols

    def _check_next_port(self, next_part, option_port, pol, lenopt):
        """
        This checks that the port is the correct one to follow through as you
        follow the hookup.
        """
        if lenopt == 1:
            if next_part[:3].upper() == 'PAM' and option_port[0].lower() != pol.lower():
                return False
            else:
                return True
        if pol.lower() in PC.both_pols:
            if option_port.lower() in ['a', 'b']:
                p = next_part[-1].lower()
            elif option_port[0].lower() in PC.both_pols:
                p = option_port[0].lower()
            else:
                p = pol
            return p == pol
        else:
            raise ValueError("Invalid polarization.")

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
                    options.append(copy.copy(conn))
        elif direction.lower() == 'down':  # Going downstream
            for conn in self.session.query(PC.Connections).filter(
                    (func.upper(PC.Connections.upstream_part) == part.upper()) &
                    (func.upper(PC.Connections.up_part_rev) == rev.upper())):
                conn.gps2Time()
                if cm_utils._is_active(self.at_date, conn.start_date, conn.stop_date):
                    options.append(copy.copy(conn))
        next_one = None
        if len(options) == 0:
            next_one = None
        elif len(options) == 1:
            opc = options[0]
            if direction.lower() == 'up':
                if self._check_next_port(opc.upstream_part, opc.upstream_output_port, pol, len(options)):
                    next_one = opc
            else:
                if self._check_next_port(opc.downstream_part, opc.downstream_input_port, pol, len(options)):
                    next_one = opc
        else:
            for opc in options:
                if direction.lower() == 'up':
                    if self._check_next_port(opc.upstream_part, opc.upstream_output_port, pol, len(options)):
                        next_one = opc
                        break
                else:
                    if self._check_next_port(opc.downstream_part, opc.downstream_input_port, pol, len(options)):
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
        is_this_one = False
        for sp in PC.full_connection_path.keys():
            for part_type in part_types_found:
                if part_type not in PC.full_connection_path[sp]:
                    break
            else:
                is_this_one = sp
                break
        colhead = []
        if not is_this_one:
            print('Parts did not conform to any parts epoch')
            parts_epoch = {'epoch': None, 'path': None}
        else:
            parts_epoch = {'epoch': is_this_one, 'path': PC.full_connection_path[is_this_one]}
            for c in PC.full_connection_path[is_this_one]:
                if c in part_types_found:
                    colhead.append(c)

        return colhead, parts_epoch

    def __hookup_add_correlator_levels(self, hookup_dict):
        import os.path
        dummy_file = os.path.join(mc.test_data_path, 'levels.tst')
        if 'level' not in hookup_dict['columns']:
            hookup_dict['columns'].append('level')
        hookup_dict['levels'] = {}
        pf_input = []
        sorted_hkeys = sorted(hookup_dict['hookup'].keys())
        # *** These nested loops must be in the same order as below ***
        for k in sorted_hkeys:
            for p in sorted(hookup_dict['hookup'][k].keys()):
                if hookup_dict['fully_connected'][k][p]:
                    f_engine = hookup_dict['hookup'][k][p][-1].downstream_part
                else:
                    f_engine = None
                pf_input.append(f_engine)
        levels = correlator_levels.get_levels(pf_input, dummy_file)
        # *** These nested loops must be in the same order as above ***
        level_ctr = 0
        for k in sorted_hkeys:
            hookup_dict['levels'][k] = {}
            for p in sorted(hookup_dict['hookup'][k].keys()):
                hookup_dict['levels'][k][p] = str(levels[level_ctr])
                level_ctr += 1
        return hookup_dict

    def get_correlator_input_from_hookup(self, hookup_dict):
        """
        Retrieve the correlator inputs from a hookup_dictionary.  This currently
        only allows for one entry in hookup_dict, which isn't necessarily what we want.
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

    def get_pam_from_hookup(self, hookup_dict, pam_name='post-amp'):
        """
        Retrieve the PAM connections from a hookup dictionary.

        returns:
            pams[pol] = (location,pam number)
            location example: RI4A1E:A
            pam number example: RCVR93:A (for a PAPER RCVR)
            pam number example: PAM75101:B (for a HERA PAM)
        """
        if len(hookup_dict['hookup'].keys()) > 1:
            raise RuntimeError('Too many hookups provided to give e/n PAM inputs.')
        pams = {}
        pam_ind = hookup_dict['parts_epoch']['path'].index(pam_name)
        if pam_name in hookup_dict['columns']:
            for k, h in hookup_dict['hookup'].iteritems():  # iterates over parts
                for pol, p in h.iteritems():  # iterates over pols
                    pams[pol] = (p[pam_ind - 1].upstream_part, p[pam_ind - 1].downstream_part)
        return pams

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

    def write_hookup_to_file(self, hookup_dict):
        with open(self.hookup_local_file, 'wb') as f:
            np.save(f, hookup_dict)
            np.save(f, self.part_type_cache)

    def check_if_hookup_file_is_current(self):
        import os
        import time
        from astropy.time import Time
        from hera_mc import cm_transfer
        try:
            stats = os.stat(self.hookup_local_file)
        except OSError as e:
            if e.errno == 2:
                return False  # File does not exist
            print("OS error:  {0}".format(e))
            raise
        result = self.session.query(cm_transfer.CMVersion).order_by(cm_transfer.CMVersion.update_time).all()
        cm_hash_time = Time(result[-1].update_time, format='gps')
        file_mod_time = Time(stats.st_mtime, format='unix')
        return file_mod_time > cm_hash_time

    def read_hookup_from_file(self):
        with open(self.hookup_local_file, 'rb') as f:
            hookup_dict = np.load(f).item()
            self.part_type_cache = np.load(f).item()
        return hookup_dict

    def show_hookup(self, hookup_dict, cols_to_show='all', show_levels=False, show_ports=True, show_revs=True,
                    show_state='full', file=None, output_format='ascii'):
        """
        Print out the hookup table -- uses tabulate package.

        Parameters
        -----------
        hookup_dict:  generated in self.get_hookup
        cols_to_show:  list of columns to include in hookup listing
        show_levels:  boolean to either show the correlator levels or not
        show_ports:  boolean to include ports or not
        show_revs:  boolean to include revisions letter or not
        show_state:  show the full hookups only, or all
        file:  file to use, None goes to stdout
        output_format:  set to html for the web-page version
        """
        headers = self.__make_header_row(hookup_dict['columns'], cols_to_show, show_levels)
        table_data = []
        numerical_keys = cm_utils.put_keys_in_numerical_order(sorted(hookup_dict['hookup'].keys()))
        for hukey in numerical_keys:
            for pol in sorted(hookup_dict['hookup'][hukey].keys()):
                use_this_row = False
                if show_state.lower() == 'all' and len(hookup_dict['hookup'][hukey][pol]):
                    use_this_row = True
                elif show_state.lower() == 'full' and hookup_dict['fully_connected'][hukey][pol]:
                    use_this_row = True
                if use_this_row:
                    timing = hookup_dict['timing'][hukey][pol]
                    if show_levels:
                        level = hookup_dict['levels'][hukey][pol]
                    else:
                        level = False
                    td = self.__make_table_row(hookup_dict['hookup'][hukey][pol],
                                               headers, timing, level,
                                               show_ports, show_revs)
                    table_data.append(td)
        table = tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n'
        if file is None:
            import sys
            file = sys.stdout
        if output_format == 'html':
            table = '<html>\n\t<body>\n\t\t<pre>\n' + table + '\t\t</pre>\n\t</body>\n</html>\n'
        print(table, file=file)

    def __make_header_row(self, header_col_list, cols_to_show, show_levels):
        headers = []
        show_flag = []
        for col in header_col_list:
            if show_levels and col == 'level':
                headers.append(col)
            elif cols_to_show[0].lower() == 'all' or col in cols_to_show:
                headers.append(col)
        return headers

    def __make_table_row(self, hup_list, headers, timing, show_level, show_port, show_rev):
        td = ['-'] * len(headers)
        dip = ''
        for d in hup_list:
            part_type = self.part_type_cache[d.upstream_part]
            if part_type in headers:
                new_row_entry = ''
                if show_port:
                    new_row_entry = dip
                new_row_entry += d.upstream_part
                if show_rev:
                    new_row_entry += ':' + d.up_part_rev
                if show_port:
                    new_row_entry += ' <' + d.upstream_output_port
                td[headers.index(part_type)] = new_row_entry
                dip = d.downstream_input_port + '> '
        part_type = self.part_type_cache[d.downstream_part]
        if part_type in headers:
            new_row_entry = ''
            if show_port:
                new_row_entry = dip
            new_row_entry += d.downstream_part
            if show_rev:
                new_row_entry += ':' + d.down_part_rev
            td[headers.index(part_type)] = new_row_entry
        if 'start' in headers:
            td[headers.index('start')] = timing[0]
        if 'stop' in headers:
            td[headers.index('stop')] = timing[1]
        if show_level:
            if 'level' in headers:
                td[headers.index('level')] = show_level
        return td
