#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for handling parts and connections

"""
from __future__ import absolute_import, division, print_function

from hera_mc import part_connect, cm_handling, cm_utils, mc
import os.path
import sys

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  info, types, part_info, conn_info, rev_info, \
                                                   check_rev, overlap_check.  'info' for more.", default='part_info')
    # set values for 'action' to use
    parser.add_argument('-p', '--hpn', help="Part number, csv-list (required). [None]", default=None)
    parser.add_argument('-r', '--revision', help="Specify revision or last/active/full/all for hpn.  [ACTIVE]", default='ACTIVE')
    parser.add_argument('-e', '--exact-match', help="Force exact matches on part numbers, not beginning N char. [False]",
                        dest='exact_match', action='store_true')
    parser.add_argument('--check-rev', help="Revision type to check against. [FULL]", dest='check_rev', default='FULL')
    parser.add_argument('--show-state', help="Show only the 'active' or 'all' parts [active]", dest='show_state', default='active')
    cm_utils.add_date_time_args(parser)

    args = parser.parse_args()

    date_query = cm_utils.get_astropytime(args.date, args.time)

    if args.action[:2].lower() == 'in':
        print(
            """
        Available actions are (only need first two letters) [hookup]:
            info:  this information
            part_info:  provide a summary of given part/rev
            conn_info:  provide a summary of connections to given part/rev/port
            rev_info:  provide a summary of revisions of given part/rev
            types:  provide a summary of part types
            check_rev:  checks whether a given part/rev exists
            overlap_check:  checks whether a given part has any overlapping active revisions

        Args needing values (or defaulted):
            -p/--hpn:  part name (required)
            -r/--revision:  revision (particular/last/active/full/all) [ACTIVE]
            --show-state:  show 'active' or 'all' parts [ACTIVE]

        Args that are flags
            -e/--exact-match:  match part number exactly, or specify first characters [False]
        """
        )
        sys.exit()

    # Pre-process the args
    action_tag = args.action[:2].lower()
    args.hpn = cm_utils.listify(args.hpn)

    # Start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    handling = cm_handling.Handling(session)

    # Process
    if action_tag == 'pa':  # part_info
        if args.hpn is not None:
            part_dossier = handling.get_part_dossier(hpn_list=args.hpn, rev=args.revision,
                                                     at_date=date_query, exact_match=args.exact_match)
            handling.show_parts(part_dossier, verbosity=args.verbosity)
        else:
            print("Need to supply part(s)")

    elif action_tag == 'co':  # connection_info
        if args.hpn is not None:
            connection_dossier = handling.get_connection_dossier(
                hpn_list=args.hpn, rev=args.revision, port=args.port,
                at_date=date_query, exact_match=args.exact_match)
            already_shown = handling.show_connections(connection_dossier, verbosity=args.verbosity)
            handling.show_other_connections(connection_dossier, already_shown)
        else:
            print("Need to supply part(s)")

    elif action_tag == 'ty':  # types of parts
        part_type_dict = handling.get_part_types(date_query)
        handling.show_part_types()

    elif action_tag == 're':  # revisions
        if args.hpn is not None:
            for hpn in args.hpn:
                rev_ret = cm_handling.cmpr.get_revisions_of_type(hpn, args.revision, date_query, session)
                cm_handling.cmpr.show_revisions(rev_ret)
        else:
            print("Need to supply parts(s)")

    elif action_tag == 'ch':  # check revisions
        if args.hpn is not None:
            for hpn in args.hpn:
                r = cm_handling.cmpr.check_rev(hpn, args.revision, args.check_rev, date_query, session)
                rrr = '' if r else ' not'
                print("{} rev {} is{} {}".format(hpn, args.revision, rrr, args.check_rev))
        else:
            print("Need to supply part(s)")

    elif action_tag == 'ov':  # overlapping revisions
        if args.hpn is not None:
            for hpn in args.hpn:
                cm_handling.cmpr.check_part_for_overlapping_revisions(hpn, session)
        else:
            print("Need to supply part(s)")
