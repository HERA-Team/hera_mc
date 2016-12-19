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
    if args.feed_number == None:
        args.feed_number = raw_input('PAPER antenna number being moved:  ')
    if args.station_name == None:
        args.station_name = raw_input('Station name where it is going:  ').upper()

    args.date = cm_utils._query_default('date',args)
    return args

def connection_OK_to_add(args,checking):
    #Check to see if feed_number part is present/active (should be)
    #Check to see if connection is active (should be) and deactivate 
    OK = True
    current = cm_utils._get_datetime(args.date,args.time)
    if checking.get_connection(args,connect._up,connect._up_rev,exact_match=True,show_connection=False):
        print('Error: ',connect._up,"already connected.")
        OK = False
    print("PAPER feed was previously at: ")
    c=checking.is_in_connections_db(args,connect._hpn,connect._hpn_rev,active=True)
    for k in c.keys():
        for l in c[k].keys():
            print(k,l,'\t\t',c[k][l])
    if len(c.keys()) == 0:
        print('Error:  ',connect._hpn,'not present')
        OK = False
    elif len(c.keys()) > 1:
        print('Error:  too many connections returned.')
        OK = False
    else:  #Found the one, so need to add stop_date to it (deactive)
        k = c.keys()[0]
        if len(c[k]['up_parts']>1):
            print("Shouldn't get here.")
            OK = False
        else:
            print("Stopping previous connection.")
            i = 0
            data = [
                    [cm_utils._pull_out_component(c[k]['up_parts'],i),
                     cm_utils._pull_out_component(c[k]['up_rev'],i),
                     cm_utils._pull_out_component(c[k]['down_parts'],i),
                     cm_utils._pull_out_component(c[k]['down_rev'],i),
                     cm_utils._pull_out_component(c[k]['b_on_up'],i),
                     cm_utils._pull_out_component(c[k]['a_on_down'],i),
                     cm_utils._pull_out_component(c[k]['start_on_up'],i),
                     'stop_date', datetime] ]
            part_connect.update_connection(args,data)
                 
    return OK

def add_connection(args,c):
    ###NotNull
    data = [[up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'up',c._up],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'up_rev',c._up_rev],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'down',c._down],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'down_rev',c._down_rev],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'b_on_up',c._b_on_up],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'a_on_down',c._a_on_down],
            [up,up_rev,down,down_rev,b_on_up,a_on_down,dt,'start_date',c._start_date]]
    part_connect.update_connection(args,data)

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-f','--feed_number', help="PAPER feed number", default=None)
    parser.add_argument('-s','--station_name', help="Name of station (HH# for hera)", default=None)
    parser.add_argument('--date', help="MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="hh:mm or now [now]", default='now')
    parser.add_argument('-v', '--verbosity', help="Set verbosity. [h].", choices=['l','m','h'], default="h")
    parser.add_argument('--add_new_connection', help="Flag to allow update to add a new record.  [True]", action='store_false')
    parser.add_argument('--active',help="Need [True]",action='store_false')
    parser.add_argument('--specify_port',help="Need [True]",default='all')

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
    args.feed_number = 'A'+args.feed_number

    connect = part_handling.PartsAndConnections(hpn=args.feed_number, hpn_rev='A',
                                                up=args.station_name, up_rev='A',
                                                down=args.feed_number,down_rev='A',
                                                b_on_up='ground',a_on_down='ground',
                                                start_date=cm_utils._get_datetime(args.date,args.time))
    connection_OK_to_add(args,connect)
    if connection_OK_to_add(args,connect):
        print("Adding new connection")
        add_connection(args,connect)



