#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for hookup

"""
from __future__ import absolute_import, division, print_function

import os.path

from hera_mc import cm_hookup, cm_utils, mc

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-p', '--hpn', help="Part number, csv-list or default. (default)", default='default')
    parser.add_argument('-r', '--revision', help="Specify revision or last/active/full/all for hpn.  (LAST)", default='LAST')
    parser.add_argument('-e', '--exact-match', help="Force exact matches on part numbers, not beginning N char.",
                        dest='exact_match', action='store_true')
    parser.add_argument('-f', '--force-new-cache', dest='force_new_cache', help="Force it to write a new hookup cache file.", action='store_true')
    parser.add_argument('-c', '--cache-info', help="Shows information about the hookup cache file.", dest='cache_info', action='store_true')
    parser.add_argument('--force-db', dest='force_db', help="Force db use (but doesn't rewrite cache)", action='store_true')
    parser.add_argument('--hookup-type', dest='hookup_type', help="Force use of specified hookup type.", default=None)
    parser.add_argument('--port', help="Define desired port(s) for hookup. (e, n, all)", dest='port', default='all')
    parser.add_argument('--state', help="Show 'full' or 'all' hookups (full)", default='full')
    parser.add_argument('--hookup-cols', help="Specify a subset of parts to show in hookup, comma-delimited no-space list. (all])",
                        dest='hookup_cols', default='all')
    parser.add_argument('--levels', help="Show power levels if enabled (and able)", action='store_true')
    parser.add_argument('--hide-ports', dest='ports', help="Hide ports on hookup.", action='store_false')
    parser.add_argument('--revs', help="Show revs on hookup.", action='store_true')
    parser.add_argument('--delete-cache-file', dest='delete_cache_file', help="Deletes the local cache file", action='store_true')
    cm_utils.add_date_time_args(parser)

    args = parser.parse_args()

    date_query = cm_utils.get_astropytime(args.date, args.time)

    # Pre-process the args
    args.hookup_cols = cm_utils.listify(args.hookup_cols)
    if args.hpn == 'default':
        args.hpn = cm_utils.default_station_prefixes
    else:
        args.hpn = cm_utils.listify(args.hpn)
    # Start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    hookup = cm_hookup.Hookup(date_query, session)
    if args.cache_info:
        print(hookup.hookup_cache_file_info())
    elif args.delete_cache_file:
        hookup.delete_cache_file()
    else:
        if args.force_db:
            force_db_at_date = date_query
        else:
            force_db_at_date = None
        hookup_dict = hookup.get_hookup(hpn_list=args.hpn, rev=args.revision, port_query=args.port,
                                        exact_match=args.exact_match, levels=args.levels,
                                        force_new_cache=args.force_new_cache, force_db_at_date=force_db_at_date,
                                        hookup_type=args.hookup_type)
        hookup.show_hookup(hookup_dict=hookup_dict, cols_to_show=args.hookup_cols, levels=args.levels,
                           ports=args.ports, revs=args.revs, state=args.state)
