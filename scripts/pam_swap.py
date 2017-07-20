#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle swapping of PAMs.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling, geo_handling, cm_hookup, cm_part_revisions
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

def check_for_part(args, handling, hpn, rev):
    """
    Check to see if new part is in parts table
    """
    part_check = handling.get_part(args, hpn, rev)


def stop_previous_parts(args,hpnr_list):
    """
    This adds stop times to the previous parts. NB:  Modify/move into cm_handling (but not in the class)?
    """
    current = int(args.date.gps)
    args.add_new_part = False

    for hpnr in hpnr_list:
        print("Stopping part %s %s at %s" % (hpnr[0], hpnr[1], str(args.date)))
        data = [[hpnr[0], hpnr[1], 'stop_gpstime', current]]

    if args.actually_do_it:
        part_connect.update_part(args, data)
    else:
        print(data)


def add_new_parts(args,new_part_list):
    """
    This adds the new parts.  NB:  Modify/move into cm_hanlding (but not in class)?
    """
    current = int(args.date.gps)
    args.add_new_part = True

    for np in new_part_list:
        print("Adding part %s %s at %s" % (np[0], np[1],  str(args.date)))
        data.append([hpnr[0], hpnr[1], 'hpn', np[0]])
        data.append([hpnr[0], hpnr[1], 'hpn_rev', np[1]])
        data.append([hpnr[0], hpnr[1], 'hptype', np[2]])
        data.append([hpnr[0], hpnr[1], 'manufacturer_number', np[3]])
        data.append([hpnr[0], hpnr[1], 'start_gpstime', current])

    if args.actually_do_it:
        part_connect.update_part(args, data)
    else:
        print(data)

def get_connection_key(c,p):
    for ck in c.keys():
        if p[0] in ck:
            break
    else:
        ck = None
    return ck

def connection_active(c,p):
    for ck in c.keys():
        if p[0] in ck and c[ck].stop_gpstime is None:
            return True


def stop_previous_connections(args, h, srev, arev, frev, do_C7=False):
    """This adds stop times to the previous connections between:
           station and antenna rev A
           antenna revA and feed rev A
    """

    current = int(args.date.gps)
    data = []
    args.add_new_connection = False

    # First connection HHX:AY
    print("Stopping connection <{}:{}<ground|ground>{}:{}>".format(srev[0],srev[1],arev[0],arev[1]))
    HHXAY = h.get_connections(srev[0],srev[1],'ground',True)
    ck = get_connection_key(HHXAY,srev)
    if ck is not None:
        gps = HHXAY[ck].start_gpstime
        stopping = [srev[0], srev[1], arev[0], arev[1], 'ground', 'ground', gps, 'stop_gpstime', current]
        data.append(stopping)

    #Second connection AY:FDAY
    print("Stopping connection <{}:{}<focus|input>{}:{}>".format(arev[0],arev[1],frev[0],frev[1]))
    AYFDAY = h.get_connections(arev[0],arev[1],'focus',True)
    ck = get_connection_key(AYFDAY,arev)
    if ck is not None:
        gps = AYFDAY[ck].start_gpstime
        stopping = [arev[0], arev[1], frev[0], frev[1], 'focus', 'input', gps, 'stop_gpstime', current]
        data.append(stopping)

    #Forth connection FDAY:FEAY
    if frev[1] == 'A':
        Num = arev[0].strip('A')
        fdrev = ('FDA'+Num,'A')
        ferev = ('FEA'+Num,'A')
        print("Stopping connection <{}:{}<terminals|input>{}:{}>".format(fdrev[0],fdrev[1],ferev[0],ferev[1]))
        FDAYFEAY = h.get_connections(fdrev[0],fdrev[1],'terminals',True)
        ck = get_connection_key(FDAYFEAY,fdrev)
        if ck is not None:
            gps = FDAYFEAY[ck].start_gpstime
            stopping = [fdrev[0], fdrev[1], ferev[0], ferev[1], 'terminals', 'input', gps, 'stop_gpstime', current]
            data.append(stopping)

    if do_C7:
        # Fifth connection (pair) FEAY/A:C7FY/A;  ports e:ea, n:na
        Num = arev[0].strip('A')
        for uport in ['e','n']:
            frev = ('FEA'+Num,'A')
            crev = ('C7F'+Num,'A')
            dport = uport+'a'
            print("Stopping connection <{}:{}<{}|{}>{}:{}>".format(frev[0],frev[1],uport,dport,crev[0],crev[1]))
            FYCY = h.get_connections(frev[0],frev[1],uport,True)
            ck = get_connection_key(FYCY,frev)
            if ck is not None:
                gps = FYCY[ck].start_gpstime
                stopping = [frev[0], frev[1], crev[0], crev[1], uport, dport, gps, 'stop_gpstime', current]
                data.append(stopping)

        # Sixth connection (pair) FEAX/A:C7FX/A;  ports e:ea, n:na (if active)
        Num = srev[0].strip('HH')
        for uport in ['e','n']:
            frev = ('FEA'+Num,'A')
            crev = ('C7F'+Num,'A')
            dport = uport+'a'
            print("Stopping connection <{}:{}<{}|{}>{}:{}>".format(frev[0],frev[1],uport,dport,crev[0],crev[1]))
            FYCY = h.get_connections(frev[0],frev[1],uport,True)
            if connection_active(FYCY,frev):
                ck = get_connection_key(FYCY,frev)
                if ck is not None:
                    gps = FYCY[ck].start_gpstime
                    stopping = [frev[0], frev[1], crev[0], crev[1], uport, dport, gps, 'stop_gpstime', current]
                    data.append(stopping)

    if args.actually_do_it:
        part_connect.update_connection(args, data)
    else:
        print(data)

