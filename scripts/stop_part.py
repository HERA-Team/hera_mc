#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to stop a specified part in the parts_paper table.

Note that 'now' is the default --date.  If you don't want to be
queried for a --date, then you should include --date <date> on the
command line.  One "trick" is that if you wish to not be queried but
use 'now' (e.g. in a script), you can specify --date Now;  or just
use the date.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect
import sys
import copy


def query_args(args):
    """
    Gets information from user
    """
    if args.part is None:
        args.part = raw_input("Part number:  ")
    if args.rev is None:
        args.rev = raw_input("Revision:  ")
    if args.date == 'now':
        args.date = cm_utils._query_default('date', args)
    return args


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-p', '--part', help="Part number", default=None)
    parser.add_argument('-r', '--rev', help='Revision', default=None)
    parser.add_argument('--actually_do_it', help="Flag to actually do it, as "
                        "opposed to printing out what it would do.",
                        action='store_true')
    cm_utils.add_date_time_args(parser)
    args = parser.parse_args()

    args = query_args(args)

    # Pre-process some args
    at_date = cm_utils._get_astropytime(args.date, args.time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    # Stop parts
    np = [[args.part, args.rev]]
    part_connect.stop_existing_parts(session, np, at_date, args.actually_do_it)
