#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle adding a comment to the part_info table.
"""

from __future__ import print_function

from hera_mc import mc, cm_utils, part_connect, cm_revisions


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
        args.library_file = cm_utils.query_default('library_file', args)
    if args.date == 'now':  # Note that 'now' is the current default.
        args.date = cm_utils.query_default('date', args)
    return args


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-p', '--hpn', help="HERA part number", default=None)
    parser.add_argument('-r', '--rev', help="Revision of part", default='last')
    parser.add_argument('-c', '--comment', help="Comment on part", default=None)
    parser.add_argument('-l', '--library_file', help="Library filename", default=None)
    cm_utils.add_date_time_args(parser)
    args = parser.parse_args()

    args = query_args(args)

    # Pre-process some args
    at_date = cm_utils.get_astropytime(args.date, args.time)
    if type(args.library_file) == str and args.library_file.lower() == 'none':
        args.library_file = None

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    if args.rev.lower() == 'last':
        args.rev = cm_revisions.get_last_revision(args.hpn, session)[0].rev
        print("Using last revision: {}".format(args.rev))

    # Check for part
    print("Adding info for part {}:{}".format(args.hpn, args.rev))
    part_connect.add_part_info(session, args.hpn, args.rev, at_date, args.comment, args.library_file)
