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

def show_part(args):
    """Return information on a part as contained in args.hpn  
       """
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for part in session.query(part_connect.Parts).filter(part_connect.Parts.hpn==args.hpn):
            if args.verbosity=='m' or args.verbosity=='h':
                print(part)
                for part_info in session.query(part_connect.PartInfo).filter(part_connect.PartInfo.hpn==args.hpn):
                    print(part_info)
                if part.hptype=='station':
                    sub_arrays = geo.split_arrays(args)
                    args.locate = args.hpn
                    geo.locate_station(args,sub_arrays)
            else:
                print(a)
def show_connections(args):
    """Return information on parts connected to args.connection
       """
    part = args.connection
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        #Seems like or'ing implies doing the queries sequentially...
        for connection in session.query(part_connect.Connections).filter(part_connect.Connections.a.like(part+'%')):
            if args.verbosity=='m' or args.verbosity=='h':
                print(connection)
                args.hpn = connection.b
                show_part(args)
            else:
                print(connection)
        for connection in session.query(part_connect.Connections).filter(part_connect.Connections.b.like(part+'%')):
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
    parser.add_argument('--show_levels',help='show power levels if on (and able)',action='store_true')
    args = parser.parse_args()
    if args.hpn:
        args.hpn = args.hpn.upper()
        show_part(args)
    if args.connection:
        args.connection = args.connection.upper()
        show_connections(args)

