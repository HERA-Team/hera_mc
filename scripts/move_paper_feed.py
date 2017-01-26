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
            args.serial_number = 'SN' + args.serial_number
    args.date = cm_utils._query_default('date', args)
    return args


def OK_to_add(args, connect, handling):
    # 1 - check to see if station is in geo_location database (should be)
    OK = True
    if not geo_location.is_in_geo_location(args, connect.upstream_part):
        print("You need to add station", connect.upstream_part, "to geo_location database")
        return False
    # 2 - check to see if the station is already connected (shouldn't be)
    current = cm_utils._get_datetime(args.date, args.time)
    if handling.is_in_connections(connect.upstream_part, connect.up_part_rev, check_if_active=True):
        print('Error: ', connect.upstream_part, "already connected.")
        return False
    # 3 - check to see if antenna is already connected (should be)
    c = handling.is_in_connections(connect.downstream_part, connect.down_part_rev, check_if_active=True)
    if type(c) == dict:  # Found the one but check if unique
        k = c.keys()[0]
        if len(c[k]['input_ports']) > 1:
            print("Number of input_ports should be 1.")
            OK = False
    else:
        print('Error:  ', connect.downstream_part, 'not present')
        OK = False
    return OK


def stop_previous_connections(args, hookup, handling):
    """This adds stop times to the previous PAPER connections between:
           station and antenna
           antenna and feed"""
    args.add_new_connection = False  # Need to temporarily disable add_new
    old_station_name = hookup[1][0]
    c = handling.is_in_connections(old_station_name, check_if_active=True)
    k = c.keys()[0]
    print(c)
    i=0
    data = [[old_station_name, cm_utils._pull_out_component(c[k]['up_rev'],i),
             args.antenna_number, 'A',
             cm_utils._pull_out_component(c[k]['upstream_output_port'], i),
             'ground',
             cm_utils._pull_out_component(c[k]['start_on_up'], i),
             'stop_date', args.date]]
    print(data)
    #part_connect.update_connection(args, data)
    #args.add_new_connection = True


def stop_previous_parts(args):
    """This adds stop times to the previously connected parts:
           previous station
           version A of antenna (version B is HERA)"""
    print("Closing previous station as a part:  ", old_station_name)
    data = [[old_station_name, old_station_rev, 'stop_date', current]]
    args.add_new_part = False
    part_connect.update_part(args, data)



def add_connection(args, c):
    dt = c.start_date
    data = [[c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, dt,
             'upstream_part', c.upstream_part],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, dt,
             'up_part_rev', c.up_part_rev],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, dt,
             'downstream_part', c.downstream_part],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, dt,
             'down_part_rev', c.down_part_rev],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, dt,
             'upstream_output_port', c.upstream_output_port],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, dt,
             'downstream_input_port', c.downstream_input_port],
            [c.upstream_part, c.up_part_rev, c.downstream_part, c.down_part_rev,
             c.upstream_output_port, c.downstream_input_port, dt,
             'start_date', c.start_date]]
    part_connect.update_connection(args, data)


def add_part(args, p):
    dt = p.start_date

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
    args.revision = 'LAST'
    args.show_levels = False
    args.mapr_cols = 'all'
    
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
    print("Trying to connect", connect)
    if OK_to_add(args, connect, handling):
        cm_utils._log('move_paper_feed', args=args)
        print("Stopping previous antenna hookup.")
        previous_hookup = handling.get_hookup(args.antenna_number,show_hookup=True)
        ph_keys = previous_hookup.keys()
        if previous_hookup is None or len(ph_keys)>2:
            print("Invalid hookup.")
            sys.exit()
        for k in ph_keys:
            if k!='columns':
                break
        stop_previous_connections(args, previous_hookup[k],handling)
        #stop_previous_parts(args,previous_hookup[k],handling)
        # add_part_new_antenna_rev_B(args, connect)  # Antenna rev B
        # connect.connection(upstream_part=args.station_name, up_part_rev='A',
        #                    downstream_part=args.antenna_number, down_part_rev='B',
        #                    upstream_output_port='ground', downstream_input_port='ground',
        #                    start_date=cm_utils._get_datetime(args.date, args.time))
        # connect.connection(upstream_part=args.station_name, up_part_rev='A',
        #                    downstream_part=args.antenna_number, down_part_rev='B',
        #                    upstream_output_port='ground', downstream_input_port='ground',
        #                    start_date=cm_utils._get_datetime(args.date, args.time))
        # add_connection(args, connect)
        # add_connection_antenna_feed(args, connect)
