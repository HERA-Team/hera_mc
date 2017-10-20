#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This publishes a webpage on paper1 (leveraging the rails stuff) that includes power levels.
If not on qmaster, it just writes the html file.

"""
from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, sys_handling

if __name__ == '__main__':
    default_hookup_cols = ['station', 'front-end', 'cable-post-amp(in)', 'post-amp', 'cable-container', 'f-engine', 'level']
    parser = mc.get_mc_argument_parser()
    # set values for 'action' to use
    parser.add_argument('-p', '--hpn', help="Part number, csv-list (required). HH", default='HH')
    parser.add_argument('-r', '--revision', help="Specify revision or last/active/full/all for hpn.  [A]", default='A')
    parser.add_argument('-e', '--exact-match', help="Force exact matches on part numbers, not beginning N char. [False]",
                        dest='exact_match', action='store_true')
    parser.add_argument('--hookup-cols', help="Specify a subset of parts to show in mapr, comma-delimited no-space list.",
                        dest='hookup_cols', default=default_hookup_cols)

    args = parser.parse_args()

    # Pre-process the args
    args.hpn = cm_utils.listify(args.hpn)
    args.hookup_cols = cm_utils.listify(args.hookup_cols)

    # Start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    system = sys_handling.Handling(session)
    system.publish_summary(args.hpn, rev=args.revision, exact_match=args.exact_match, hookup_cols=args.hookup_cols)
