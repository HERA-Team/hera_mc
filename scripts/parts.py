#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for handling parts and connections

"""
from __future__ import absolute_import, division, print_function

from hera_mc import part_connect, cm_handling, cm_utils, mc
import os.path
import sys

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  info, hookup, types, part_info, conn_info, rev_info, \
                                                   check_rev, overlap_check, update.  'info' for more.", default='hookup')
    # set values for 'action' to use
    parser.add_argument('-p', '--hpn', help="Part number (required). [None]", default=None)
    parser.add_argument('-r', '--revision', help="Specify revision or last/active/full/all for hpn.  [LAST]", default='LAST')
    parser.add_argument('-e', '--exact-match', help="Force exact matches on part numbers, not beginning N char. [False]",
                        dest='exact_match', action='store_true')
    parser.add_argument('--port', help="Define desired port(s) for hookup. [all]", dest='port', default='all')
    parser.add_argument('--show_state', help="Show only the 'full', active' or 'all' parts [active]", default='active')
    parser.add_argument('--hookup-cols', help="Specify a subset of parts to show in mapr, comma-delimited no-space list. [all]",
                        dest='hookup_cols', default='all')
    parser.add_argument('--full-req', help="hookup columns needed to constitute fully connected, comma-delimited no-space list\
                                            [station, f_engine]", dest='full_req', default='station,f_engine')
    parser.add_argument('--update', help="Update part number records.  Format hpn0:[rev0]:col0:val0, \
                                          [hpn1:[rev1]]col1:val1...  [None]", default=None)
    parser.add_argument('--show-levels', help="Show power levels if enabled (and able) [False]", dest='show_levels', action='store_true')
    parser.add_argument('--levels-testing', help="Set to test filename if correlator levels not accessible - keep False \
                                                  to use actual correlator [False]", dest='levels_testing', default=False)
    parser.add_argument('--add-new-part', help="Flag to allow update to add a new record.  [False]", dest='add_new_part', action='store_true')
    cm_utils.add_verbosity_args(parser)
    cm_utils.add_date_time_args(parser)

    args = parser.parse_args()

    date_query = cm_utils._get_astropytime(args.date, args.time)

    if args.action[:2].lower() == 'in':
        print(
            """
        Available actions are (only need first two letters) [hookup]:
            info:  this information
            hookup:  provide hookup information for supplied part/rev/port
            part_info:  provide a summary of given part/rev
            conn_info:  provide a summary of connections to given part/rev/port
            rev_info:  provide a summary of revisions of given part/rev
            types:  provide a summary of part types
            check_rev:  checks whether a given part/rev exists
            overlap_check:  checks whether a given part has any overlapping active revisions
            update:  update a part (not recommended - do it via a script)

        Args needing values (or defaulted):
            -p/--hpn:  part name (required)
            -r/--revision:  revision (particular/last/active/full/all) [LAST]
            --port:  port name (particular/all) [ALL]
            --show_state:  show 'full', 'active' or 'all' parts [ACTIVE]
            --hookup-cols:  comma-delimited list of columns to include in hookup (no spaces) [ALL]
            --full-req:  comma-delimited list of columns to require for fully connections [station,f_engine]
            --levels-testing:  filename for test correlator information, prepend with ':' for test directory [False]
                               Note that ':levels.tst' should work.
            --update:  date for update (not recommended - do it via a script)

        Args that are flags
            -e/--exact-match:  match part number exactly, or specify first characters [False]
            --show-levels:  include correlator levels in hookup output [False]
            --add-new-part:  flag to allow including a new part for update
        """
        )
        sys.exit()

    # Pre-process the args
    if args.hpn is None:
        print("Must specify a part name (-p/--hpn)")
        sys.exit()

    if ',' in args.hookup_cols:
        args.hookup_cols = args.hookup_cols.split(',')
    else:
        args.hookup_cols = [args.hookup_cols]

    if ',' in args.full_req:
        args.full_req = args.full_req.split(',')
    else:
        args.full_req = [args.full_req]

    if args.levels_testing is not False and args.levels_testing[0] == ':':
        args.levels_testing = os.path.join(mc.test_data_path, args.levels_testing[1:])

    # Start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    handling = cm_handling.Handling(session)

    # Process
    if args.action[:2].lower() == 'pa':  # part_info
        part_dossier = handling.get_part_dossier(hpn=args.hpn, rev=args.revision,
                                                 at_date=date_query, exact_match=args.exact_match)
        handling.show_parts(part_dossier, verbosity=args.verbosity)

    elif args.action[:2].lower() == 'co':  # connection_info
        connection_dossier = handling.get_connection_dossier(
            hpn=args.hpn, rev=args.revision, port=args.port,
            at_date=date_query, exact_match=args.exact_match)
        already_shown = handling.show_connections(connection_dossier, verbosity=args.verbosity)
        handling.show_other_connections(connection_dossier, already_shown)

    elif args.action[:2].lower() == 'ho':  # hookup
        from hera_mc import cm_hookup
        hookup = cm_hookup.Hookup(session)
        hookup_dict = hookup.get_hookup(hpn=args.hpn, rev=args.revision, port=args.port,
                                        at_date=date_query, exact_match=args.exact_match,
                                        show_levels=args.show_levels, levels_testing=args.levels_testing)
        hookup.show_hookup(hookup_dict, args.hookup_cols, args.show_levels)

    elif args.action[:2].lower() == 'ty':  # types of parts
        part_type_dict = handling.get_part_types(date_query, show_hptype=True)

    elif args.action[:2].lower() == 're':  # revisions
        rev_ret = cm_handling.cmpr.get_revisions_of_type(args.hpn, args.revision, date_query,
                                                         args.full_req, session)
        cm_handling.cmpr.show_revisions(rev_ret)

    elif args.action[:2].lower() == 'ch':  # check revisions
        r = cm_handling.cmpr.check_rev(args.hpn, args.revision, args.check_rev, date_query,
                                       args.full_req, session)
        rrr = '' if r else ' not'
        print("{} rev {} is{} {}".format(args.hpn, args.revision, rrr, args.check_rev))

    elif args.action[:2].lower() == 'ov':  # overlapping revisions
        cm_handling.cmpr.check_part_for_overlapping_revisions(args.hpn, session)

    elif args.action[:2].lower() == 'up':  # update
        you_are_sure = cm_utils._query_yn("Warning:  Update is best done via a script \
                                            -- are you sure you want to do this? ", 'n')
        if you_are_sure:
            part_connect.update(session, args.update, args.add_new_part)
