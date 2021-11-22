#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to add a general connection to the database.
"""

from hera_mc import mc, cm_utils, cm_partconnect, cm_handling


def query_args(args):
    """
    Gets information from user
    """
    if args.uppart is None:
        args.uppart = input("Upstream part number:  ")
    if args.uprev is None:
        args.uprev = input("Upstream part revision:  ")
    if args.upport is None:
        args.upport = input("Upstream output port:  ")
    if args.dnpart is None:
        args.dnpart = input("Downstream part number:  ")
    if args.dnrev is None:
        args.dnrev = input("Downstream part revision:  ")
    if args.dnport is None:
        args.dnport = input("Downstream input port:  ")
    if args.date == "now":
        args.date = cm_utils.query_default("date", args)
    return args


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument("-u", "--uppart", help="Upstream part number", default=None)
    parser.add_argument("--uprev", help="Upstream part revision", default=None)
    parser.add_argument("--upport", help="Upstream output port", default=None)
    parser.add_argument("-d", "--dnpart", help="Downstream part number", default=None)
    parser.add_argument("--dnrev", help="Downstream part revision", default=None)
    parser.add_argument("--dnport", help="Downstream input port", default=None)
    cm_utils.add_date_time_args(parser)
    args = parser.parse_args()

    args = query_args(args)

    # Pre-process some args
    if args.date is not None:
        at_date = cm_utils.get_astropytime(args.date, args.time, args.format)
    c = cm_partconnect.Connections()
    c.connection(
        upstream_part=args.uppart,
        up_part_rev=args.uprev,
        upstream_output_port=args.upport,
        downstream_part=args.dnpart,
        down_part_rev=args.dnrev,
        downstream_input_port=args.dnport,
    )

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    handling = cm_handling.Handling(session)
    chk = handling.get_specific_connection(c, at_date)
    if len(chk) == 1 and chk[0].stop_gpstime is None:
        connection_start_was = chk[0].start_gpstime
        print(
            "Stopping connection {}:{}:{} <-> {}:{}:{} : {}".format(
                args.uppart,
                args.uprev,
                args.upport,
                args.dnpart,
                args.dnrev,
                args.dnport,
                connection_start_was,
            )
        )
        go_ahead = True
    else:
        print("Error:  Connection to stop is not valid.  Quitting.")
        print(
            "{}:{}:{} <X> {}:{}:{}".format(
                args.uppart,
                args.uprev,
                args.upport,
                args.dnpart,
                args.dnrev,
                args.dnport,
            )
        )
        go_ahead = False

    if go_ahead:
        # Connect parts
        npc = [
            [
                args.uppart,
                args.uprev,
                args.dnpart,
                args.dnrev,
                args.upport,
                args.dnport,
                connection_start_was,
            ]
        ]
        cm_partconnect.stop_connections(session, npc, at_date)
