#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle installing a new station into system.  All parameters are part of args.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, part_handling
import sys

def query_connection(args):
    """
    Gets connection information from user
    """
    if args.station_name == None:
        args.station_name = raw_input('Station name:  ').upper()
    if args.feed_number == None:
        args.from_file = raw_input('Feed number:  ')
    args.date = cm_utils._query_default('date',args)
    return args

def connection_OK_to_modify(args):
    #Check to see if feed_number part is present/active (should be)
    #Check to see if connection is active (should be) and deactivate (part_handling.deactivate_connection)
    # ?
    OK = True
    if deactivate:
        part_handling.deactivate_connection(args,XXX)
    if geo_location.is_station_present(args,args.station_name):
        print(args.station_name,' already present.')
        OK = False
    return OK

def modify_connections(args):
    ###NotNull
    up = args.station_name
    up_rev= 'A'
    down = args.feed_number
    down_rev= 'A'
    b_on_up = 'ground'
    a_on_down = 'ground'
    dt = cm_utils._get_datetime(args.date,args.time)
    data = [[up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'up',up],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'up_rev',up_rev],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'down',down],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'down_rev',down_rev],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'b_on_up',b_on_up],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'a_on_down',a_on_down],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'start_date',dt]]

    part_connect.update_connection(args,data)

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-f','--feed_number', help="PAPER feed number", default=None)
    parser.add_argument('-s','--station_name', help="Name of station (HH# for hera)", default=None)
    parser.add_argument('--date', help="MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="hh:mm or now [now]", default='now')
    parser.add_argument('-v', '--verbosity', help="Set verbosity. [h].", choices=['l','m','h'], default="h")
    parser.add_argument('--add_new_connection', help="Flag to allow update to add a new record.  [True]", action='store_false')

    args = parser.parse_args()
    args.verbosity = args.verbosity.lower()
    if len(sys.argv)==1:
        query = True
    elif args.feed_number==None or args.station_name==None:
        query = True
    else:
        query = False

    if query:
        args = query_connection(args)

    if connection_OK_to_modify(args):
        modify_connection(args)


def get_part_information(args,install):
    """
    Gets part information from user and database and calls correct part-type installation
    """
    part_types = install.get_part_types(args,False)
    tmp_hpn = args.hpn
    args.hpn = 'HH23'
    print("Here is an example hookup")
    install.get_hookup(args,show_hookup=True)
    args.hpn = tmp.hpn
    args.hptype = raw_input("What is the part type?  ")
    try:
        aports = part_types[args.hptype]['a_ports']
        bports = part_types[args.hptype]['b_ports']
    except KeyError:
        print('\nError:  ',args.hptype,'not valid part type -- look again at the list\n')
        install.get_part_types(args,True)
        print()
        sys.exit()

    new_or_replace = raw_input("Is this a 'n'ew or 'r'eplacement part (n/r)?  ").lower()
    args.hpn = raw_input("What is the hera part number?  ")
    args.hpn = args.hpn.upper()
    print(args.hptype," part type has the following ports:  ")
    print("\tA ports:  ",end='')
    for a in aports:
        print(a,end='    ',sep='not working for some reason')
    print("\n\tB ports:  ",end='')
    for b in bports:
        print(b,end='    ',sep='not working for some reason')
    print()

    
    #art_dict = handling.get_part(args, show_part=True)

