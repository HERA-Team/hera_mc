#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This finds and displays part hookups.

"""
from __future__ import absolute_import, division, print_function

from tabulate import tabulate
import os
import six
import copy
import json
from argparse import Namespace
from astropy.time import Time

from . import mc, cm_utils, cm_transfer, cm_sysdef, cm_dossier, cm_active


class Hookup(object):
    """
    Class to find and display the signal path hookup, with a few utility functions.
    To speed things up, it uses a cache file, but only if the query is for prefixes in
    hookup_list_to_cache and if the cache file is current relative to the cm_version
    """
    hookup_list_to_cache = cm_utils.all_hera_zone_prefixes
    if six.PY2:
        hookup_cache_file = os.path.expanduser('~/.hera_mc/hookup_cache_2.json')
    else:
        hookup_cache_file = os.path.expanduser('~/.hera_mc/hookup_cache_3.json')

    def __init__(self, session=None):
        """
        Hookup traces parts and connections through the signal path (as defined
        by the connections in cm_sysdef).
        """
        if session is None:  # pragma: no cover
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.part_type_cache = {}
        self.cached_hookup_dict = None
        self.sysdef = cm_sysdef.Sysdef()
        self.active = None

    def delete_cache_file(self):
        """
        Deletes the local cached hookup file.
        """
        if os.path.exists(self.hookup_cache_file):
            os.remove(self.hookup_cache_file)

    def requested_list_OK_for_cache(self, hpn):
        """
        Checks that all hookup requests match the cached keys.

        Parameters
        ----------
        hpn : list
            List of HERA part numbers being checked.

        Returns
        -------
        bool
            True if the part numbers are in the cached keys. Else False
        """
        for x in hpn:
            for key_prefix in self.hookup_list_to_cache:
                if x[:len(key_prefix)].upper() == key_prefix.upper():
                    break
            else:
                return False
        return True

    def _cull_dict(self, hpn, search_dict, exact_match):
        """
        Determines the complete appropriate set of parts to use within search_dict.

        The supplied search_dict has all options, which are culled by the supplied
        hpn and exact_match flag.

        Parameters
        ----------
        hpn : list
            Contains part numbers (or partial part numbers) to include in the hookup list.
        search_dict : dict
            Contains information about all parts possible to search, keyed on the "standard"
            cm_utils.make_part_key
        exact_match : bool
            If False, will only check the first characters in each hpn entry.  E.g. 'HH1'
            would allow 'HH1', 'HH10', 'HH123', etc

        Returns
        -------
        dict
            Contains the found entries within search_dict
        """

        hpn_upper = [x.upper() for x in hpn]
        found_dict = {}
        for key in search_dict.keys():
            hpn, rev = cm_utils.split_part_key(key.upper())
            use_this_one = False
            if exact_match:
                if hpn in hpn_upper:
                    use_this_one = True
            else:
                for hlu in hpn_upper:
                    if hpn.startswith(hlu):
                        use_this_one = True
                        break
            if use_this_one:
                found_dict[key] = copy.copy(search_dict[key])
        return(found_dict)

    def get_hookup_from_db(self, hpn, pol, at_date, exact_match=False, hookup_type=None):
        """
        Searches the connections database for the supplied match parameters and returns a hookup dict.

        This gets called by the get_hookup wrapper if the database needs to be read (for instance, to generate
        a cache file, or search for parts different than those keyed on in the cache file.)  It will look over
        all active revisions.

        Parameters
        -----------
        hpn : str, list
            List/string of input hera part number(s) (whole or first part thereof)
        pol : str
            A port polarization to follow, or 'all',  ('e', 'n', 'all')
        at_date :  str, int
            Date for query.  Anything intelligible to cm_utils.get_astropytime
        exact_match : bool
            Flag for either exact_match or partial
        hookup_type : str or None
            Type of hookup to use (current observing system is 'parts_hera').
            If 'None' it will determine which system it thinks it is based on
            the part-type.  The order in which it checks is specified in cm_sysdef.
            Only change if you know you want a different system (like 'parts_paper').

        Returns
        -------
        dict
            Hookup dossier dictionary.
        """
        # Reset at_date
        at_date = cm_utils.get_astropytime(at_date)
        self.at_date = at_date
        self.active = cm_active.ActiveData(self.session, at_date=at_date)
        self.active.load_parts(at_date=None)
        self.active.load_connections(at_date=None)
        hpn = cm_utils.listify(hpn)
        parts = self._cull_dict(hpn, self.active.parts, exact_match)
        hookup_dict = {}
        for k, part in six.iteritems(parts):
            self.hookup_type = self.sysdef.find_hookup_type(part_type=part.hptype, hookup_type=hookup_type)
            if part.hptype in self.sysdef.redirect_part_types[self.hookup_type]:
                redirect_parts = self.sysdef.handle_redirect_part_types(part, self.active)
                redirect_hookup_dict = self.get_hookup_from_db(hpn=redirect_parts, pol=pol, at_date=self.at_date,
                                                               exact_match=True, hookup_type=self.hookup_type)
                for rhdk, vhd in six.iteritems(redirect_hookup_dict):
                    hookup_dict[rhdk] = vhd
                redirect_hookup_dict = None
                continue
            self.sysdef.setup(part=part, pol=pol, hookup_type=self.hookup_type)
            hookup_dict[k] = cm_dossier.HookupEntry(entry_key=k, sysdef=self.sysdef)
            for port_pol in self.sysdef.ppkeys:
                hookup_dict[k].hookup[port_pol] = self._follow_hookup_stream(part=part.hpn, rev=part.hpn_rev, port_pol=port_pol)
                part_types_found = self.get_part_types_found(hookup_dict[k].hookup[port_pol])
                hookup_dict[k].get_hookup_type_and_column_headers(port_pol, part_types_found)
                hookup_dict[k].add_timing_and_fully_connected(port_pol)
        return hookup_dict

    def get_part_types_found(self, hookup_connections):
        """
        Takes a list of connections and returns the part_types of them.  It also
        populates 'self.part_type_cache'

        Parameters
        ----------
        hookup_connections : list
            List of Connection objects

        Returns
        -------
        list
            List of part_types
        """
        if not len(hookup_connections):
            return []
        part_types_found = set()
        for c in hookup_connections:
            key = cm_utils.make_part_key(c.upstream_part, c.up_part_rev)
            part_type = self.active.parts[key].hptype
            part_types_found.add(part_type)
            self.part_type_cache[c.upstream_part] = part_type
        key = cm_utils.make_part_key(c.downstream_part, c.down_part_rev)
        part_type = self.active.parts[key].hptype
        part_types_found.add(part_type)
        self.part_type_cache[c.downstream_part] = part_type
        return list(part_types_found)

    def _follow_hookup_stream(self, part, rev, port_pol):
        """
        This follows a list of connections upstream and downstream.

        Parameters
        ----------
        part : str
            HERA part number
        rev : str
            HERA part revision
        port_pol : str
            Port polarization to follow.  Should be 'E<port' or 'N<port'.

        Returns
        -------
        list
            List of connections for that hookup.
        """
        key = cm_utils.make_part_key(part, rev)
        part_type = self.active.parts[key].hptype
        pol, port = port_pol.split('<')
        port_list = cm_utils.to_upper(self.sysdef.get_ports(pol, part_type))
        self.upstream = []
        self.downstream = []
        current = Namespace(direction='up', part=part.upper(), rev=rev.upper(), key=key, pol=pol.upper(),
                            hptype=part_type, port=port.upper(), allowed_ports=port_list)
        self._recursive_connect(current)
        current = Namespace(direction='down', part=part.upper(), rev=rev.upper(), key=key, pol=pol.upper(),
                            hptype=part_type, port=port.upper(), allowed_ports=port_list)
        self._recursive_connect(current)
        hu = []
        for pn in reversed(self.upstream):
            hu.append(pn)
        for pn in self.downstream:
            hu.append(pn)
        return hu

    def _recursive_connect(self, current):
        """
        Find the next connection up the signal chain.

        Parameters
        ----------
        current : Namespace object
            Namespace containing current information.
        """
        conn = self._get_connection(current)
        if conn is None:
            return None
        if current.direction == 'up':
            self.upstream.append(conn)
        elif current.direction == 'down':
            self.downstream.append(conn)
        self._recursive_connect(current)

    def _get_connection(self, current):
        """
        Get next connected part going the given direction.

        Parameters
        ----------
        current : Namespace object
            Namespace containing current information.
        """
        odir = self.sysdef.opposite_direction[current.direction]
        try:
            options = list(self.active.connections[odir][current.key].keys())
        except KeyError:
            return None
        this_port = self._get_port(current, options)
        if this_port is None:
            return None
        this_conn = self.active.connections[odir][current.key][this_port]
        if current.direction == 'up':
            current.part = this_conn.upstream_part.upper()
            current.rev = this_conn.up_part_rev.upper()
            current.port = this_conn.upstream_output_port.upper()
        elif current.direction == 'down':
            current.part = this_conn.downstream_part.upper()
            current.rev = this_conn.down_part_rev.upper()
            current.port = this_conn.downstream_input_port.upper()
        current.key = cm_utils.make_part_key(current.part, current.rev)
        options = list(self.active.connections[current.direction][current.key].keys())
        try:
            current.type = self.active.parts[current.key].hptype
        except KeyError:
            return None
        current.allowed_ports = cm_utils.to_upper(self.sysdef.get_ports(current.pol, current.type))
        current.port = self._get_port(current, options)
        return this_conn

    def _get_port(self, current, options):
        if current.port is None:
            return None
        sysdef_options = []
        for p in options:
            if p in current.allowed_ports:
                sysdef_options.append(p)
        if current.hptype in self.sysdef.single_pol_labeled_parts[self.hookup_type]:
            if current.part[-1].upper() == current.pol[0]:
                return sysdef_options[0]
        if len(sysdef_options) == 1:
            return sysdef_options[0]
        for p in sysdef_options:
            if p == current.port:
                return p
        for p in sysdef_options:
            if p[0] == current.pol[0]:
                return p

    def get_hookup(self, hpn, pol='all', at_date='now', exact_match=False,
                   use_cache=False, hookup_type='parts_hera'):
        """
        Return the hookup to the supplied part/pol in the form of a dictionary.

        It will return all active revisions at_date from either the database or
        the cache file if use_cache == True and the part number keys agree.

        Parameters
        -----------
        hpn : str, list
            List/string of input hera part number(s) (whole or first part thereof)
                - if string == 'cache' it returns the entire cache file
        pol : str
            A port polarization to follow, or 'all',  ('e', 'n', 'all') default is 'all'.
        at_date :  str, int
            Date for query.  Anything intelligible to cm_utils.get_astropytime
        exact_match : bool
            Flag for either exact_match or partial
        use_cache : bool
            Flag to force the cache to be read, if present and keys agree
        hookup_type : str or None
            Type of hookup to use (current observing system is 'parts_hera').
            If 'None' it will determine which system it thinks it is based on
            the part-type.  The order in which it checks is specified in cm_sysdef.
            Only change if you know you want a different system (like 'parts_paper').

        Returns
        -------
        dict
            Hookup dictionary.
        """
        at_date = cm_utils.get_astropytime(at_date)
        self.at_date = at_date
        self.hookup_type = hookup_type

        if isinstance(hpn, six.string_types) and hpn.lower() == 'cache':
            self.read_hookup_cache_from_file()
            return self.cached_hookup_dict

        hpn = cm_utils.listify(hpn)
        if use_cache and self.requested_list_OK_for_cache(hpn):
            self.read_hookup_cache_from_file()
            return self._cull_dict(hpn, self.cached_hookup_dict, exact_match)

        return self.get_hookup_from_db(hpn=hpn, pol=pol, at_date=at_date,
                                       exact_match=exact_match, hookup_type=hookup_type)

    def write_hookup_cache_to_file(self, log_msg='Write.'):
        """
        Writes the current hookup to the cache file.

        Parameters
        ----------
        log_msg : str
            String containing any desired messages for the cm log.  This should be a short description
            of wny a new cache file is being written.  E.g. "Found new antenna." or "Cronjob to ensure
            cache file up to date."
        """
        self.hookup_list_to_cache = cm_utils.default_station_prefixes
        self.at_date = cm_utils.get_astropytime('now')
        self.hookup_type = 'parts_hera'
        self.cached_hookup_dict = self.get_hookup_from_db(self.hookup_list_to_cache, pol='all', at_date=self.at_date,
                                                          exact_match=False, hookup_type=self.hookup_type)
        hookup_dict_for_json = copy.deepcopy(self.cached_hookup_dict)
        for key, value in six.iteritems(self.cached_hookup_dict):
            if isinstance(value, cm_dossier.HookupEntry):
                hookup_dict_for_json[key] = value._to_dict()

        save_dict = {'at_date_gps': self.at_date.gps,
                     'hookup_type': self.hookup_type,
                     'hookup_list': self.hookup_list_to_cache,
                     'hookup_dict': hookup_dict_for_json,
                     'part_type_cache': self.part_type_cache}
        with open(self.hookup_cache_file, 'w') as outfile:
            json.dump(save_dict, outfile)

        cf_info = self.hookup_cache_file_info()
        log_dict = {'hu-list': cm_utils.stringify(self.hookup_list_to_cache),
                    'log_msg': log_msg, 'cache_file_info': cf_info}
        cm_utils.log('update_cache', log_dict=log_dict)

    def read_hookup_cache_from_file(self):
        """
        Reads the current cache file into memory.
        """
        with open(self.hookup_cache_file, 'r') as outfile:
            cache_dict = json.load(outfile)
        if self.hookup_cache_file_OK(cache_dict):
            print("<<<Cache IS current with database>>>")
        else:
            print("<<<Cache is NOT current with database>>>")
        self.cached_at_date = Time(cache_dict['at_date_gps'], format='gps')
        self.cached_hookup_type = cache_dict['hookup_type']
        self.cached_hookup_list = cache_dict['hookup_list']
        hookup_dict = {}
        for key, value in six.iteritems(cache_dict['hookup_dict']):
            # this should only contain dicts made from HookupEntry
            # add asserts to make sure
            assert(isinstance(value, dict))
            assert(sorted(value.keys()) == sorted(['entry_key', 'hookup', 'fully_connected',
                                                   'hookup_type', 'columns', 'timing', 'sysdef']))
            hookup_dict[key] = cm_dossier.HookupEntry(input_dict=value)

        self.cached_hookup_dict = hookup_dict
        self.part_type_cache = cache_dict['part_type_cache']
        self.hookup_type = self.cached_hookup_type

    def hookup_cache_file_OK(self, cache_dict=None):
        """
        This determines if the cache file is up-to-date relative to the cm database.
        and if hookup_type is correct
        There are 4 relevant dates:
            cm_hash_time:  last time the database was updated per CMVersion
            file_mod_time:  when the cache file was last changed (ie written)
            at_date:  the date of the get hookup request (self.at_date)
            cached_at_date:  the date in the cache file for which it was written.
        If the cache_file was written before the latest cm_version, it fails because
        anything could have changed within the database.

        Returns
        -------
        bool
            True if the cache file is current.
        """
        # Get the relevant dates (checking the cache_file/cm_version up front)
        if cache_dict is None:
            return False
        stats = os.stat(self.hookup_cache_file)
        result = self.session.query(cm_transfer.CMVersion).order_by(cm_transfer.CMVersion.update_time).all()
        cm_hash_time = Time(result[-1].update_time, format='gps')
        file_mod_time = Time(stats.st_mtime, format='unix')
        # If CMVersion changed since file was written, don't know so fail...
        if file_mod_time < cm_hash_time:  # pragma: no cover
            log_dict = {'file_mod_time': cm_utils.get_time_for_display(file_mod_time),
                        'cm_hash_time': cm_utils.get_time_for_display(cm_hash_time)}
            cm_utils.log('__hookup_cache_file_date_OK:  out of date.', log_dict=log_dict)
            return False
        cached_at_date = Time(cache_dict['at_date_gps'], format='gps')
        cached_hookup_type = cache_dict['hookup_type']

        if self.hookup_type is None:
            self.hookup_type = cached_hookup_type
        if self.hookup_type != cached_hookup_type:  # pragma: no cover
            return False

        # If the cached and query dates are after the last hash time it's ok
        if cached_at_date > cm_hash_time and self.at_date > cm_hash_time:
            return True

        # If not returned above, return False to regenerate
        return False

    def hookup_cache_file_info(self):
        """
        Reads in information about the current cache file.

        Returns
        -------
        str
            String containing the information.
        """
        if not os.path.exists(self.hookup_cache_file):  # pragma: no cover
            s = "{} does not exist.\n".format(self.hookup_cache_file)
        else:
            self.read_hookup_cache_from_file()
            s = 'Cache file:  {}\n'.format(self.hookup_cache_file)
            s += 'Cache hookup type:  {}\n'.format(self.cached_hookup_type)
            s += 'Cached_at_date:  {}\n'.format(cm_utils.get_time_for_display(self.cached_at_date))
            stats = os.stat(self.hookup_cache_file)
            file_mod_time = Time(stats.st_mtime, format='unix')
            s += 'Cache file_mod_time:  {}\n'.format(cm_utils.get_time_for_display(file_mod_time))
            s += 'Cached hookup list:  {}\n'.format(self.cached_hookup_list)
            s += 'Cached hookup has {} keys.\n'.format(len(self.cached_hookup_dict.keys()))
            hooked_up = 0
            for k, hu in six.iteritems(self.cached_hookup_dict):
                for pol in hu.fully_connected:
                    if hu.fully_connected[pol]:
                        hooked_up += 1
            s += "Number of ant-pols hooked up is {}\n".format(hooked_up)
        result = self.session.query(cm_transfer.CMVersion).order_by(cm_transfer.CMVersion.update_time).all()
        cm_hash_time = Time(result[-1].update_time, format='gps')
        s += '\nCM Version latest cm_hash_time:  {}\n'.format(cm_utils.get_time_for_display(cm_hash_time))
        return s

    def get_notes(self, hookup_dict, state='all'):
        """
        Retrieves information for hookup.

        Parameters
        ----------
        hookup_dict : dict
            Hookup dictionary generated in self.get_hookup
        state : str
            String designating whether to show the full hookups only, or all

        Returns
        -------
        dict
            hookup notes
        """
        if self.active is None:
            self.active = cm_active.ActiveData(self.session, at_date=self.at_date)
        self.active.get_info(self.at_date)
        info_keys = list(self.active.info.keys())
        hu_notes = {}
        for hkey in hookup_dict.keys():
            all_hu_hpn = set()
            for pol in hookup_dict[hkey].hookup.keys():
                for hpn in hookup_dict[hkey].hookup[pol]:
                    if state == 'all' or (state == 'full' and hookup_dict[hkey].fully_connected[pol]):
                        all_hu_hpn.add(cm_utils.make_part_key(hpn.upstream_part, hpn.up_part_rev))
                        all_hu_hpn.add(cm_utils.make_part_key(hpn.downstream_part, hpn.down_part_rev))
            hu_notes[hkey] = {}
            for ikey in all_hu_hpn:
                if ikey in info_keys:
                    hu_notes[hkey][ikey] = {}
                    for entry in self.active.info[ikey]:
                        hu_notes[hkey][ikey][entry.posting_gpstime] = entry.comment.replace('\\n', '\n')
        return hu_notes

    def show_notes(self, hookup_dict, state='all'):
        """
        Print out the information for hookup.

        Parameters
        ----------
        hookup_dict : dict
            Hookup dictionary generated in self.get_hookup
        state : str
            String designating whether to show the full hookups only, or all

        Returns
        -------
        str
            Content as a string
        """
        hu_notes = self.get_notes(hookup_dict=hookup_dict, state=state)
        full_info_string = ''
        for hkey in cm_utils.put_keys_in_order(list(hu_notes.keys()), sort_order='NPR'):
            hdr = "---{}---".format(hkey)
            entry_info = ''
            part_hu_hpn = cm_utils.put_keys_in_order(list(hu_notes[hkey].keys()), sort_order='PNR')
            if hkey in part_hu_hpn:  # Do the hkey first
                part_hu_hpn.remove(hkey)
                part_hu_hpn = [hkey] + part_hu_hpn
            for ikey in part_hu_hpn:
                gps_times = sorted(list(hu_notes[hkey][ikey].keys()))
                for gtime in gps_times:
                    atime = cm_utils.get_time_for_display(gtime)
                    entry_info += "\t{} ({})  {}\n".format(ikey, atime, hu_notes[hkey][ikey][gtime])
            if len(entry_info):
                full_info_string += "{}\n{}\n".format(hdr, entry_info)
        return full_info_string

    def show_hookup(self, hookup_dict, cols_to_show='all', state='full', ports=False, revs=False,
                    filename=None, output_format='table'):
        """
        Print out the hookup table -- uses tabulate package.

        Parameters
        ----------
        hookup_dict : dict
            Hookup dictionary generated in self.get_hookup
        cols_to_show : list, str
            list of columns to include in hookup listing
        ports : bool
            Flag to include ports or not
        revs : bool
            Flag to include revisions or not
        state : str
            String designating whether to show the full hookups only, or all
        filename : str or None
            File name to use, None goes to stdout.  The file that gets written is
            in all cases an "ascii" file
        output_format : str
            Set output file type.
                'html' for a web-page version,
                'csv' for a comma-separated value version, or
                'table' for a formatted text table

        Returns
        -------
        str
            Table as a string

        """
        show = {'ports': ports, 'revs': revs}
        headers = self.make_header_row(hookup_dict, cols_to_show)
        table_data = []
        total_shown = 0
        for hukey in cm_utils.put_keys_in_order(hookup_dict.keys(), sort_order='NPR'):
            for pol in cm_utils.put_keys_in_order(hookup_dict[hukey].hookup.keys(), sort_order='PNR'):
                if not len(hookup_dict[hukey].hookup[pol]):
                    continue
                use_this_row = False
                if state.lower() == 'all':
                    use_this_row = True
                elif state.lower() == 'full' and hookup_dict[hukey].fully_connected[pol]:
                    use_this_row = True
                if not use_this_row:
                    continue
                total_shown += 1
                td = hookup_dict[hukey].table_entry_row(pol, headers, self.part_type_cache, show)
                table_data.append(td)
        if total_shown == 0:
            print("None found for {} (show-state is {})".format(cm_utils.get_time_for_display(self.at_date), state))
            return
        if output_format.lower().startswith('htm'):
            dtime = cm_utils.get_time_for_display('now') + '\n'
            table = cm_utils.html_table(headers, table_data)
            table = '<html>\n\t<body>\n\t\t<pre>\n' + dtime + table + dtime + '\t\t</pre>\n\t</body>\n</html>\n'
        elif output_format.lower().startswith('csv'):
            table = cm_utils.csv_table(headers, table_data)
        else:
            table = tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n'
        if filename is not None:
            with open(filename, 'w') as fp:
                print(table, file=fp)
        return table

    def make_header_row(self, hookup_dict, cols_to_show):
        """
        Generates the appropriate header row for the displayed hookup.

        Parameters
        ----------
        hookup_dict : dict
            Hookup dictionary generated in self.get_hookup
        cols_to_show : list, str
            list of columns to include in hookup listing

        Returns
        -------
        list
            List of header titles.
        """
        col_list = []
        for h in hookup_dict.values():
            for cols in h.columns.values():
                if len(cols) > len(col_list):
                    col_list = copy.copy(cols)
        if isinstance(cols_to_show, six.string_types):
            cols_to_show = [cols_to_show]
        if cols_to_show[0].lower() == 'all':
            return col_list
        headers = []
        cols_to_show = [x.lower() for x in cols_to_show]
        for col in col_list:
            if col.lower() in cols_to_show:
                headers.append(col)
        return headers
