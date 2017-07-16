#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle the ONE TIME renumbering of HERA dishes.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling, geo_handling, cm_hookup, cm_part_revisions
import sys
import copy


def query_renumber(args):
    """
    Gets renumber information from user
    """
    if args.station_name == None:
        args.station_name = raw_input('Station name for which to renumber:  ')
    args.date = cm_utils._query_default('date', args)
    return args


def stop_previous_parts(args,antrev,feedrev):
    """This adds stop times to the previous parts"""
    current = int(args.date.gps)
    args.add_new_part = False

    print("Stopping part %s %s at %s" % (antrev[0], antrev[1], str(args.date)))
    data = [[antrev[0], antrev[1], 'stop_gpstime', current]]
    
    if feedrev[1] == 'A':
        print("Stopping part %s %s at %s" % (feedrev[0], feedrev[1], str(args.date)))
        data.append([feedrev[0], feedrev[1], 'stop_gpstime', current])

    print(data)
    #part_connect.update_part(args, data)


def add_new_parts(args,antrev,mfgna,feedrev):
    """This adds the new rev B antenna and FDA rev B"""
    current = int(args.date.gps)
    args.add_new_part = True

    print("Adding part %s %s at %s" % (antrev[0], antrev[1], str(args.date)))
    data =     [[antrev[0], antrev[1], 'hpn', antrev[0]]]
    data.append([antrev[0], antrev[1], 'hpn_rev', antrev[1]])
    data.append([antrev[0], antrev[1], 'hptype', 'antenna'])
    data.append([antrev[0], antrev[1], 'manufacturer_number', mfgna])
    data.append([antrev[0], antrev[1], 'start_gpstime', current])

    if feedrev[1] == 'A':
        mfgnf = get_mfg_number(feedrev)
        print("Adding part %s %s at %s" % (feedrev[0], 'B', str(args.date)))
        data.append([feedrev[0], 'B', 'hpn', feedrev[0]])
        data.append([feedrev[0], 'B', 'hpn_rev', 'B'])
        data.append([feedrev[0], 'B', 'hptype', 'feed'])
        data.append([feedrev[0], 'B', 'manufacturer_number', mfgnf])
        data.append([feedrev[0], 'B', 'start_gpstime', current])

    print(data)
    #part_connect.update_part(args, data)

def verbose_previous_hookup(previous_hookup):
    for pk in previous_hookup.keys():
        if pk !='columns':
            for i,a in enumerate(previous_hookup[pk]):
                print('\t',previous_hookup['columns'][i],':  ',a.upstream_part,a.up_part_rev)

def stop_previous_connections(args, handling, connect, previous_hookup, srev, arev, frev):
    """This adds stop times to the previous connections between:
           station and antenna rev A
           antenna revA and feed rev A
           feed rev A and frontend
    """

    current = int(args.date.gps)
    data = []
    args.add_new_connection = False
    HHXAY = handling.get_connections(srev[0],srev[1],'ground',True)
    for ck in HHXAY.keys():
        if srev[0] in ck:
            break
    gps = HHXAY[ck].start_gpstime
    connect.connection(upstream_part=srev[0],           up_part_rev=srev[1],
                       downstream_part=arev[0],         down_part_rev=arev[1],
                       upstream_output_port='terminals', downstream_input_port='input',
                       start_gpstime=gps,
                       stop_gpstime=None)
    print("Stopping connection ", c)
    station_connection = [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                          c.upstream_output_port, c.downstream_input_port, c.start_gpstime,
                         'stop_date', current]
    data.append(station_connection)


    print(data)
    #part_connect.update_connection(args, data)


def add_new_connection(args, c):
    # Add the provided new connection c
    print("Adding ", c)
    args.add_new_connection = True
    data = [[c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_date,
             'upstream_part', c.upstream_part],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_date,
             'up_part_rev', c.up_part_rev],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_date,
             'downstream_part', c.downstream_part],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_date,
             'down_part_rev', c.down_part_rev],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_date,
             'upstream_output_port', c.upstream_output_port],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_date,
             'downstream_input_port', c.downstream_input_port],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, c.start_date,
             'start_date', c.start_date]]
    print(data)
    #part_connect.update_connection(args, data)

def get_mfg_number(hrev):
    full_part = handling.get_part(hrev[0],hrev[1])
    if len(full_part.keys())>1:
        print("Too many parts for old rev:  ",hrev)
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
    parser.add_argument('-s', '--station_name', help="Name of station (HH# for hera)", default=None)
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    args.verbosity = args.verbosity.lower()
    args.date = cm_utils._get_datetime(args.date)

    # Add extra args needed for various things
    args.add_new_connection = True
    args.active = True
    args.specify_port = 'all'
    args.revision = 'A'
    args.show_levels = False
    args.mapr_cols = 'all'
    args.exact_match = True

    if len(sys.argv) == 1 or args.station_name is None:
        query = True
    else:
        query = False

    if query:
        args = query_renumber(args)
    args.station_name = args.station_name.upper()
    if args.station_name[0] != 'H':
        args.station_name = 'HH' + args.station_name
    statrev = (args.station_name,cm_part_revisions.get_last_revision(args,args.station_name)[0][0])

    connect = part_connect.Connections()
    geo = geo_handling.Handling(args)
    part = part_connect.Parts()
    handling = cm_handling.Handling(args)
    hookup = cm_hookup.Hookup(args)

    old_antrev = geo.is_in_connections(args.station_name,args.date,True)
    new_mfg_number = get_mfg_number(old_antrev)
    new_antrev = ('A' + args.station_name[2:], 'H')
    previous_hookup = hookup.get_hookup(old_antrev[0], old_antrev[1], show_hookup=True)
    verbose_previous_hookup(previous_hookup)
    
    if isinstance(old_antrev,tuple):
        print('Converting {}:{} to {}:{}'.format(old_antrev[0],old_antrev[1],new_antrev[0],new_antrev[1]))
        feedrev = get_feed(previous_hookup)
        if feedrev[1] == 'A':
            print('H19 - wonky feed cage, but assuming it will get replaced.')

        stop_previous_parts(args,old_antrev,feedrev)
        add_new_parts(args,new_antrev,new_mfg_number,feedrev)
        stop_previous_connections(args, handling, connect, previous_hookup, statrev, old_antrev, feedrev)
    #     # Connection is set above to be checked by OK_to_add
    #     add_new_connection(args, connect)
    #     # Adding new antenna/feed connection
    #     feed = 'FD' + args.antenna_number

    #     add_new_connection(args, connect)
    #     # Adding new feed/frontend connection
    #     frontend = 'FE' + args.antenna_number

    #     add_new_connection(args, connect)
