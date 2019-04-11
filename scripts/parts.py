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

from hera_mc import cm_handling, cm_utils, mc

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  info, types, part_info, conn_info, rev_info, \
                                                   physical, check_rev, health.  'info' for more.", default='part_info')
    # set values for 'action' to use
    parser.add_argument('-p', '--hpn', help="Part number or portion thereof, csv-list. [None]", default=None)
    parser.add_argument('-r', '--revision', help="Specify revision or last/active/full/all for hpn.  [active]", default='active')
    parser.add_argument('--port', help="Specify port [all]", default='all')
    parser.add_argument('-e', '--exact-match', help="Force exact matches on part numbers, not beginning N char. [False]",
                        dest='exact_match', action='store_true')
    parser.add_argument('--notes', help="<For action=part_info>:  Displays part notes with posting dates and not other info",
                        action='store_true')
    parser.add_argument('--sort_notes_by', help="<For action=part_info --notes> Can sort the notes listing by part \
                        ('part') or posting time ('post') [part]", default='part')
    cm_utils.add_verbosity_args(parser)
    cm_utils.add_date_time_args(parser)
    parser.add_argument('--notes_start_date', help="<For part_info notes> start_date for notes [<]", default='<')
    parser.add_argument('--notes_start_time', help="<For part_info notes> start_time for notes", default=0.0)

    args = parser.parse_args()

    args.verbosity = cm_utils.parse_verbosity(args.verbosity)
    action_tag = args.action[:2].lower()
    args.hpn = cm_utils.listify(args.hpn)
    date_query = cm_utils.get_astropytime(args.date, args.time)
    notes_start_date = cm_utils.get_astropytime(args.notes_start_date, args.notes_start_time)

    if action_tag == 'in':
        print(
            """
        Available actions are (only need first two letters):
            info:  this information
            part_info:  provide a summary of given part/rev
            conn_info:  provide a summary of connections to given part/rev/port
            rev_info:  provide a summary of revisions of given part/rev
            types:  provide a summary of part types
            physical:  shows the "physical" connections, which are those _not_ needed
                       to uniquely track antenna-to-correlator but that we still want to
                       track though, e.g. power, rack location, ...
                       (Use 'hookup.py' to look at the connections that see the
                       station-correlator hookup)
            check_rev:  checks whether a given part/rev exists
            health:  runs various "health" checks

        Args needing values (or defaulted):
            -p/--hpn:  part name [None]
            -r/--revision:  revision (particular/last/active/full/all) [Active]
            --port:  port name [ALL]
            --date:  query date [now]
            --time:  query time
            --notes_start_date:  start date for notes display [<]
            --notes_stop_time:  start time for notes display
            --sort_notes_by:  for the full notes listing (i.e. where hpn=None), you may sort by
                              the part number ('part') or by the posting time ('post')

        Args that are flags
            -e/--exact-match:  match part number exactly, or specify first characters [False]
            --notes:  <For part_info>  Displays part notes with posting dates
        """
        )
        sys.exit()

    # Start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    handling = cm_handling.Handling(session)

    # Process
    if action_tag == 'ty':  # types of parts
        part_type_dict = handling.get_part_types(args.port, date_query)
        handling.show_part_types()
        sys.exit()

    if action_tag == 'ph':  # physical port connections
        ppc = handling.get_physical_connections(date_query)
        handling.show_connections(ppc, headers=['Upstream', '<uOutput:', ':dInput>', 'Downstream', 'dStart', 'dStop'])
        sys.exit()

    if action_tag == 'he':  # overlapping revisions
        from hera_mc import cm_health
        healthy = cm_health.Connections(session)
        if args.hpn is None:
            healthy.check_for_duplicate_connections(display_results=True)
        else:
            for hpn in args.hpn:
                healthy.check_for_existing_connection(hpn, display_results=True)
            for hpn in args.hpn:
                cm_health.check_part_for_overlapping_revisions(hpn, session)
        sys.exit()

    if args.hpn is None and not (action_tag == 'pa' and args.notes):
        print("Need to supply a part name.")
        sys.exit()

    if action_tag == 'pa':  # part_info
        part_dossier = handling.get_part_dossier(hpn=args.hpn, rev=args.revision, at_date=date_query,
                                                 notes_start_date=notes_start_date, sort_notes_by='part',
                                                 exact_match=args.exact_match, full_version=True)
        handling.show_parts(part_dossier, args.notes)
    elif action_tag == 'co':  # connection_info
        connection_dossier = handling.get_part_connection_dossier(
            hpn=args.hpn, rev=args.revision, port=args.port,
            at_date=date_query, exact_match=args.exact_match)
        handling.show_connections(connection_dossier, verbosity=args.verbosity)
    elif action_tag == 're':  # revisions
        for hpn in args.hpn:
            rev_ret = cm_handling.cmrev.get_revisions_of_type(hpn, args.revision, date_query, session)
            if hpn.lower() != 'help':
                cm_handling.cmrev.show_revisions(rev_ret)
    elif action_tag == 'ch':  # check revisions
        for hpn in args.hpn:
            rev_chk = cm_handling.cmrev.get_revisions_of_type(hpn, args.revision, date_query, session)
            print("{}:{} ".format(hpn, args.revision), end='')
            if len(rev_chk):
                for r in rev_chk:
                    start = cm_utils.get_time_for_display(r.started)
                    end = cm_utils.get_time_for_display(r.ended)
                    print("found as {}:{}    start: {}  end: {}".format(r.hpn, r.rev, start, end))
            else:
                print("not found.")