def add_new_connections(args, c, srev, arev, frev, do_C7=False):
    """
    This generates a connection object to send to the updater
       station and new antenna number/H
       antenna and feed
       if old feedrev is 'A', adds connection between B and FEAY/A
    """
    current = int(args.date.gps)

    # First new connection
    c.connection(upstream_part=srev[0],         up_part_rev=srev[1],
                 downstream_part=arev[0],       down_part_rev=arev[1],
                 upstream_output_port='ground', downstream_input_port='ground', start_gpstime=current,
                 stop_gpstime=None)
    __connection_updater(args,c)

    # Second new connection
    c.connection(upstream_part=arev[0],         up_part_rev=arev[1],
                 downstream_part=frev[0],       down_part_rev='B',
                 upstream_output_port='focus', downstream_input_port='input', start_gpstime=current,
                 stop_gpstime=None)
    __connection_updater(args,c)

    fea = frev[0].replace('D','E')
    # Third new connection if needed
    if frev[1] == 'A':
        c.connection(upstream_part=frev[0],     up_part_rev='B',
                     downstream_part=fea,       down_part_rev='A',
                     upstream_output_port='terminals', downstream_input_port='input', start_gpstime=current,
                     stop_gpstime=None)
        __connection_updater(args,c)

    if do_C7:
        # Hook FEA to C7F
        for uport in ['e','n']:
            c7f = 'C7F' + arev[0][1:]
            dport = uport+'a'
            c.connection(upstream_part=fea,          up_part_rev='A',
                         downstream_part=c7f,        down_part_rev='A',
                         upstream_output_port=uport, downstream_input_port=dport, start_gpstime=current,
                         stop_gpstime=None)
            __connection_updater(args,c)

def __connection_updater(args, c):
    """
    This actually updates the connections
    """
    print("Adding ", c)
    args.add_new_connection = True
    data = [[c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
             'upstream_part', c.upstream_part],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
             'up_part_rev', c.up_part_rev],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
             'downstream_part', c.downstream_part],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
             'down_part_rev', c.down_part_rev],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
             'upstream_output_port', c.upstream_output_port],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
             'downstream_input_port', c.downstream_input_port],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
             'start_gpstime', c.start_gpstime]]

    if args.actually_do_it:
        part_connect.update_connection(args, data)
    else:
        print(data)

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
    parser.add_argument('-s', '--receiverator', help="Receiverator number (1-8)", default = None)
    parser.add_argument('-i', '--r-input', dest='r_input', help="Input to receiverator (A1-B8)", default = None)
    parser.add_argument('-p', '--pam-number', dest='pam_number', help="Serial number of PAM", default = None)
    parser.add_argument('-r', '--rev', help="Revision number of PAM (currently B)", default='B')
    parser.add_argument('--actually_do_it', help="Flag to actually do it, as opposed to printing out what it would do.", action='store_true')
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    # Add extra args needed for various things
    args.show_levels = False
    args.mapr_cols = 'all'
    args.exact_match = True
    args.actually_do_it = True

    if args.receiverator is None or args.r_input is None or args.pam_number is None:
        args = query_args(args)

    # Pre-process some args
    args.r_input = args.r_input.upper()
    args.verbosity = args.verbosity.lower()
    args.date = cm_utils._get_datetime(args.date,args.time)

    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(args)
    hookup = cm_hookup.Hookup(args)

    # Stop previous PAM (aka "Receiver") if needed
    hpn = "PAM"+args.pam_number
    pn = check_for_part(args,handling,hpn,args.rev)
    print(pn)

    # Disconnect previous PAM on both sides (RI/RO)

    # Connect new PAM on both sides (RI/RO)

    go_ahead = False
    if go_ahead:
        print('Converting {}:{} to {}:{}'.format(old_antrev[0],old_antrev[1],new_antrev[0],new_antrev[1]))
        feedrev = get_feed(previous_hookup)
        if feedrev[1] == 'A':
            print('H19 - wonky feed cage, but assuming it will get replaced.')
        stop_previous_parts(args,old_antrev,feedrev)
        add_new_parts(args,new_antrev,new_mfg_number,feedrev)
        stop_previous_connections(args, handling, statrev, old_antrev, feedrev, do_C7)
        add_new_connections(args, connect, statrev, new_antrev, feedrev, do_C7)
