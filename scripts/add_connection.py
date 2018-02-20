#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to add a general connection to the database.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling, cm_health
import sys
import copy


def query_args(args):
    """
    Gets information from user
    """
    if args.uppart is None:
        args.uppart = raw_input('Upstream part number:  ')
    if args.uprev is None:
        args.uprev = raw_input('Upstream part revision:  ')
    if args.upport is None:
        args.upport = raw_input('Upstream output port:  ')
    if args.dnpart is None:
        args.dnpart = raw_input('Downstream part number:  ')
    if args.dnrev is None:
        args.dnrev = raw_input('Downstream part revision:  ')
    if args.dnport is None:
        args.dnport = raw_input('Downstream input port:  ')
    if args.date == 'now':  # note that 'now' is the current default.
        args.date = cm_utils.query_default('date', args)
    return args


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-u', '--uppart', help="Upstream part number", default=None)
    parser.add_argument('--uprev', help='Upstream part revision', default=None)
    parser.add_argument('--upport', help='Upstream output port', default=None)
    parser.add_argument('-d', '--dnpart', help="Downstream part number", default=None)
    parser.add_argument('--dnrev', help='Downstream part revision', default=None)
    parser.add_argument('--dnport', help='Downstream input port', default=None)
    parser.add_argument('--actually_do_it', help="Flag to actually do it, as "
                        "opposed to printing out what it would do.",
                        action='store_true')
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    args = query_args(args)

    # Pre-process some args
    at_date = cm_utils.get_astropytime(args.date, args.time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    connect = part_connect.Connections()
    handling = cm_handling.Handling(session)
    up_check = handling.get_connection_dossier(hpn_list=[args.uppart], rev=args.uprev,
                                               port=args.upport, at_date=at_date,
                                               exact_match=True)
    dn_check = handling.get_connection_dossier(hpn_list=[args.dnpart], rev=args.dnrev,
                                               port=args.dnport, at_date=at_date,
                                               exact_match=True)
    # Check for connection
    c = part_connect.Connections()
    c.connection(upstream_part=args.uppart, up_part_rev=args.uprev, upstream_output_port=args.upport,
                 downstream_part=args.dnpart, down_part_rev=args.dnrev, downstream_input_port=args.dnport)
    chk = handling.get_specific_connection(c, at_date)
    if len(chk) == 0:
        go_ahead = True
    elif len(chk) == 1 and chk[0].stop_gpstime is not None:
        go_ahead = True
    else:
        go_ahead = False

    if go_ahead:
        if args.verbosity == 'h':
            print('Adding connection {}:{}:{} <-> {}:{}:{}'
                  .format(args.uppart, args.uprev, args.upport, args.dnpart, args.dnrev, args.dnport))
        # Connect parts
        npc = [[args.uppart, args.uprev, args.upport, args.dnpart, args.dnrev, args.dnport]]
        part_connect.add_new_connections(session, connect, npc, at_date, args.actually_do_it)
