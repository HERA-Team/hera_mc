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
    if args.feed_number == None:
        args.feed_number = raw_input('PAPER antenna number being moved:  ')
    if args.station_name == None:
        args.station_name = raw_input(
            'Station name where it is going:  ').upper()

    args.date = cm_utils._query_default('date', args)
    return args


def check_if_OK_to_add_and_deactivate_previous(args, connect):
    # 1 - check to see if station is in geo_location database (should be)
    OK = True
    if not geo_location.is_station_present(args, connect.up):
        print("You need to add station", connect.up, "to geo_location database")
        OK = False
    # 2 - check to see if the station is already connected (shouldn't be)
    current = cm_utils._get_datetime(args.date, args.time)
    checking = cm_handling.Handling(args)
    if checking.is_in_connections_db(connect.up, connect.up_rev, check_if_active=True):
        print('Error: ', connect.up, "already connected.")
        OK = False
    # 3 - check to see if feed is already connected (should be)
    c = checking.is_in_connections_db(
        connect.down, connect.down_rev, check_if_active=True)
    if OK:
        if type(c) == dict:  # Found the one, so need to add stop_date to it (deactivate)
            print("PAPER feed was previously at: ")
            checking.show_connection(c)
            k = c.keys()[0]
            if len(c[k]['a_ports']) > 1:
                print("Shouldn't get here.")
                OK = False
            else:
                print("Stopping previous connection.")
                i = 0
                old_station_name = cm_utils._pull_out_component(
                    c[k]['up_parts'], i)
                old_station_rev = cm_utils._pull_out_component(
                    c[k]['up_rev'], i)
                data = [[old_station_name, old_station_rev,
                         args.feed_number, 'A',
                         cm_utils._pull_out_component(c[k]['b_on_up'], i),
                         'ground',
                         cm_utils._pull_out_component(c[k]['start_on_up'], i),
                         'stop_date', current]]
                args.add_new_connection = False  # Need to temporarily disable add_new
                part_connect.update_connection(args, data)
                args.add_new_connection = True
                print("Closing previous station as a part:  ", old_station_name)
                data = [[old_station_name, old_station_rev, 'stop_date', current]]
                args.add_new_part = False
                part_connect.update_part(args, data)

        else:
            print('Error:  ', connect.down, 'not present')
            OK = False
    return OK


def add_connection(args, c):
    dt = c.start_date
    data = [[c.up, c.up_rev, c.down, c.down_rev, c.b_on_up, c.a_on_down, dt, 'up', c.up],
            [c.up, c.up_rev, c.down, c.down_rev, c.b_on_up,
                c.a_on_down, dt, 'up_rev', c.up_rev],
            [c.up, c.up_rev, c.down, c.down_rev, c.b_on_up,
                c.a_on_down, dt, 'down', c.down],
            [c.up, c.up_rev, c.down, c.down_rev, c.b_on_up,
                c.a_on_down, dt, 'down_rev', c.down_rev],
            [c.up, c.up_rev, c.down, c.down_rev, c.b_on_up,
                c.a_on_down, dt, 'b_on_up', c.b_on_up],
            [c.up, c.up_rev, c.down, c.down_rev, c.b_on_up,
                c.a_on_down, dt, 'a_on_down', c.a_on_down],
            [c.up, c.up_rev, c.down, c.down_rev, c.b_on_up, c.a_on_down, dt, 'start_date', c.start_date]]
    part_connect.update_connection(args, data)

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-f', '--feed_number',
                        help="PAPER feed number", default=None)
    parser.add_argument('-s', '--station_name',
                        help="Name of station (HH# for hera)", default=None)
    parser.add_argument('--date', help="MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="hh:mm or now [now]", default='now')
    parser.add_argument(
        '-v', '--verbosity', help="Set verbosity. [h].", choices=['l', 'm', 'h'], default="h")
    parser.add_argument('--add_new_connection',
                        help="Don't change  [True]", action='store_false')
    parser.add_argument(
        '--active', help="Don't change [True]", action='store_false')
    parser.add_argument(
        '--specify_port', help="Don't change [True]", default='all')

    args = parser.parse_args()
    args.verbosity = args.verbosity.lower()
    if len(sys.argv) == 1:
        query = True
    elif args.feed_number == None or args.station_name == None:
        query = True
    else:
        query = False

    if query:
        args = query_connection(args)
    if args.feed_number[0] != 'A':
        args.feed_number = 'A' + args.feed_number
    connect = part_connect.Connections()
    connect.connection(up=args.station_name, up_rev='A',
                       down=args.feed_number, down_rev='A',
                       b_on_up='ground', a_on_down='ground',
                       start_date=cm_utils._get_datetime(args.date, args.time))
    print("Trying", connect)
    if check_if_OK_to_add_and_deactivate_previous(args, connect):
        cm_utils._log('move_paper_feed', args=args)
        print("Adding new connection.")
        add_connection(args, connect)
