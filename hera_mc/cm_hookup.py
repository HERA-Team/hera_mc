#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This finds and displays part hookups.

"""
from __future__ import absolute_import, division, print_function

from tabulate import tabulate
import sys
import numpy as np
import os
import six
import copy
from argparse import Namespace
from sqlalchemy import func
from astropy.time import Time, TimeDelta

from . import mc, cm_utils, cm_handling, cm_transfer, cm_sysdef
from . import part_connect as PC


class HookupDossierEntry:
    def __init__(self, entry_key, sysdef):
        """
        This is the structure of the hookup entry.  All are keyed on polarization
        """
        self.entry_key = entry_key
        self.hookup = {}  # actual hookup connection information
        self.fully_connected = {}  # flag if fully connected
        self.hookup_type = {}  # name of hookup_type
        self.columns = {}  # list with the actual column headers in hookup
        self.timing = {}  # aggregate hookup start and stop
        self.sysdef = sysdef

    def __repr__(self):
        s = "<{}:  {}>\n".format(self.entry_key, self.hookup_type)
        s += "{}\n".format(self.hookup)
        s += "{}\n".format(self.fully_connected)
        s += "{}\n".format(self.timing)
        return s

    def get_hookup_type_and_column_headers(self, pol, part_types_found):
        """
        The columns in the hookup contain parts in the hookup chain and the column headers are
        the part types contained in that column.  This returns the headers for the retrieved hookup.

        It just checks which hookup_type the parts are in and keeps however many
        parts are used.

        Parameters:
        -------------
        part_types_found:  list of the part types that were found
        """
        self.hookup_type[pol] = None
        self.columns[pol] = []
        if len(part_types_found) == 0:
            return
        is_this_one = False
        for sp in self.sysdef.checking_order:
            for part_type in part_types_found:
                if part_type not in self.sysdef.full_connection_path[sp]:
                    break
            else:
                is_this_one = sp
                break
        if not is_this_one:
            print('Parts did not conform to any hookup_type')
            return
        else:
            self.hookup_type[pol] = is_this_one
            for c in self.sysdef.full_connection_path[is_this_one]:
                if c in part_types_found:
                    self.columns[pol].append(c)

    def add_timing_and_fully_connected(self, pol):
        if self.hookup_type[pol] is not None:
            full_hookup_length = len(self.sysdef.full_connection_path[self.hookup_type[pol]]) - 1
        else:
            full_hookup_length = -1
        latest_start = 0
        earliest_stop = None
        for c in self.hookup[pol]:
            if c.start_gpstime > latest_start:
                latest_start = c.start_gpstime
            if c.stop_gpstime is None:
                pass
            elif earliest_stop is None:
                earliest_stop = c.stop_gpstime
            elif c.stop_gpstime < earliest_stop:
                earliest_stop = c.stop_gpstime
        self.timing[pol] = [latest_start, earliest_stop]
        self.fully_connected[pol] = len(self.hookup[pol]) == full_hookup_length
        self.columns[pol].append('start')
        self.columns[pol].append('stop')

    def get_part_in_hookup_from_type(self, part_type, include_revs=False, include_ports=False):
        """
        Retrieve the part name for a given part_type from a hookup

        Parameters:
        ------------
        part_type:  string of valid part type in hookup_dict (e.g. 'snap' or 'feed')
        include_revs:  is set to True, returns revision number
        include_ports:  if set to True, it returns the associated ports to the part

        returns:
            parts:  dictionary keyed on polarization for actual installed part number of
                    specified type within hookup as a string per pol
                    if include_revs part number is e.g. FDV1:A
                    if include_ports they are included as e.g. 'input>FDV:A<terminals'
        """
        parts = {}
        extra_cols = ['start', 'stop']
        for pol, names in six.iteritems(self.columns):
            if part_type not in names:
                parts[pol] = None
                continue
            iend = 1
            for ec in extra_cols:
                if ec in self.columns[pol]:
                    iend += 1
            part_ind = names.index(part_type)
            is_first_one = (part_ind == 0)
            is_last_one = (part_ind == len(names) - iend)
            # Get part number
            if is_last_one:
                part_number = self.hookup[pol][part_ind - 1].downstream_part
            else:
                part_number = self.hookup[pol][part_ind].upstream_part
            # Get rev
            rev = ''
            if include_revs:
                if is_last_one:
                    rev = ':' + self.hookup[pol][part_ind - 1].down_part_rev
                else:
                    rev = ':' + self.hookup[pol][part_ind].up_part_rev
            # Get ports
            in_port = ''
            out_port = ''
            if include_ports:
                if is_first_one:
                    out_port = '<' + self.hookup[pol][part_ind].upstream_output_port
                elif is_last_one:
                    in_port = self.hookup[pol][part_ind - 1].downstream_input_port + '>'
                else:
                    out_port = '<' + self.hookup[pol][part_ind].upstream_output_port
                    in_port = self.hookup[pol][part_ind - 1].downstream_input_port + '>'
            # Finish
            parts[pol] = "{}{}{}{}".format(in_port, part_number, rev, out_port)
        return parts

    def table_entry_row(self, pol, headers, part_types, show):
        timing = self.timing[pol]
        td = ['-'] * len(headers)
        # Get the first N-1 parts
        dip = ''
        for d in self.hookup[pol]:
            part_type = part_types[d.upstream_part]
            if part_type in headers:
                new_row_entry = build_new_row_entry(
                    dip, d.upstream_part, d.up_part_rev, d.upstream_output_port, show)
                td[headers.index(part_type)] = new_row_entry
            dip = d.downstream_input_port + '> '
        # Get the last part in the hookup
        part_type = part_types[d.downstream_part]
        if part_type in headers:
            new_row_entry = build_new_row_entry(
                dip, d.downstream_part, d.down_part_rev, None, show)
            td[headers.index(part_type)] = new_row_entry
        # Add timing
        if 'start' in headers:
            td[headers.index('start')] = timing[0]
        if 'stop' in headers:
            td[headers.index('stop')] = timing[1]
        return td


def build_new_row_entry(dip, part, rev, port, show):
    new_row_entry = ''
    if show['ports']:
        new_row_entry = dip
    new_row_entry += part
    if show['revs']:
        new_row_entry += ':' + rev
    if port is not None and show['ports']:
        new_row_entry += ' <' + port
    return new_row_entry


class Hookup:
    """
    Class to find and display the signal path hookup, with a few utility functions.
    To speed things up, it uses a cache file, but only if the query is for prefixes in
    hookup_list_to_cache and if the cache file is current relative to the cm_version
    """
    hookup_list_to_cache = cm_utils.all_hera_zone_prefixes
    if six.PY2:
        hookup_cache_file = os.path.expanduser('~/.hera_mc/hookup_cache_2.npy')
    else:
        hookup_cache_file = os.path.expanduser('~/.hera_mc/hookup_cache_3.npy')

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
        self.handling = cm_handling.Handling(session)
        self.part_type_cache = {}
        self.cached_hookup_dict = None
        self.sysdef = cm_sysdef.Sysdef()

    def reset_memory_cache(self, hookup=None):
        """
        Resets the class cache dictionary to the supplied hookup dict, which can be None.  If None,
        then the next time it will re-read from the file.

        Parameters
        -----------
        hookup:  will set the cached_hookup_dict to this, which is either a hookup dict or None.
        """
        self.cached_hookup_dict = hookup

    def delete_cache_file(self):
        if os.path.exists(self.hookup_cache_file):
            os.remove(self.hookup_cache_file)

    def _hookup_cache_to_use(self, force_new_cache=False):
        """
        Confirms/sets the cached_hookup_dict to use.  If force_new_cache is set, it automatically
        writes/uses a new one.  If the cache file is out of date it writes/uses a new one.  Otherwise
        it uses the existing one (rereading from the cache file if not one in memory.)

        If the cache file is up-to-date and is in memory, this does nothing.

        Parameters
        -----------
        force_new_cache:  force a new cache hookup to be set and written to disc.

        """
        if force_new_cache or not self._hookup_cache_file_OK():
            self.cached_hookup_dict = self.get_hookup_from_db(hpn_list=self.hookup_list_to_cache, rev='ACTIVE',
                                                              port_query='all', at_date=self.at_date,
                                                              exact_match=False, hookup_type=self.hookup_type)
            log_msg = "force_new_cache:  {}".format(force_new_cache)
            self.write_hookup_cache_to_file(log_msg)
        elif self.cached_hookup_dict is None:
            if os.path.exists(self.hookup_cache_file):
                self.read_hookup_cache_from_file()
            else:  # pragma: no cover
                self._hookup_cache_to_use(force_new_cache=True)

    def get_hookup(self, hpn_list, rev='ACTIVE', port_query='all', at_date='now', exact_match=False,
                   force_new_cache=False, force_db=False, hookup_type=None):
        """
        Return the full hookup to the supplied part/rev/port in the form of a dictionary.
        The data may come from one of two sources:
        (1) if the (a) part list is consistent with the keys, (b) date is current, and (c) revision
            hash is current with a local cache file, data from the cache file will be used.
        (2) if those conditions are not met, or the flag 'force_new_cache' is True, or 'force_db'
            is True, it will use the database.

        Parameters
        -----------
        hpn_list:  - list/string of input hera part number(s) (whole or first part thereof)
                   - if string == 'cache' it returns the current dict that would be used
                   - if there are any non-hookup-cached items in list, it reads the database
        rev:  the revision number or descriptor
        port_query:  a port polarization to follow, or 'all',  ('e', 'n', 'all') default is 'all'.
        at_date:  date for query
        exact_match:  boolean for either exact_match or partial
        force_new_cache:  boolean to force a full database read as opposed to the cache file.
                          This will also rewrite the cache file in the process
        force_db:  flag to force the database to be read, not touching the cache file
        hookup_type:  type of hookup to use (current observing system is 'parts_hera').
                      If 'None' it will determine which system it thinks it is based on
                      the part-type.  The order in which it checks is specified in cm_sysdef.
                      Only change if you know you want a different system (like 'parts_paper').
        """
        at_date = cm_utils.get_astropytime(at_date)
        self.at_date = at_date
        self.hookup_type = hookup_type

        # Take appropriate action if hpn_list is a string
        if isinstance(hpn_list, six.string_types):
            if hpn_list.lower().startswith('cache'):
                print("Force read of cache file - not guaranteed fresh.")
                self.read_hookup_cache_from_file()
                return self.cached_hookup_dict
            else:
                hpn_list = cm_utils.listify(hpn_list)

        # Check if force_db either requested or needed
        if force_db or not self._requested_list_OK_for_cache(hpn_list):
            return self.get_hookup_from_db(hpn_list=hpn_list, rev=rev, port_query=port_query, at_date=at_date,
                                           exact_match=exact_match, hookup_type=hookup_type)

        # Check/get the appropriate hookup dict
        # (a) in memory, (b) re-read cache file, or (c) generate new
        self._hookup_cache_to_use(force_new_cache=force_new_cache)

        # Now build up the returned hookup_dict
        hookup_dict = {}
        hpn_list = [x.lower() for x in hpn_list]
        for k in self.cached_hookup_dict:
            hpn, rev = cm_utils.split_part_key(k)
            use_this_one = False
            if exact_match:
                if hpn.lower() in hpn_list:
                    use_this_one = True
            else:
                for p in hpn_list:
                    if hpn[:len(p)].lower() == p:
                        use_this_one = True
                        break
            if use_this_one:
                hookup_dict[k] = copy.copy(self.cached_hookup_dict[k])
        return hookup_dict

    def _requested_list_OK_for_cache(self, hpn_list):
        """
        Checks that all hookup requests match the cached keys.
        """
        for x in hpn_list:
            for key_prefix in self.hookup_list_to_cache:
                if x[:len(key_prefix)].upper() == key_prefix.upper():
                    break
            else:
                return False
        return True

    def get_hookup_from_db(self, hpn_list, rev, port_query, at_date, exact_match=False, hookup_type=None):
        """
        This gets called by the get_hookup wrapper if the database needs to be read (for instance, to generate
        a cache file, or search for parts different than those keyed on in the cache file.)
        """
        # Reset at_date
        at_date = cm_utils.get_astropytime(at_date)
        self.at_date = at_date
        self.hookup_type = hookup_type

        # Get all the appropriate parts
        parts = self.handling.get_part_dossier(hpn=hpn_list, rev=rev,
                                               at_date=self.at_date,
                                               exact_match=exact_match,
                                               full_version=True)
        hookup_dict = {}
        for k, part in six.iteritems(parts):
            if not cm_utils.is_active(self.at_date, part.part.start_date, part.part.stop_date):
                continue
            hookup_type = self.sysdef.find_hookup_type(part_type=part.part_type, hookup_type=hookup_type)
            if part.part_type in self.sysdef.redirect_part_types[hookup_type]:
                redirect_parts = self.sysdef.handle_redirect_part_types(part, at_date=at_date, session=self.session)
                redirect_hookup_dict = self.get_hookup_from_db(hpn_list=redirect_parts, rev=rev, port_query=port_query,
                                                               at_date=self.at_date, exact_match=True, hookup_type=hookup_type)
                for rhdk, vhd in six.iteritems(redirect_hookup_dict):
                    hookup_dict[rhdk] = vhd
                redirect_hookup_dict = None
                continue
            self.sysdef.setup(part=part, port_query=port_query, hookup_type=hookup_type)
            self.hookup_type = self.sysdef.this_hookup_type
            if self.sysdef.pol is None:
                continue
            hookup_dict[k] = HookupDossierEntry(k, self.sysdef)
            for port_pol in self.sysdef.pol:
                hookup_dict[k].hookup[port_pol] = self._follow_hookup_stream(part.hpn, part.rev, port_pol)
                part_types_found = self.get_part_types_found(hookup_dict[k].hookup[port_pol])
                hookup_dict[k].get_hookup_type_and_column_headers(port_pol, part_types_found)
                hookup_dict[k].add_timing_and_fully_connected(port_pol)
        return hookup_dict

    def get_part_types_found(self, hookup_connections):
        if not len(hookup_connections):
            return []
        part_types_found = set()
        for c in hookup_connections:
            part_type = self.handling.get_part_type_for(c.upstream_part).lower()
            part_types_found.add(part_type)
            self.part_type_cache[c.upstream_part] = part_type
        part_type = self.handling.get_part_type_for(c.downstream_part).lower()
        part_types_found.add(part_type)
        self.part_type_cache[c.downstream_part] = part_type
        return list(part_types_found)

    def _follow_hookup_stream(self, part, rev, port_pol):
        self.upstream = []
        self.downstream = []
        port = port_pol  # Seed it
        pol = port_pol[0]
        starting = Namespace(direction='up', part=part, rev=rev, port=port, pol=pol)
        current = copy.copy(starting)
        self._recursive_connect(current)
        starting.direction = 'down'
        self._recursive_connect(starting)

        hu = []
        for pn in reversed(self.upstream):
            hu.append(pn)
        for pn in self.downstream:
            hu.append(pn)
        return hu

    def _recursive_connect(self, current):
        """
        Find the next connection up the signal chain.
        """
        next_conn = self._get_next_connection(current)
        if next_conn is not None:
            if current.direction == 'up':
                self.upstream.append(next_conn)
                current.part = next_conn.upstream_part
                current.rev = next_conn.up_part_rev
                current.port = next_conn.upstream_output_port
            else:
                self.downstream.append(next_conn)
                current.part = next_conn.downstream_part
                current.rev = next_conn.down_part_rev
                current.port = next_conn.downstream_input_port
            self._recursive_connect(current)

    def _get_next_connection(self, current):
        """
        Get next connected part going the given direction.
        """
        # Get all of the port options going the right direction
        tpk = cm_utils.make_part_key(current.part, current.rev)
        this = self.handling.get_part_dossier(hpn=current.part, rev=current.rev, at_date=self.at_date,
                                              exact_match=True, full_version=False)[tpk]
        options = []
        next = []
        if current.direction == 'up':      # Going upstream
            for conn in self.session.query(PC.Connections).filter(
                    (func.upper(PC.Connections.downstream_part) == current.part.upper())
                    & (func.upper(PC.Connections.down_part_rev) == current.rev.upper())):
                conn.gps2Time()
                if not cm_utils.is_active(self.at_date, conn.start_date, conn.stop_date):
                    continue
                options.append(copy.copy(conn))
                npk = cm_utils.make_part_key(conn.upstream_part, conn.up_part_rev)
                next.append(self.handling.get_part_dossier(hpn=conn.upstream_part, rev=conn.up_part_rev, at_date=self.at_date,
                                                           exact_match=True, full_version=False)[npk])
        elif current.direction == 'down':  # Going downstream
            for conn in self.session.query(PC.Connections).filter(
                    (func.upper(PC.Connections.upstream_part) == current.part.upper())
                    & (func.upper(PC.Connections.up_part_rev) == current.rev.upper())):
                conn.gps2Time()
                if not cm_utils.is_active(self.at_date, conn.start_date, conn.stop_date):
                    continue
                options.append(copy.copy(conn))
                npk = cm_utils.make_part_key(conn.downstream_part, conn.down_part_rev)
                next.append(self.handling.get_part_dossier(hpn=conn.downstream_part, rev=conn.down_part_rev, at_date=self.at_date,
                                                           exact_match=True, full_version=False)[npk])
        return self.sysdef.next_connection(options, current, this, next)

    def write_hookup_cache_to_file(self, log_msg):
        with open(self.hookup_cache_file, 'wb') as f:
            np.save(f, self.at_date)
            np.save(f, self.hookup_type)
            np.save(f, cm_utils.stringify(self.hookup_list_to_cache))
            np.save(f, self.cached_hookup_dict)
            np.save(f, self.part_type_cache)
        cf_info = self.hookup_cache_file_info()
        log_dict = {'hu-list': cm_utils.stringify(self.hookup_list_to_cache),
                    'log_msg': log_msg, 'cache_file_info': cf_info}
        cm_utils.log('update_cache', log_dict=log_dict)

    def read_hookup_cache_from_file(self):
        if os.path.exists(self.hookup_cache_file):
            with open(self.hookup_cache_file, 'rb') as f:
                self.cached_at_date = Time(np.load(f).item())
                self.cached_hookup_type = np.load(f).item()
                self.cached_hookup_list = cm_utils.listify(np.load(f).item())
                self.cached_hookup_dict = np.load(f).item()
                self.part_type_cache = np.load(f).item()
        else:
            self._hookup_cache_to_use(force_new_cache=True)
            self.read_hookup_cache_from_file()
        self.hookup_type = self.cached_hookup_type

    def _hookup_cache_file_OK(self, contemporaneous_minutes=15.0):
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
        """
        # Get the relevant dates (checking the cache_file/cm_version up front)
        try:
            stats = os.stat(self.hookup_cache_file)
        except OSError as e:  # pragma: no cover
            if e.errno == 2:
                cm_utils.log('__hookup_cache_file_date_OK:  no cache file found.')
                return False  # File does not exist
            print("OS error:  {0}".format(e))
            raise
        result = self.session.query(cm_transfer.CMVersion).order_by(cm_transfer.CMVersion.update_time).all()
        cm_hash_time = Time(result[-1].update_time, format='gps')
        file_mod_time = Time(stats.st_mtime, format='unix')
        # If CMVersion changed since file was written, don't know so fail...
        if file_mod_time < cm_hash_time:  # pragma: no cover
            log_dict = {'file_mod_time': cm_utils.get_time_for_display(file_mod_time),
                        'cm_hash_time': cm_utils.get_time_for_display(cm_hash_time)}
            cm_utils.log('__hookup_cache_file_date_OK:  out of date.', log_dict=log_dict)
            return False
        if os.path.exists(self.hookup_cache_file):
            with open(self.hookup_cache_file, 'rb') as f:
                cached_at_date = Time(np.load(f).item())
                cached_hookup_type = np.load(f).item()
        else:  # pragma: no cover
            return False

        if self.hookup_type is None:
            self.hookup_type = cached_hookup_type
        if self.hookup_type != cached_hookup_type:  # pragma: no cover
            return False

        # If the cached and query dates are after the last hash time it's ok
        if cached_at_date > cm_hash_time and self.at_date > cm_hash_time:
            return True

        # OK if cached_at_date and the at_date are basically the same is OK
        if abs(cached_at_date - self.at_date) < TimeDelta(60.0 * contemporaneous_minutes, format='sec'):
            return True

    def hookup_cache_file_info(self):
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

    def show_hookup(self, hookup_dict, cols_to_show='all', state='full', ports=False, revs=False,
                    file=None, output_format='ascii'):
        """
        Print out the hookup table -- uses tabulate package.

        Parameters
        -----------
        hookup_dict:  generated in self.get_hookup
        cols_to_show:  list of columns to include in hookup listing
        ports:  boolean to include ports or not
        revs:  boolean to include revisions letter or not
        state:  show the full hookups only, or all
        file:  file to use, None goes to stdout
        output_format:  set to html for the web-page version, or ascii

        """
        show = {'ports': ports, 'revs': revs}
        headers = self.make_header_row(hookup_dict, cols_to_show)
        table_data = []
        numerical_keys = cm_utils.put_keys_in_numerical_order(sorted(hookup_dict.keys()))
        total_shown = 0
        for hukey in numerical_keys:
            for pol in sorted(hookup_dict[hukey].hookup.keys()):
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
        if file is None:
            import sys
            file = sys.stdout
        if output_format == 'html':
            dtime = cm_utils.get_time_for_display('now') + '\n'
            table = cm_utils.html_table(headers, table_data)
            table = '<html>\n\t<body>\n\t\t<pre>\n' + dtime + table + dtime + '\t\t</pre>\n\t</body>\n</html>\n'
        else:
            table = tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n'
        print(table, file=file)

    def make_header_row(self, hookup_dict, cols_to_show):
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
