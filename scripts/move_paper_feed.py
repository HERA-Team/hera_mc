#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle moving a PAPER feed into HERA hex.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling, geo_location, cm_hookup
import sys
import copy

def print4test(data,verbosity,comment):
    if verbosity=='h':
        print(comment+'\n')
        for d in data:
            print('\t',d)
    elif verbosity=='m':
        print(comment+'\n')

def query_connection(args):
    """
    Gets connection information from user
    """
    if args.antenna_number == None:
        args.antenna_number = raw_input('PAPER antenna number being moved:  ')
    if args.station_name == None:
        args.station_name = raw_input('Station name where it is going:  ')
    if args.serial_number == -1:
        args.serial_number = raw_input("Serial number of HERA station/antenna (use -1 if you don't know):  ")
        if args.serial_number[0] != 'S':
            args.serial_number = 'S/N' + args.serial_number
    args.date = cm_utils._query_default('date', args)
    return args


def OK_to_add(args, connect, handling):
    is_OK_to_add = True
    # 1 - check to see if station is in geo_location database (should be)
    if not geo_location.is_in_geo_location(args, connect.upstream_part):
        print("You need to add_station.py", connect.upstream_part, "to geo_location database")
        is_OK_to_add = False
    # 2 - check to see if the station is already connected (shouldn't be)
    current = cm_utils._get_datetime(args.date, args.time)
    if handling.is_in_connections(connect.upstream_part, 'A', return_active=True):
        print('Error: ', connect.upstream_part, "already connected.")
        is_OK_to_add = False
    # 3 - check to see if antenna is already connected (should be, but isn't necesarily active)
    is_connected = handling.is_in_connections(connect.downstream_part, 'A', return_active=True)
    if not is_connected:
        print('Error:  ', connect.downstream_part, 'not present')
        is_OK_to_add = False
    if type(is_connected) != list:
        print('Note:',connect.downstream_part,'is connected, but not active.')

    return is_OK_to_add


def stop_previous_parts(args):
    """This adds stop times to the previously connected rev A antenna and FDP rev A"""
    current = cm_utils._get_datetime(args.date, args.time)
    args.add_new_part = False

    print("Stopping part %s %s at %s" % (args.antenna_number, 'A', str(current)))
    data = [[args.antenna_number, 'A', 'stop_date', current]]
    
    feed = 'FDP' + args.antenna_number.strip('A')
    print("Stopping part %s %s at %s" % (feed, 'A', str(current)))
    data.append([feed, 'A', 'stop_date', current])

    if args.make_update:
        part_connect.update_part(args, data)
    else:
        print4test(data,args.verbosity,'Test: stop_previous_parts')


def add_new_parts(args):
    """This adds the new rev B antenna and FDA rev B"""
    current = cm_utils._get_datetime(args.date, args.time)
    args.add_new_part = True

    print("Adding part %s %s at %s" % (args.antenna_number, 'B', str(current)))
    data = [[args.antenna_number, 'B', 'hpn', args.antenna_number]]
    data.append([args.antenna_number, 'B', 'hpn_rev', 'B'])
    data.append([args.antenna_number, 'B', 'hptype', 'antenna'])
    data.append([args.antenna_number, 'B', 'manufacturer_number', args.serial_number])
    data.append([args.antenna_number, 'B', 'start_date', current])

    feed = 'FD'+args.antenna_number
    print("Adding part %s %s at %s" % (feed, 'B', str(current)))
    mfg_number = 'P' + args.antenna_number.strip('A')
    data.append([feed, 'B', 'hpn', feed])
    data.append([feed, 'B', 'hpn_rev', 'B'])
    data.append([feed, 'B', 'hptype', 'feed'])
    data.append([feed, 'B', 'manufacturer_number', mfg_number])
    data.append([feed, 'B', 'start_date', current])

    if args.make_update:
        part_connect.update_part(args, data)
    else:
        print4test(data,args.verbosity,'Test: add_new_parts')


