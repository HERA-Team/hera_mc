#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This checks either a supplied part list or all of the parts
to find whether it has any overlapping revisions in time.  It
only prints a warning and the info.
"""

from __future__ import absolute_import, division, print_function
from hera_mc import mc, cm_revisions, cm_handling, cm_utils
import sys

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-p', '--part', help="Part number or list (comma-separated, no spaces)", default=None)

    args = parser.parse_args()

    # start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    h = cm_handling.Handling(session)
    at_date = cm_utils._get_astropytime('now')

    if args.part is None:
        part_dict = h.get_part_types(at_date, show_hptype=True)
        args.part = []
        for k, v in part_dict.iteritems():
            for p in v['part_list']:
                if p not in args.part:
                    args.part.append(p)
    elif ',' in args.part:
        args.part = args.part.split(',')
    else:
        args.part = [args.part]

    found_some = False
    for p in args.part:
        overlap = cm_revisions.check_part_for_overlapping_revisions(p, session)
        if len(overlap) > 0:
            found_some = True
    if found_some:
        print("Overlapping part revisions were found.")
    else:
        print("No overlapping part revisions were found.")
