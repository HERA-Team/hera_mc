#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle swapping of FEMs.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling, cm_hookup
import sys
import copy


def query_args(args):
    """
    Gets information from user
    """
    if args.ant == None:
        args.ant = raw_input('Antenna containing the FEM:  ')
    if args.fem_number == None:
        print('The FEM has a five digit number on it.')
        args.fem_number = raw_input('What is the number:  ')
    args.date = cm_utils._query_default('date', args)
    return args


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-a', '--ant', help="Antenna number", default=None)
    parser.add_argument('-f', '--fem-number', dest='fem_number', help="Serial number of FEM", default=None)
    parser.add_argument('--rev', help="Revision number of FEM (currently A)", default='A')
    parser.add_argument('--actually_do_it', help="Flag to actually do it, as opposed to printing out what it would do.", action='store_true')
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    if args.ant is None or args.fem_number is None:
        args = query_args(args)

    # Pre-process some args
    if args.ant[0].upper() != 'A':
        args.ant = 'A' + args.ant
    args.verbosity = args.verbosity.lower()
    at_date = cm_utils._get_datetime(args.date, args.time)
    fem_hpn = 'FEM' + args.fem_number
    show_args = {'show-levels': False}

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(session)
    hookup = cm_hookup.Hookup(session)

    if handling.is_in_connections(fem_hpn, args.rev):
        go_ahead = False
        print("Error:  {} is already connected".format(fem_hpn))
        print("Stopping this swap.")
    else:
        go_ahead = True
        hd = hookup.get_hookup(hpn=args.ant, rev='H', port='all', at_date=at_date, state_args=show_args, exact_match=True)
        k = hd['hookup'].keys()[0]
        old_fe = hd['hookup'][k][3]
        hookup.show_hookup(hd, 'all', False)
        print('Old front-end "balun":  {}:{}'.format(old_fe.upstream_part,old_fe.up_part_rev))
        ctr = 99
        if ctr > 1:
            go_ahead = False
            print("Error:  multiple connections to {}".format(fem_hpn))
            print("Stopping this swap.")
        else:
            k = rc['connections'].keys()[0]
            old_balun = rc['connections'][k].downstream_part
            old_brev = rc['connections'][k].down_part_rev
            print('Replacing {}:{} with {}:{}'.format(old_rcvr, old_rrev, new_hpn, new_rev))

    if go_ahead:
        # Add new PAM
        new_pam = [(new_hpn, new_rev, 'post-amp module', args.pam_number)]
        part_connect.add_new_parts(session, part, new_pam, at_date, args.actually_do_it)

        # Disconnect previous RCVR on both sides (RI/RO)
        pcs = [(old_rcvr, old_rrev, 'ea'), (old_rcvr, old_rrev, 'na'), (old_rcvr, old_rrev, 'eb'), (old_rcvr, old_rrev, 'nb')]
        part_connect.stop_existing_connections(session, handling, pcs, at_date, args.actually_do_it)

        # Connect new PAM on both sides (RI/RO)
        npc = [(rie, 'A', 'b', new_hpn, new_rev, 'ea'), (rin, 'A', 'b', new_hpn, new_rev, 'na'),
               (new_hpn, new_rev, 'eb', roe, 'A', 'a'), (new_hpn, new_rev, 'nb', ron, 'A', 'a')]
        part_connect.add_new_connections(session, connect, npc, at_date, args.actually_do_it)
