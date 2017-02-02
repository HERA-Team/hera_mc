#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle moving a PAPER feed into HERA hex.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling, geo_location
import sys
import copy


def query_connection(args):
    """
    Gets connection information from user
    """
    if args.antenna_number == None:
        args.antenna_number = raw_input('PAPER antenna number being moved:  ')
    if args.station_name == None:
        args.station_name = raw_input('Station name where it is going:  ').upper()
    if args.serial_number == -1:
        args.serial_number = raw_input("Serial number of HERA station/antenna (use -1 if you don't know):  ")
        if args.serial_number[0] != 'S':
            args.serial_number = 'S/N' + args.serial_number
    args.date = cm_utils._query_default('date', args)
    return args


def OK_to_add(args, connect, handling):
    # 1 - check to see if station is in geo_location database (should be)
    if not geo_location.is_in_geo_location(args, connect.upstream_part):
        print("You need to add station", connect.upstream_part, "to geo_location database")
        return False
    # 2 - check to see if the station is already connected (shouldn't be)
    current = cm_utils._get_datetime(args.date, args.time)
    if handling.is_in_connections(connect.upstream_part, 'A', return_active=True):
        print('Error: ', connect.upstream_part, "already connected.")
        return False
    # 3 - check to see if antenna is already connected (should be)
    c = handling.is_in_connections(connect.downstream_part, 'A', return_active=True)
    if type(c) != list:
        print('Error:  ', connect.downstream_part, 'not present')
        return False
    return True


def stop_previous_antenna_part(args):
    """This adds stop times to the previously connected rev A antenna"""
    current = cm_utils._get_datetime(args.date, args.time)
    print("Stopping part %s %s at %s" % (args.antenna_number, 'A', str(current)))
    data = [[args.antenna_number, 'A', 'stop_date', current]]
    args.add_new_part = False
    part_connect.update_part(args, data)


def add_new_antenna_part(args):
    """This adds the new rev B antenna"""
    current = cm_utils._get_datetime(args.date, args.time)
    print("Adding part %s %s at %s" % (args.antenna_number, 'B', str(current)))
    args.add_new_part = True
    data = [[args.antenna_number, 'B', 'hpn', args.antenna_number]]
    data.append([args.antenna_number, 'B', 'hpn_rev', 'B'])
    data.append([args.antenna_number, 'B', 'hptype', 'antenna'])
    data.append([args.antenna_number, 'B', 'manufacturer_number', args.serial_number])
    data.append([args.antenna_number, 'B', 'start_date', current])
    part_connect.update_part(args, data)


def stop_previous_connections(args, handling):
    """This adds stop times to the previous PAPER connections between:
           station and antenna rev A
           antenna revA and feed rev A"""
    current = cm_utils._get_datetime(args.date, args.time)
    existing = handling.get_connections(args.antenna_number, 'A', exact_match=True)
    data = []
    args.add_new_connection = False  # Need to temporarily disable add_new
    for k, c in existing.iteritems():
        if k in handling.non_class_connections_dict_entries:
            continue
        if c.downstream_part == args.antenna_number and c.down_part_rev == 'A':
            print("Stopping connection ", c)
            data.append([c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                         c.upstream_output_port, c.downstream_input_port, c.start_date,
                         'stop_date', current])
        if c.upstream_part == args.antenna_number and c.up_part_rev == 'A':
            print("Stopping connection ", c)
            feed_connection = [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
                               c.upstream_output_port, c.downstream_input_port, c.start_date,
                               'stop_date', current]
            data.append(feed_connection)
    part_connect.update_connection(args, data)
    return feed_connection


def add_new_connection(args, c):
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
    part_connect.update_connection(args, data)


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-a', '--antenna_number', help="PAPER antenna number", default=None)
    parser.add_argument('-s', '--station_name', help="Name of station (HH# for hera)", default=None)
    parser.add_argument('-n', '--serial_number', help="Serial number of HERA station/antenna", default=-1)
    parser.add_argument('--date', help="MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="hh:mm or now [now]", default='now')
    parser.add_argument('-v', '--verbosity', help="Set verbosity. [h].", choices=['l', 'm', 'h'], default="h")

    args = parser.parse_args()
    args.verbosity = args.verbosity.lower()
    # Add extra args needed for various.
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
    if args.station_name[0] != 'H':
        args.station_name = 'HH' + args.station_name
    if args.antenna_number[0] != 'A':
        args.antenna_number = 'A' + args.antenna_number
    connect = part_connect.Connections()
    part = part_connect.Parts()
    handling = cm_handling.Handling(args)
    connect.connection(upstream_part=args.station_name, up_part_rev='A',
                       downstream_part=args.antenna_number, down_part_rev='B',
                       upstream_output_port='ground', downstream_input_port='ground',
                       start_date=cm_utils._get_datetime(args.date, args.time))
    print("Trying to stop previous antenna hookup.")
    previous_hookup = handling.get_hookup(args.antenna_number, show_hookup=True)
    if OK_to_add(args, connect, handling):
        cm_utils._log('move_paper_feed', args=args)
        stop_previous_antenna_part(args)
        add_new_antenna_part(args)
        fc = stop_previous_connections(args, handling)
        add_new_connection(args, connect)
        connect.connection(upstream_part=fc[0],        up_part_rev='B',
                           downstream_part=fc[2],      down_part_rev=fc[3],
                           upstream_output_port=fc[4], downstream_input_port=fc[5],
                           start_date=cm_utils._get_datetime(args.date, args.time),
                           stop_date=None)
        add_new_connection(args, connect)
