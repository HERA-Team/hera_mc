#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle adding a part.
"""

from hera_mc import mc, cm_utils, cm_partconnect


def query_args(args):
    """
    Gets information from user
    """
    if args.hpn is None:
        args.hpn = input("HERA part number:  ")
    if args.rev is None:
        args.rev = input("HERA part revision:  ")
    if args.hptype is None:
        args.hptype = input("HERA part type:  ")
    if args.mfg is None:
        args.mfg = input("Manufacturers number for part:  ")
    args.date = cm_utils.query_default("date", args)
    return args


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument("-p", "--hpn", help="HERA part number", default=None)
    parser.add_argument("-r", "--rev", help="Revision number of part", default=None)
    parser.add_argument("-t", "--hptype", help="HERA part type", default=None)
    parser.add_argument(
        "-m", "--mfg", help="Manufacturers number for part", default=None
    )
    parser.add_argument(
        "--disallow_restart",
        dest="allow_restart",
        help="Flag to disallow restarting an " "existing and stopped part",
        action="store_false",
    )
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    if args.hpn is None or args.rev is None or args.hptype is None or args.mfg is None:
        args = query_args(args)

    # Pre-process some args
    at_date = cm_utils.get_astropytime(args.date, args.time, args.format)
    args.verbosity = cm_utils.parse_verbosity(args.verbosity)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    if args.verbosity > 1:
        print("Trying to add new part {}:{}".format(args.hpn, args.rev))
    new_part = [[args.hpn, args.rev, args.hptype, args.mfg]]
    cm_partconnect.add_new_parts(
        session, part_list=new_part, at_date=at_date, allow_restart=args.allow_restart
    )
