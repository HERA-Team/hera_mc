#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for handling parts and connections

"""
from __future__ import absolute_import, division, print_function

from hera_mc import part_connect, mc, part_handling
import geo

if __name__=='__main__':
    handling = part_handling.PartsAndConnections()
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
        part_dict = handling.get_part(args,show_part=True)
    if args.connection:
        args.connection = args.connection.upper()
        connection_dict = handling.get_connection(args,show_connection=True)
    if args.mapr:
        args.mapr = args.mapr.upper()
        hookup_dict = handling.get_hookup(args,show_hookup=True)

