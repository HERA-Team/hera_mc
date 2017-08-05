#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle adding a general part.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling
import sys
import copy


def query_args(args):
    """
    Gets information from user
    """
    if args.hpn is None:
        args.hpn = raw_input('HERA part number:  ')
    if args.rev is None:
        args.rev = raw_input('HERA part revision:  ')
    if args.hptype is None:
        args.hptype = raw_input('HERA part type:  ')
    if args.mfg is None:
        args.mfg = raw_input('Manufacturers number for part:  ')
    args.date = cm_utils._query_default('date', args)
    return args

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-p', '--hpn', help="HERA part number", default = None)
    parser.add_argument('-r', '--rev', help="Revision number of part", default=None)
    parser.add_argument('-t', '--hptype', help="HERA part type", default = None)
    parser.add_argument('-m', '--mfg', help="Manufacturers number for part", default = None)
    parser.add_argument('--actually_do_it', help="Flag to actually do it, as opposed to printing out what it would do.", action='store_true')
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    if args.hpn is None or args.rev is None or args.hptype is None or args.mfg is None:
        args = query_args(args)

    # Pre-process some args
    at_date = cm_utils._get_astropytime(args.date, args.time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(session)
    part_check = handling.get_part_dossier(hpn=args.hpn, rev=args.rev, at_date=at_date, exact_match=True)

    # Check for part
    if len(part_check.keys()>0):
        print("Error:  {} is already in parts database".format(args.hpn))
        print("Stopping this addition.")
    else:
        # Add new part
        print("Adding new part {}:{}".format(args.hpn,args.rev))
        new_part_add = [(args.hpn, args.rev, args.hptype, args.mfg)]
        part_connect.add_new_parts(session, part, new_part_add, at_date, args.actually_do_it)



