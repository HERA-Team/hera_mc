#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle adding a comment to the part_info table.
"""

from __future__ import print_function

from hera_mc import mc, cm_utils, part_connect


def query_args(args):
    """
    Gets information from user
    """
    if args.hpn is None:
        args.hpn = raw_input('HERA part number:  ')
    if args.rev is None:
        args.rev = raw_input('HERA part revision:  ')
    if args.comment is None:
        args.comment = raw_input('Comment:  ')
    if args.library_file is None:
        args.library_file = cm_utils._query_default('library_file', args)
    if args.date == 'now':  # Note that 'now' is the current default.
        args.date = cm_utils._query_default('date', args)
    return args


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-p', '--hpn', help="HERA part number", default=None)
    parser.add_argument('-r', '--rev', help="Revision of part", default=None)
    parser.add_argument('-c', '--comment', help="Comment on part", default=None)
    parser.add_argument('-l', '--library_file', help="Library filename", default=None)
    parser.add_argument('--swap-underscores', dest='swap_underscores', help="Replaces underscores in comment with spaces.", action='store_true')
    cm_utils.add_date_time_args(parser)
    args = parser.parse_args()

    args = query_args(args)

    # Pre-process some args
    at_date = cm_utils._get_astropytime(args.date, args.time)
    if args.library_file.lower() == 'none':
        args.library_file = None
    if args.swap_underscores:
        comment = ''
        for c in args.comment:
            if c == '_':
                comment += ' '
            else:
                comment += c
    else:
        comment = args.comment

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    # Check for part
    print("Adding info for part {}:{}".format(args.hpn, args.rev))
    part_connect.add_part_info(session, args.hpn, args.rev, at_date, comment, args.library_file)
