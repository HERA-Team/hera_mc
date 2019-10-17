#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for handling parts and connections

"""
from __future__ import absolute_import, division, print_function

import os.path
import sys
import six

from hera_mc import mc, cm_handling, cm_utils

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  parts, connections, notes, revisions", default='parts')
    # set values for 'action' to use
    parser.add_argument('-p', '--hpn', help="Part number or portion thereof, csv-list. [None]", default=None)
    parser.add_argument('-r', '--revision', help="Specify revision or last/active/full/all for hpn.  [active]", default='active')
    parser.add_argument('-e', '--exact-match', help="Force exact matches on part numbers, not beginning N char. [False]",
                        dest='exact_match', action='store_true')
    parser.add_argument('--notes', help="<For action=part_info>:  Displays part notes with posting dates and not other info",
                        action='store_true')
    cm_utils.add_verbosity_args(parser)
    cm_utils.add_date_time_args(parser)
    parser.add_argument('--notes_start_date', help="<For notes> start_date for notes [<]", default='<')
    parser.add_argument('--notes_start_time', help="<For notes> start_time for notes", default=0.0)

    args = parser.parse_args()

    args.verbosity = cm_utils.parse_verbosity(args.verbosity)
    action_tag = args.action[:2].lower()
    args.hpn = cm_utils.listify(args.hpn)
    date_query = cm_utils.get_astropytime(args.date, args.time)
    notes_start_date = cm_utils.get_astropytime(args.notes_start_date, args.notes_start_time)

    # Start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    handling = cm_handling.Handling(session)

    if action_tag == 're':  # revisions
        for hpn in args.hpn:
            rev_ret = cm_handling.cmrev.get_revisions_of_type(hpn, args.revision, date_query, session)
            cm_handling.cmrev.show_revisions(rev_ret)
        sys.exit()

    if action_tag == 'pa':  # part_info
        columns = ['hpn', 'hpn_rev', 'hptype', 'manufacturer_number', 'start_gpstime', 'stop_gpstime',
                   'input_ports', 'output_ports', 'geo', 'comment']
    elif action_tag == 'co':  # connection_info
        columns = []
    elif action_tag == 'no':  # notes
        columns = ['hpn', 'comment']
    dossier = handling.get_dossier(hpn=args.hpn, rev=args.revision, at_date=date_query,
                                   notes_start_date=notes_start_date, exact_match=args.exact_match)
    print(handling.show_dossier(dossier, columns))
