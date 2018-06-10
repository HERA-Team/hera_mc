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
import time
from astropy.time import Time, TimeDelta

from hera_mc import mc, geo_location, cm_utils, cm_handling, cm_transfer
from hera_mc import part_connect as PC
import copy
from sqlalchemy import func


def get_part_pols(part, port_query):
    """
    Given the current part and port_query (which is either 'pol' (or 'all'), 'e', or 'n')
    this figures out which pols to do.  Basically, given 'pol' and part it
    figures out whether to return ['e'], ['n'], ['e', 'n']

    Parameter:
    -----------
    part:  current part dossier
    port_query:  the ports that were requested ('e' or 'n' or 'all')
    """

    # These are parts that have their polarization as the last letter of the part name
    # There are none for HERA in the RFoF architecture
    single_pol_EN_parts = ['RI', 'RO', 'CR']
    port_groups = ['all', 'pol']
    port_query = port_query.lower()
    if port_query in port_groups:
        if part.part.hpn[:2].upper() in single_pol_EN_parts:
            return [part.part.hpn[-1].lower()]
        return PC.both_pols

    if port_query in PC.both_pols:
        return [port_query]
    raise ValueError('Invalid port_query')


class HookupDossierEntry:
    def __init__(self, entry_key):
        """
        This is the structure of the hookup entry.  All are keyed on polarization
        """
        self.entry_key = entry_key
        self.hookup = {}  # actual hookup connection information
        self.fully_connected = {}  # flag if fully connected
        self.parts_epoch = {}  # name of parts_epoch
        self.columns = {}  # list with the actual column headers in hookup
        self.timing = {}  # aggregate hookup start and stop
        self.level = {}  # correlator level

    def get_epoch_and_column_headers(self, pol, part_types_found):
        """
        The columns in the hookup contain parts in the hookup chain and the column headers are
        the part types contained in that column.  This returns the headers for the retrieved hookup.

        It just checks which epoch the parts are in (parts_paper or parts_hera) and keeps however many
        parts are used.

        Parameters:
        -------------
        part_types_found:  list of the part types that were found
        """
        self.parts_epoch[pol] = None
        self.columns[pol] = []
        if len(part_types_found) == 0:
            return
        is_this_one = False
        for sp in PC.full_connection_path:
            for part_type in part_types_found:
                if part_type not in PC.full_connection_path[sp]:
                    break
            else:
                is_this_one = sp
                break
        if not is_this_one:
            print('Parts did not conform to any parts epoch')
            return
        else:
            self.parts_epoch[pol] = is_this_one
            for c in PC.full_connection_path[is_this_one]:
                if c in part_types_found:
                    self.columns[pol].append(c)

    def add_timing_and_fully_connected(self, pol):
        if self.parts_epoch[pol] is not None:
            full_hookup_length = len(PC.full_connection_path[self.parts_epoch[pol]]) - 1
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

    def add_correlator_levels(self, pol):
        print("Correlator levels not yet implemented for new correlator.")
        self.columns[pol].append('level')
        self.level[pol] = 'N/A'

    def get_part_info(self, part_name):
        """
        Retrieve the value for a part name from a hookup

        Parameters:
        ------------
        part_name:  string of valid part name in hookup_dict

        returns:
            parts[pol] = part number
            location example: RI4A1E:A
            pam number example: RCVR93:A (for a PAPER RCVR)
            pam number example: PAM75101:B (for a HERA PAM)
        """
        parts = {}
        extra_cols = ['start', 'stop', 'level']
        for pol, names in self.columns.iteritems():
            if part_name not in names:
                parts[pol] = None
                continue
            iend = 2
            for ec in extra_cols:
                if ec in self.columns[pol]:
                    iend += 1
            part_ind = names.index(part_name)
            if part_ind < len(names) - iend:
                parts[pol] = self.hookup[pol][part_ind].upstream_part
            else:
                parts[pol] = self.hookup[pol][part_ind - 1].downstream_part
        return parts

    def table_entry_row(self, pol, headers, part_types, show):
        timing = self.timing[pol]
        if show['levels']:
            level = self.level[pol]
        else:
            level = False
        td = ['-'] * len(headers)
        # Get the first N-1 parts
        dip = ''
        for d in self.hookup[pol]:
            part_type = part_types[d.upstream_part]
            if part_type in headers:
                new_row_entry = ''
                if show['ports']:
                    new_row_entry = dip
                new_row_entry += d.upstream_part
                if show['revs']:
                    new_row_entry += ':' + d.up_part_rev
                if show['ports']:
                    new_row_entry += ' <' + d.upstream_output_port
                td[headers.index(part_type)] = new_row_entry
                dip = d.downstream_input_port + '> '
        # Get the last part in the hookup
        part_type = part_types[d.downstream_part]
        if part_type in headers:
            new_row_entry = ''
            if show['ports']:
                new_row_entry = dip
            new_row_entry += d.downstream_part
            if show['revs']:
                new_row_entry += ':' + d.down_part_rev
            td[headers.index(part_type)] = new_row_entry
        # Add timing and levels
        if 'start' in headers:
            td[headers.index('start')] = timing[0]
        if 'stop' in headers:
            td[headers.index('stop')] = timing[1]
        if level:
            td[headers.index('level')] = level
        return td


