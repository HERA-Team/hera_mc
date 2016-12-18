#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle moving a PAPER feed into HERA hex.
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
        args.feed_number = raw_input('Feed number:  ')
    args.date = cm_utils._query_default('date',args)
    return args

def connection_OK_to_add(args,checking):
    #Check to see if feed_number part is present/active (should be)
    #Check to see if connection is active (should be) and deactivate 
    # ?
    OK = True
    datetime = cm_utils._get_datetime(args.date,args.time)
    ###THIS IS WRONG NEED is_part_connected()
    was_active = checking.is_connection_active(args,datetime,True)

    return OK

def add_connection(args,c):
    ###NotNull
    data = [[up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'up',c.up],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'up_rev',c.up_rev],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'down',c.down],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'down_rev',c.down_rev],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'b_on_up',c.b_on_up],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'a_on_down',c.a_on_down],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'start_date',c.start_date]]
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

    connect = part_handling.PartsAndConnections(up=args.station_name,up_rev='A',
                                                down=args.feed_number,down_rev='A',
              b_on_up='ground',a_on_down='ground',start_date=cm_utils._get_datetime(args.date,args.time))

    if connection_OK_to_add(args,connect):
        add_connection(args,connect)