def stop_previous_connections(args, handling):
    """This adds stop times to the previous PAPER connections between:
           station and antenna rev A
           antenna revA and feed rev A
           feed rev A and frontend
    """
    current = cm_utils._get_datetime(args.date, args.time)
    data = []
    args.add_new_connection = False

    existing = handling.get_connections(args.antenna_number, 'A', exact_match=True)
    for k, c in existing.iteritems():
        if k in handling.non_class_connections_dict_entries:
            continue
        if c.downstream_part == args.antenna_number and c.down_part_rev == 'A':
            print("Stopping connection ", c)
            station_connection = [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                                  c.upstream_output_port, c.downstream_input_port, c.start_date,
                                 'stop_date', current]
            data.append(station_connection)
        if c.upstream_part == args.antenna_number and c.up_part_rev == 'A':
            print("Stopping connection ", c)
            feed_connection = [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                               c.upstream_output_port, c.downstream_input_port, c.start_date,
                               'stop_date', current]
            data.append(feed_connection)
    feed = feed_connection[2]
    feed_rev = feed_connection[3]
    existing = handling.get_connections(feed, feed_rev, exact_match=True)
    for k, c in existing.iteritems():
        if k in handling.non_class_connections_dict_entries:
            continue
        if c.upstream_part == feed and c.up_part_rev == feed_rev:
            print("Stopping connection ", c)
            frontend_connection = [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                                   c.upstream_output_port, c.downstream_input_port, c.start_date,
                                   'stop_date', current]
            data.append(frontend_connection)
    if args.make_update:
        part_connect.update_connection(args, data)
    else:
        print4test(data,args.verbosity,'Test: stop_previous_connections')


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
    if args.make_update:
        part_connect.update_connection(args, data)
    else:
        print4test(data,args.verbosity,'Test: add_new_connection')


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-a', '--antenna_number', help="PAPER antenna number", default=None)
    parser.add_argument('-s', '--station_name', help="Name of station (HH# for hera)", default=None)
    parser.add_argument('-n', '--serial_number', help="Serial number of HERA station/antenna", default=-1)
    parser.add_argument('--date', help="MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="hh:mm or now [now]", default='now')
    parser.add_argument('--make-update', help="Set to actually change database (otherwise it just shows).",
                        dest='make_update', action='store_true')
    parser.add_argument('-v', '--verbosity', help="Set verbosity. [h].", choices=['l', 'm', 'h'], default="m")

    args = parser.parse_args()
    args.verbosity = args.verbosity.lower()
    # Add extra args needed for various things
    args.add_new_connection = True
    args.active = True
    args.specify_port = 'all'
    args.revision = 'A'
    args.show_levels = False
    args.mapr_cols = 'all'
    args.exact_match = True

    if len(sys.argv) == 1:
        query = True
    elif args.antenna_number == None or args.station_name == None:
        query = True
    else:
        query = False

    if query:
        args = query_connection(args)
    args.station_name = args.station_name.upper()
    args.antenna_number = args.antenna_number.upper()
    if args.station_name[0] != 'H':
        args.station_name = 'HH' + args.station_name
    if args.antenna_number[0] != 'A':
        args.antenna_number = 'A' + args.antenna_number
    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(args)
    hookup = cm_hookup.Hookup(args)

    if args.make_update:
        print("\nUpdating antenna/feed installation.\n")
    else:
        print("\nThis will only print out the actions.\n\t'--make-update' to actually make changes.\n")

    print("Showing previous hookup:")
    previous_hookup = hookup.get_hookup(args.antenna_number, show_hookup=True)

    # This is the new station/antenna connection to be checked
    connect.connection(upstream_part=args.station_name, up_part_rev='A',
               downstream_part=args.antenna_number, down_part_rev='B',
               upstream_output_port='ground', downstream_input_port='ground',
               start_date=cm_utils._get_datetime(args.date, args.time))
    if OK_to_add(args, connect, handling):
        if args.make_update:
            print("OK to update -- actually doing it.")
            cm_utils._log('move_paper_feed', args=args)
        else:
            print("This is what would be happening if --make-update was enabled:")
        stop_previous_parts(args)
        add_new_parts(args)
        stop_previous_connections(args, handling)
        # Connection is set above to be checked by OK_to_add
        add_new_connection(args, connect)
        # Adding new antenna/feed connection
        feed = 'FD' + args.antenna_number
        connect.connection(upstream_part=args.antenna_number, up_part_rev='B',
                           downstream_part=feed,              down_part_rev='B',
                           upstream_output_port='focus',      downstream_input_port='input',
                           start_date=cm_utils._get_datetime(args.date, args.time),
                           stop_date=None)
        add_new_connection(args, connect)
        # Adding new feed/frontend connection
        frontend = 'FE' + args.antenna_number
        connect.connection(upstream_part=feed,               up_part_rev='B',
                           downstream_part=frontend,         down_part_rev='A',
                           upstream_output_port='terminals', downstream_input_port='input',
                           start_date=cm_utils._get_datetime(args.date, args.time),
                           stop_date=None)
        add_new_connection(args, connect)
