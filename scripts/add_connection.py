#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to add a general connection to the database.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling
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
    args.date = cm_utils._query_default('date', args)
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
    at_date = cm_utils._get_astropytime(args.date, args.time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    connect = part_connect.Connections()
    handling = cm_handling.Handling(session)
    up_check = handling.get_connection_dossier(hpn=args.uppart, rev=args.uprev,
                                               port=args.upport, at_date=at_date,
                                               exact_match=True)
    dn_check = handling.get_connection_dossier(hpn=args.dnpart, rev=args.dnrev,
                                               port=args.dnport, at_date=at_date,
                                               exact_match=True)

    # Check for upward connection downstream
    for k, v in up_check['connection'].iteritems():
        if v.upstream_part.lower() == args.uppart.lower() and v.up_part_rev.lower() == args.uprev and
            v.upstream_output_port.lower() == args.upport.lower() and v.stop_gpstime is not None:
                go_ahead = False
                print("Error:  {}:{}<{}> is already actively connected to {}".format(args.uppart, 
                    args.uprev, args.upport, v.downstream_part))
    # Check for downward connection upstream
    for k, v in dn_check['connection'].iteritems():
        if v.downstream_part.lower() == args.dnpart.lower() and v.down_part_rev.lower() == args.dnrev and
            v.downstream_input_port.lower() == args.dnport.lower() and v.stop_gpstime is not None:
                go_ahead = False
                print("Error:  {}:{}<{}> is already actively connected to {}".format(args.dnpart, 
                    args.dnrev, args.dnport, v.upstream_part))


    if go_ahead:
        print('Adding connection {}:{}:{} <-> {}:{}:{}'
              .format(args.uppart, args.uprev, args.upport, args.dnpart,
                      args.dnrev, args.dnport))
        # Connect parts
        npc = [[args.uppart, args.uprev, args.upport, args.dnpart, args.dnrev, args.dnport]]
        part_connect.add_new_connections(session, connect, npc, at_date, args.actually_do_it)
