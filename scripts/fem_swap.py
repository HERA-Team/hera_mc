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
    if args.ant is None:
        args.ant = raw_input('Antenna containing the FEM:  ')
    if args.fem_number is None:
        print('The FEM has a five digit number on it.')
        args.fem_number = raw_input('What is the number:  ')
    args.date = cm_utils._query_default('date', args)
    return args


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-a', '--ant', help="Antenna number", default=None)
    parser.add_argument('-f', '--fem-number', dest='fem_number',
                        help="Serial number of FEM", default=None)
    parser.add_argument('--rev', help="Revision number of FEM (currently A)",
                        default='A')
    parser.add_argument('--actually_do_it', help="Flag to actually do it, as "
                        "opposed to printing out what it would do.",
                        action='store_true')
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    if args.ant is None or args.fem_number is None:
        args = query_args(args)

    # Pre-process some args
    if args.ant[0].upper() != 'A':
        args.ant = 'A' + args.ant
    args.verbosity = args.verbosity.lower()
    at_date = cm_utils._get_astropytime(args.date, args.time)
    fem_hpn = 'FEM' + args.fem_number

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(session)
    hookup = cm_hookup.Hookup(session)

    if handling.is_in_connections(fem_hpn, args.rev):
        print("<<<<<<<Error>>>>>>>  {} is already connected".format(fem_hpn))
        sys.exit()
    # ###ERROR EXIT POINT

    hd = hookup.get_hookup(hpn_list=[args.ant], rev='H', port='all', at_date=at_date,
                           exact_match=True)
    k = hd['hookup'].keys()[0]
    if len(hd['hookup'][k]['e']) == 0:
        print("<<<<<<<ERROR>>>>>>>  'e' hookup is len(0)")
        print(hd['hookup'][k]['e'])
        sys.exit()
    # ###ERROR EXIT POINT

    old_fd = hd['hookup'][k]['e'][1]
    if len(hd['hookup'][k]['e']) < 4:
        print("<<< {} does not have the expected hookup.".format(k))
        old_fe = None
    else:
        old_fe = hd['hookup'][k]['e'][3]
        bal_conn = handling.get_connection_dossier([old_fe.upstream_part],
                                                   old_fe.up_part_rev, 'all',
                                                   at_date, exact_match=True)
        ctr = len(bal_conn['connections'].keys())
        if ctr < 3:  # This is an ill-defined variable...
            print("<<<<<<<Error>>>>>>>  unexpected number of connections to {}".
                  format(old_fe.upstream_part))
            print(bal_conn['connections'])
            print(len(bal_conn['connections']))
            sys.exit()
    # ###ERROR EXIT POINT

    # Add new FEM
    new_fem = [(fem_hpn, args.rev, 'front-end', args.fem_number)]
    part_connect.add_new_parts(session, part, new_fem, at_date, args.actually_do_it)

    if old_fe is not None:
        # Disconnect previous FE on both sides (FD/C7)
        balun = old_fe.upstream_part
        brev = old_fe.up_part_rev
        print('Replacing {}:{} with {}:{}'.format(balun, brev, fem_hpn, args.rev))
        pcs = [(balun, brev, 'input'), (balun, brev, 'n'), (balun, brev, 'e')]
        part_connect.stop_existing_connections_to_part(session, handling, pcs, at_date,
                                                       args.actually_do_it)
        # Connect new FEM on both sides (FD/C7)
        npc = []
        for k, c in bal_conn['connections'].iteritems():
            x = None
            if c.stop_gpstime is None:
                if (c.downstream_part.upper() == balun.upper() and
                        c.down_part_rev.upper() == brev.upper()):
                    x = [c.upstream_part, c.up_part_rev, c.upstream_output_port,
                         fem_hpn, args.rev, 'input']
                elif (c.upstream_part.upper() == balun.upper() and
                      c.up_part_rev.upper() == brev.upper()):
                    port_name = c.downstream_input_port.lower()[0]
                    x = [fem_hpn, args.rev, port_name, c.downstream_part,
                         c.down_part_rev, c.downstream_input_port]
                else:
                    print("Didn't find the part...")
                    print(c)
                if x is not None:
                    npc.append(x)
        part_connect.add_new_connections(session, connect, npc, at_date,
                                         args.actually_do_it)
    else:
        # Disconnect previous FE on C7F side
        C7F = 'C7F' + args.ant.strip('A')
        C7F_rev = 'A'
        c7_conn = handling.get_connection_dossier(C7F, C7F_rev, 'all',
                                                  at_date, exact_match=True)
        for k, c in c7_conn['connections'].iteritems():
            if c.downstream_input_port == 'na':
                balun = c7_conn['connections'][k].upstream_part
                brev = c7_conn['connections'][k].up_part_rev
        print("Stopping {}:{} - {}:{}".format(C7F, C7F_rev, balun, brev))
        pcs = [(balun, brev, 'n'), (balun, brev, 'e')]
        part_connect.stop_existing_connections_to_part(session, handling, pcs, at_date,
                                                       args.actually_do_it)
        # Connect new FEM on both sides (FD/C7)
        feed = old_fd.downstream_part
        frev = old_fd.down_part_rev
        print('Adding {}:{} to {}:{}'.format(feed, frev, fem_hpn, args.rev))
        npc = [
              [feed, frev, 'terminals', fem_hpn, args.rev, 'input'],
              [fem_hpn, args.rev, 'e', C7F, C7F_rev, 'ea'],
              [fem_hpn, args.rev, 'n', C7F, C7F_rev, 'na']
        ]
        part_connect.add_new_connections(session, connect, npc, at_date,
                                         args.actually_do_it)
