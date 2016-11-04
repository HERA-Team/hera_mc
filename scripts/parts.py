#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for parts and connections

"""
from __future__ import absolute_import, division, print_function

from hera_mc import part_connect, mc
import geo

import copy

#Pass part using a dictionary with a superset of part data:
#   {hpn, hptype, manufacturer_number, manufacture_date, short_description, portA[name(s)], portB[name(s)], geo[E,N,z,station,subarray]}
#Pass connections by using a dictionary of lists:
#   {A[name(s)], port_on_A[name(s)], start_on_A[time(s)], stop_on_A[time(s)],
#    B[name(s)], port_on_B[name(s)], start_on_B[time(s)], stop_on_B[time(s)]}

def get_part(args,show_part=False):
    """Return information on a part as contained in args.hpn.  It should find only one.
       """
    partDict = {}
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for part in session.query(part_connect.Parts).filter(part_connect.Parts.hpn==args.hpn):
            partrepr = part.__repr__()
            partDict = {'0hpn':part.hpn, '1hptype':part.hptype, 
                        '2manufacturer_number':part.manufacturer_number, 
                        '3manufacture_date':part.manufacture_date}
            for part_info in session.query(part_connect.PartInfo).filter(part_connect.PartInfo.hpn==args.hpn):
                partDict['4short_description'] = part_info.short_description
            if part.hptype=='station':
                sub_arrays = geo.split_arrays(args)
                args.locate = args.hpn
                partDict['5geo'] = geo.locate_station(args,sub_arrays,show_geo=False)
    if show_part:
        if args.verbosity=='m' or args.verbosity=='h':
            print(partDict)
        else:
            print(partrepr)
    return partDict
def get_connections(args,show_connections=False):
    """Return information on parts connected to args.connection -- NEED TO INCLUDE USING START/STOP_TIME!!!
       It should get connections immediately adjacent to one part (upstream and downstream).
       """
    connectionDict = {}
    part = args.connection
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for connection in session.query(part_connect.Connections).filter(part_connect.Connections.a.like(part+'%')):
            if show_connections:
                if args.verbosity=='m' or args.verbosity=='h':
                    print(connection)
                    args.hpn = connection.b
                    show_part(args)
                else:
                    print(connection)
        for connection in session.query(part_connect.Connections).filter(part_connect.Connections.b.like(part+'%')):
            if show_connections:
                if args.verbosity=='m' or args.verbosity=='h':
                    print(connection)
                    args.hpn = connection.a
                    show_part(args)
                else:
                    print(connection)

if __name__=='__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-p','--hpn',help="Graph data of all elements (per xgraph, ygraph args)",default=None)
    parser.add_argument('-v','--verbosity',help="Set verbosity {l,m,h} [m].",default="m")
    parser.add_argument('-c','--connection',help="Show all connections directly to a part",default=None)
    parser.add_argument('-m','--mapr',help="Show full hookup chains (see --define_hookup and --show_levels)",default=None)
    parser.add_argument('--define_hookup',help="Define the displayed hookup parts/connections (see default for format)",
                         default='station:dish:cable_receiverin_:cable_container:f_engine')
    parser.add_argument('--show_levels',help='show power levels if enabled (and able)',action='store_true')
    args = parser.parse_args()
    if args.hpn:
        args.hpn = args.hpn.upper()
        get_part(args,show_part=True)
    if args.connection:
        args.connection = args.connection.upper()
        get_connections(args,show_connections=True)
    if args.mapr:
        print('Working on it.')

