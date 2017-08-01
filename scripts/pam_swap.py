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
    if args.receiverator == None:
        args.receiverator = raw_input('Receiverator containing the PAM:  ')
    if args.r_input == None:
        args.r_input = raw_input('What input on the receiverator (A1-B8):  ')
    if args.pam_number == None:
        print('The PAM has a five digit number on the front bottom.')
        args.pam_number = raw_input('What is the number:  ')
    args.date = cm_utils._query_default('date', args)
    return args


def get_mfg_number(hrev):
    full_part = handling.get_part(hrev[0],hrev[1],exact_match=True)
    if len(full_part.keys())>1:
        print("Too many parts for old rev:  ",hrev, full_part.keys())
        raise ValueError
    else:
        mfg = full_part[full_part.keys()[0]]['part'].manufacturer_number
    if mfg[:3]=='S/N':
        mfg = 'H' + mfg[3:]
    elif hrev[0][0]=='A':
        print("Mfg number wrong:  ",mfg)
        raise ValueError
    elif hrev[0][0]!='F':
        print('Wrong rev:  ',hrev)
    return mfg
def get_feed(hookup):
    feed_col = previous_hookup['columns'].index('feed')
    feeds = []
    frs = []
    for pk in previous_hookup.keys():
        if pk != 'columns':
            feeds.append(previous_hookup[pk][feed_col].upstream_part)
            frs.append(previous_hookup[pk][feed_col].up_part_rev)
    if len(feeds)!=2:
        print('Wrong number of feed options.')
        raise ValueError
    if feeds[0]!=feeds[1] or frs[0]!=frs[1]:
        print("Feed options don't match",feeds,frs)
        raise ValueError
    return feeds[0],frs[0]

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-r', '--receiverator', help="Receiverator number (1-8)", default = None)
    parser.add_argument('-i', '--input', dest='r_input', help="Input to receiverator (A1-B8)", default = None)
    parser.add_argument('-p', '--pam-number', dest='pam_number', help="Serial number of PAM", default = None)
    parser.add_argument('--rev', help="Revision number of PAM (currently B)", default='B')
    parser.add_argument('--actually_do_it', help="Flag to actually do it, as opposed to printing out what it would do.", action='store_true')
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    if args.receiverator is None or args.r_input is None or args.pam_number is None:
        args = query_args(args)

    # Pre-process some args
    args.r_input = args.r_input.upper()
    args.verbosity = args.verbosity.lower()
    at_date = cm_utils._get_datetime(args.date,args.time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(session)

    # Check for PAM and find RCVR
    new_hpn = 'PAM'+args.pam_number
    new_rev = 'B'  #This is the current revision number of the supplied PAMs
    rie = 'RI'+args.receiverator+args.r_input+'E'
    rin = 'RI'+args.receiverator+args.r_input+'N'
    roe = 'RO'+args.receiverator+args.r_input+'E'
    ron = 'RO'+args.receiverator+args.r_input+'N'
    if handling.is_in_connections(new_hpn, new_rev):
        go_ahead = False
        print("Error:  {} is already connected".format(new_hpn))
        print("Stopping this swap.")
    else:
        go_ahead = True
        rc = handling.get_connection_dossier(hpn=rie,rev='A',port='b', at_date=at_date, exact_match=True)
        ctr = len(rc['connections'].keys())
        if ctr>1:
            go_ahead = False
            print("Error:  multiple connections to {}".format(new_hpn))
            print("Stopping this swap.")
        else:
            k = rc['connections'].keys()[0]
            old_rcvr = rc['connections'][k].downstream_part
            old_rrev = rc['connections'][k].down_part_rev
            print('Replacing {}:{} with {}:{}'.format(old_rcvr, old_rrev, new_hpn, new_rev))

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

