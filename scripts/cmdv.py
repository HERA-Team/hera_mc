#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Allows some different data views of cm database.

"""
from __future__ import absolute_import, division, print_function
from hera_mc import mc, geo_handling, cm_utils, cm_revisions
from astropy.time import Time, TimeDelta
import sys

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  fcview, info [fcview]", default='fcview')
    parser.add_argument('-p', '--part', help="Part list (comma-separated,no spaces) [HH0]", default='HH0')
    cm_utils.add_date_time_args(parser)
    parser.add_argument(
        '--date2', help="UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' [now]",
        default='now')
    parser.add_argument(
        '--time2', help="UTC hh:mm or float (hours)", default=0.0)
    args = parser.parse_args()

    args.action = args.action.lower()[:3]

    if args.action == 'inf':
        print(
            """
        Available actions are (only need first three letters) [fcview]:
            fcview:  fully-connected view of part --part(-p) between date and date2.
                     both default to 'now', so at least date must be changed.
            info:  Print this information and exit.
        """
        )
        sys.exit()

    # start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    if ',' in args.part:
        args.part = args.part.split(',')
    else:
        args.part = [args.part]