class Hookup:
    """
    Class to find and display the signal path hookup, with a few utility functions.
    To speed things up, it uses a cache file, but only if the query is for prefixes in
    hookup_list_to_cache and if the cache file is current relative to the cm_version
    """
    hookup_list_to_cache = cm_utils.all_hera_zone_prefixes
    hookup_cache_file = os.path.expanduser('~/.hera_mc/hookup_cache.npy')

    def __init__(self, at_date='now', session=None):
        """
        Hookup traces parts and connections through the signal path (as defined
            by the connections).
        """
        if session is None:
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.at_date = cm_utils.get_astropytime(at_date)
        self.handling = cm_handling.Handling(session)
        self.part_type_cache = {}
        self.cached_hookup_dict = None

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

    def determine_hookup_cache_to_use(self, force_new=False):
        """
        Determines action regarding using an existing cache file or writing and using a new one.
        If force_new is set, it automatically writes/uses a new one.  If the cache file is out of
        date it writes/uses a new one.  Otherwise it uses the existing one (rereading from the
        cache file if not one in memory.)

        This assumes that if a hookup_dict is read in, it corresponds to the cache_file.

        If the cache file is up-to-date and is in memory, this does nothing.

        Parameters
        -----------
        force_new:  boolean to force a new read as opposed to using cache file,
                    if the existing file is valid.  If the existing cache file is out-of-date
                    relative to the cm_version it will also generate/write a new one.

        """
        cache_file_date_OK = self.hookup_cache_file_date_OK()
        if force_new or not cache_file_date_OK:
            self.cached_hookup_dict = self.get_hookup_from_db(hpn_list=self.hookup_list_to_cache, rev='ACTIVE',
                                                              port_query='all', at_date=self.at_date,
                                                              exact_match=False, levels=False)
            log_msg = "force_new:  {};  cache_file_date_OK:  {}".format(force_new, cache_file_date_OK)
            self.write_hookup_cache_to_file(log_msg)
        elif self.cached_hookup_dict is None:
            if os.path.exists(self.hookup_cache_file):
                self.read_hookup_cache_from_file()
            else:
                self.determine_hookup_cache_to_use(force_new=True)

    def get_hookup(self, hpn_list, rev='ACTIVE', port_query='all', exact_match=False, levels=False,
                   force_new=False, force_specific=False, force_specific_at_date='now'):
        """
        Return the full hookup to the supplied part/rev/port in the form of a dictionary.
        Unless force_new is True, it will check a local hookup file and return that if current
        otherwise it will go through the full database to get hookup.
        Returns hookup dossier entry, a dictionary with the following entries:
        This only gets the contemporary hookups (unlike parts and connections,
            which get all.)  That is, only hookups valid at_date are returned.
            They are therefore only within one parts_epoch

        Parameters
        -----------
        hpn_list:  list/string of input hera part number(s) (whole or first part thereof)
                   if string == 'cached' it returns the current dict that would be used
                   if there are any non-hookup-cached items in list, it defaults to force_specific
        rev:  the revision number or descriptor
        port_query:  a specifiable port name to follow or 'all',  default is 'all'.
        exact_match:  boolean for either exact_match or partial
        levels:  boolean to include correlator levels
        force_new:  boolean to force a full database read as opposed to checking file
                    this will also rewrite the cache-file
        force_specific:  boolean to force this to read/write the file to use the supplied values
                         Setting this makes get_hookup provide specific hookups (mimicking the
                         action before the cache file option was instituted)
        force_specific_at_date:  date for hookup check -- use only if force_specific
        """
        # Take appropriate action if hpn_list is a string
        if isinstance(hpn_list, (str, unicode)):
            if hpn_list.lower() == 'cached':
                print("Force read of cache file - not guaranteed fresh.")
                self.read_hookup_cache_from_file()
                return self.cached_hookup_dict
            else:
                hpn_list = cm_utils.listify(hpn_list)

        # Check if force_specific return either requested or needed
        requested_list_OK_for_cache = self.double_check_request_for_cache_keys(hpn_list)
        if not requested_list_OK_for_cache:
            s = "Hookup request list does not match cache file - using database."
            d = {'hpn_list (request)': hpn_list, 'hookup_list_to_cache': self.hookup_list_to_cache}
            cm_utils.log(s, params=d)
        if force_specific or not requested_list_OK_for_cache:
            return self.get_hookup_from_db(hpn_list=hpn_list, rev=rev, port_query=port_query,
                                           at_date=force_specific_at_date,
                                           exact_match=exact_match, levels=levels)

        # Check/get the appropriate hookup dict
        # (a) in memory, (b) re-read cache file, or (c) generate new
        self.determine_hookup_cache_to_use(force_new=force_new)

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
            if levels:
                for pol in hookup_dict[k].hookup:
                    hookup_dict[k].add_correlator_levels(pol)
        return hookup_dict

    def double_check_request_for_cache_keys(self, hpn_list):
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

    def get_hookup_from_db(self, hpn_list, rev, port_query, at_date, exact_match=False, levels=False):
        """
        This gets called by the get_hookup wrapper if the database is to be read.
        It is the full original method that was used prior to the cache file wrapper stuff.
        """
        # Get all the appropriate parts
        parts = self.handling.get_part_dossier(hpn_list=hpn_list, rev=rev,
                                               at_date=at_date,
                                               exact_match=exact_match,
                                               full_version=False)
        hookup_dict = {}
        for k, part in parts.iteritems():
            if not cm_utils.is_active(self.at_date, part.part.start_date, part.part.stop_date):
                continue
            if k in hookup_dict:
                print("{} already found -- seem to have a duplicate active part.".format(k))
                continue
            hookup_dict[k] = HookupDossierEntry(k)
            pols_to_do = get_part_pols(part, port_query)
            for pol in pols_to_do:
                hookup_dict[k].hookup[pol] = self._follow_hookup_stream(part.part.hpn, part.part.hpn_rev, pol)
                part_types_found = self.get_part_types_found(hookup_dict[k].hookup[pol])
                hookup_dict[k].get_epoch_and_column_headers(pol, part_types_found)
                hookup_dict[k].add_timing_and_fully_connected(pol)
                if levels:
                    hookup_dict[k].add_correlator_levels(pol)
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

    def _follow_hookup_stream(self, part, rev, pol):
        self.upstream = []
        self.downstream = []
        port = pol  # Seed it
        self._recursive_go('up', part, rev, port, pol)
        self._recursive_go('down', part, rev, port, pol)

        hu = []
        for pn in reversed(self.upstream):
            hu.append(pn)
        for pn in self.downstream:
            hu.append(pn)
        return hu

    def _recursive_go(self, direction, part, rev, port, pol):
        """
        Find the next connection up the signal chain.
        """
        conn = self._get_next_connection(direction, part, rev, port, pol)
        if conn:
            if direction == 'up':
                self.upstream.append(conn[0])
                part = conn[0].upstream_part
                rev = conn[0].up_part_rev
                port = conn[0].upstream_output_port
            else:
                self.downstream.append(conn[0])
                part = conn[0].downstream_part
                rev = conn[0].down_part_rev
                port = conn[0].downstream_input_port
            self._recursive_go(direction, part, rev, port, pol)

    def _get_next_connection(self, direction, part, rev, port, pol):
        """
        Get next connected part going the given direction.
        """
        # Get all of the port options going the right direction
        options = []
        if direction == 'up':      # Going upstream
            for conn in self.session.query(PC.Connections).filter(
                    (func.upper(PC.Connections.downstream_part) == part.upper()) &
                    (func.upper(PC.Connections.down_part_rev) == rev.upper())):
                conn.gps2Time()
                if cm_utils.is_active(self.at_date, conn.start_date, conn.stop_date):
                    options.append(copy.copy(conn))
        elif direction == 'down':  # Going downstream
            for conn in self.session.query(PC.Connections).filter(
                    (func.upper(PC.Connections.upstream_part) == part.upper()) &
                    (func.upper(PC.Connections.up_part_rev) == rev.upper())):
                conn.gps2Time()
                if cm_utils.is_active(self.at_date, conn.start_date, conn.stop_date):
                    options.append(copy.copy(conn))
        # Now find the correct ones
        next_one = []
        portside = {'up': 'out', 'down': 'in'}
        otherside = {'up': 'down', 'down': 'up'}
        for opc in options:
            this_part = getattr(opc, '{}stream_part'.format(otherside[direction]))
            this_port = getattr(opc, '{}stream_{}put_port'.format(otherside[direction], portside[otherside[direction]]))
            next_part = getattr(opc, '{}stream_part'.format(direction))
            check_port = getattr(opc, '{}stream_{}put_port'.format(direction, portside[direction]))
            if self._check_next_port(this_part, this_port, next_part, check_port, pol, len(options)):
                next_one.append(opc)
        return next_one

    def _check_next_port(self, this_part, this_port, next_part, option_port, pol, lenopt):
        """
        This checks that the port is the correct one to follow through as you
        follow the hookup.
        """
        if option_port[0] == '@':
            return False

        if lenopt == 1:  # Assume the only option is correct
            return True

        if option_port.lower() in ['a', 'b']:
            p = next_part[-1].lower()
        elif option_port[0].lower() in PC.both_pols:
            p = option_port[0].lower()
        else:
            p = pol

        return p == pol

    def write_hookup_cache_to_file(self, log_msg):
        with open(self.hookup_cache_file, 'wb') as f:
            np.save(f, self.at_date)
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
                self.cached_hookup_list = cm_utils.listify(np.load(f).item())
                self.cached_hookup_dict = np.load(f).item()
                self.part_type_cache = np.load(f).item()
        else:
            self.determine_hookup_cache_to_use(force_new=True)
            self.read_hookup_cache_from_file()

    def hookup_cache_file_date_OK(self, contemporaneous_minutes=15.0):
        """
        This determines if the cache file is up-to-date relative to the cm database.
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
        except OSError as e:
            if e.errno == 2:
                cm_utils.log('__hookup_cache_file_date_OK:  no cache file found.')
                return False  # File does not exist
            print("OS error:  {0}".format(e))
            raise
        result = self.session.query(cm_transfer.CMVersion).order_by(cm_transfer.CMVersion.update_time).all()
        cm_hash_time = Time(result[-1].update_time, format='gps')
        file_mod_time = Time(stats.st_mtime, format='unix')
        # If CMVersion changed since file was written, don't know so fail...
        if file_mod_time < cm_hash_time:
            log_dict = {'file_mod_time': cm_utils.get_time_for_display(file_mod_time),
                        'cm_hash_time': cm_utils.get_time_for_display(cm_hash_time)}
            cm_utils.log('__hookup_cache_file_date_OK:  out of date.', log_dict=log_dict)
            return False
        if os.path.exists(self.hookup_cache_file):
            with open(self.hookup_cache_file, 'rb') as f:
                cached_at_date = Time(np.load(f).item())
        else:
            return False

        # If the cached and query dates are after the last hash time it's ok
        if cached_at_date > cm_hash_time and self.at_date > cm_hash_time:
            return True

        # OK if cached_at_date and the at_date are basically the same is OK
        if abs(cached_at_date - self.at_date) < TimeDelta(60.0 * contemporaneous_minutes, format='sec'):
            return True

        # Otherwise, not OK
        _A = cached_at_date > cm_hash_time
        _B = self.at_date > cm_hash_time
        _C = abs(cached_at_date - self.at_date) < TimeDelta(60.0 * contemporaneous_minutes, format='sec')
        log_dict = {'cached_at_date': cm_utils.get_time_for_display(cached_at_date),
                    'at_date': cm_utils.get_time_for_display(self.at_date),
                    'cm_hash_time': cm_utils.get_time_for_display(cm_hash_time),
                    '_A': _A, '_B': _B, '_C': _C}
        cm_utils.log('__hookup_cache_file_OK:  timing incorrect.', log_dict=log_dict)
        return False

    def hookup_cache_file_info(self):
        if not os.path.exists(self.hookup_cache_file):
            s = "{} does not exist.\n".format(self.hookup_cache_file)
        else:
            self.read_hookup_cache_from_file()
            s = 'Cache file:  {}\n'.format(self.hookup_cache_file)
            s += 'Cached_at_date:  {}\n'.format(cm_utils.get_time_for_display(self.cached_at_date))
            stats = os.stat(self.hookup_cache_file)
            file_mod_time = Time(stats.st_mtime, format='unix')
            s += 'Cache file_mod_time:  {}\n'.format(cm_utils.get_time_for_display(file_mod_time))
            s += 'Cached hookup list:  {}\n'.format(self.cached_hookup_list)
            s += 'Cached hookup has {} keys.\n'.format(len(self.cached_hookup_dict.keys()))
            hooked_up = 0
            for k, hu in self.cached_hookup_dict.iteritems():
                for pol in hu.fully_connected:
                    if hu.fully_connected[pol]:
                        hooked_up += 1
            s += "Number of ant-pols hooked up is {}\n".format(hooked_up)
        result = self.session.query(cm_transfer.CMVersion).order_by(cm_transfer.CMVersion.update_time).all()
        cm_hash_time = Time(result[-1].update_time, format='gps')
        s += '\nCM Version latest cm_hash_time:  {}\n'.format(cm_utils.get_time_for_display(cm_hash_time))
        return s

    def show_hookup(self, hookup_dict, cols_to_show='all', state='full', levels=False, ports=False, revs=False,
                    file=None, output_format='ascii'):
        """
        Print out the hookup table -- uses tabulate package.

        Parameters
        -----------
        hookup_dict:  generated in self.get_hookup
        cols_to_show:  list of columns to include in hookup listing
        levels:  boolean to either show the correlator levels or not
        ports:  boolean to include ports or not
        revs:  boolean to include revisions letter or not
        state:  show the full hookups only, or all
        file:  file to use, None goes to stdout
        output_format:  set to html for the web-page version, or ascii

        """
        show = {'levels': levels, 'ports': ports, 'revs': revs}
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
        table = tabulate(table_data, headers=headers, tablefmt='orgtbl') + '\n'
        if file is None:
            import sys
            file = sys.stdout
        if output_format == 'html':
            dtime = cm_utils.get_time_for_display('now') + '\n'
            table = '<html>\n\t<body>\n\t\t<pre>\n' + dtime + table + dtime + '\t\t</pre>\n\t</body>\n</html>\n'
        print(table, file=file)

    def make_header_row(self, hookup_dict, cols_to_show):
        col_list = []
        for h in hookup_dict.values():
            for cols in h.columns.values():
                if len(cols) > len(col_list):
                    col_list = copy.copy(cols)
        if cols_to_show[0].lower() == 'all':
            return col_list
        headers = []
        cols_to_show = [x.lower() for x in cols_to_show]
        for col in col_list:
            if col.lower() in cols_to_show:
                headers.append(col)
        return headers
