#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold scripts to check various parts/revisions

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

    overlapping = {}
    found_some = False
    for p in args.part:
        overlap = cm_revisions.check_part_for_overlapping_revisions(p, session)
        if len(overlap) > 0:
            overlapping[p] = overlap
            found_some = True
    if found_some:
        print("Overlapping part revisions are:")
        for k, p in overlapping.iteritems():
            if len(p) > 0:
                print('\t' + p)
    else:
        print("No overlapping part revisions were found.")
