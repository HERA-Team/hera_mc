#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle swapping of PAMs.
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
    parser.add_argument('-u', '--uppart', help="Upstream part number", default = None)
    parser.add_argument('--uprev', help='Upstream part revision', default = None)
    parser.add_argument('--upport', help='Upstream output port', default = None)
    parser.add_argument('-d', '--dnpart', help="Downstream part number", default=None)
    parser.add_argument('--dnrev', help='Downstream part revision', default = None)
    parser.add_argument('--dnport', help='Downstream input port', default = None)
    parser.add_argument('--actually_do_it', help="Flag to actually do it, as opposed to printing out what it would do.", action='store_true')
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    args = query_args(args)

    # Pre-process some args
    at_date = cm_utils._get_datetime(args.date,args.time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(session)
    up_check = handling.get_connection_dossier(hpn=args.uppart, rev=args.uprev, port=args.upport, at_date=at_date, exact_match=True)
    dn_check = handling.get_connection_dossier(hpn=args.dnpart, rev=args.uprev, port=args.upport, at_date=at_date, exact_match=True)

    # Check for connection
    if len(part_check.keys()>0):
        go_ahead = False
        print("Error:  {} is already connected".format(new_hpn))
        print("Stopping this swap.")
    else:
        go_ahead = True
        rc = handling.get_connection_dossier(hpn=rie,rev='A',port='b', at_date=at_date, exact_match=True)
        ctr = 0
        for k in rc.keys():
            if k not in handling.non_class_connection_dossier_entries:
                ctr+=1
                old_rcvr = rc[k].downstream_part
                old_rrev = rc[k].down_part_rev
                print('Replacing {}:{} with {}:{}'.format(old_rcvr, old_rrev, new_hpn, new_rev))
            if ctr>1:
                go_ahead = False
                print("Error:  multiple connections to {}".format(new_hpn))
                print("Stopping this swap.")
    if go_ahead:
        # Add new PAM
        new_pam = [(new_hpn,new_rev,'post-amp module',args.pam_number)]
        part_connect.add_new_parts(session, part, new_pam, at_date, args.actually_do_it)

        # Disconnect previous RCVR on both sides (RI/RO)
        pcs = [(old_rcvr,old_rrev,'ea'),(old_rcvr,old_rrev,'na'),(old_rcvr,old_rrev,'eb'),(old_rcvr,old_rrev,'nb')]
        part_connect.stop_existing_connections(session, handling, pcs, at_date, args.actually_do_it)

        # Connect new PAM on both sides (RI/RO)
        npc = [(rie,'A','b',new_hpn,new_rev,'ea'),(rin,'A','b',new_hpn,new_rev,'na'),
               (new_hpn,new_rev,'eb',roe,'A','a'),(new_hpn,new_rev,'nb',ron,'A','a')]
        part_connect.add_new_connections(session, connect, npc, at_date, args.actually_do_it)

