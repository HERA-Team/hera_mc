#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle adding data to the part_rosetta table.
"""

from hera_mc import mc, cm_utils, cm_partconnect


def query_args(args):
    """
    Gets information from user
    """
    if args.hpn is None:
        args.hpn = input("HERA part number:  ")
    if args.syspn is None:
        args.syspn = input("System part number:  ")
    args.date = cm_utils.query_default("date", args)
    args.time = cm_utils.query_default("time", args)
    args.date2 = cm_utils.query_default("date2", args)
    args.time2 = cm_utils.query_default("time2", args)
    return args


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument("hpn", nargs="?", help="HERA part number")
    parser.add_argument("syspn", nargs="?", help="System part number")
    parser.add_argument(
        "-q", "--query", help="Set flag if wished to be queried", action="store_true"
    )
    cm_utils.add_date_time_args(parser)
    parser.add_argument("--date2", help="Stop date (if not None)", default=None)
    parser.add_argument("--time2", help="Stop time (if not None)", default=None)
    parser.add_argument(
        "--time2float_format", help="Format is date2 is unix, gps, jd", default=None
    )
    parser.add_argument("--verbose", help="Turn verbose mode on.", action="store_true")
    args = parser.parse_args()

    if args.query:
        args = query_args(args)

    # Pre-process some args
    start_date = cm_utils.get_astropytime(args.date, args.time, args.format)
    stop_date = cm_utils.get_astropytime(args.date2, args.time2, args.time2float_format)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    # Check for part
    if args.verbose:
        print("Adding part_rosetta {}: - {}".format(args.hpn, args.syspn))
    cm_partconnect.update_part_rosetta(
        args.hpn, args.syspn, start_date, stop_date, session
    )
