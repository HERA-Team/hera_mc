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
    at_date = cm_utils._get_datetime(args.date,args.time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(session)
    part_check = handling.get_part_dossier(hpn=args.hpn, rev=args.rev, at_date=at_date, exact_match=True)

    # Check for part
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

