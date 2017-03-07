#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location

"""
from __future__ import absolute_import, division, print_function
import datetime
import sys
from hera_mc import mc, geo_handling

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    # action arguments
    parser.add_argument('-c', '--cofa', help="Print out center of array information.", action='store_true')
    parser.add_argument('-l', '--locate',help="Location of given station_name or antenna_number (assumed if <int>).  [None]", default=None)
    parser.add_argument('-g', '--graph', help="Graph station types, list or 'all' [False]", action='store', nargs='?', const='all', default=False)
    parser.add_argument('-s', '--show', help="Show:  shortcut for -g 'hh,ph,s' -l NN [False]", default=False)
    parser.add_argument('-d', '--since_date', help="Show stations set up since date mm/dd/yy [False]", default=False)

    # parameter state arguments
    parser.add_argument('-v', '--verbosity', help="Set verbosity. [m].", choices=['L', 'l', 'm', 'M', 'h', 'H'], default='m')
    parser.add_argument('-x', '--xgraph', help="X-axis of graph. [E]", choices=['N', 'n', 'E', 'e', 'Z', 'z'], default='E')
    parser.add_argument('-y', '--ygraph', help="Y-axis of graph. [N]", choices=['N', 'n', 'E', 'e', 'Z', 'z'], default='N')
    parser.add_argument('--date', help="MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="hh:mm or now [now]", default='now')
    parser.add_argument('--background', help="Station types used for graph with show/since_date ['HH,PH,S']", default='HH,PH,S')
    group_connected = parser.add_mutually_exclusive_group()
    group_connected.add_argument('--show-active', help="Flag to show only the active stations (default)",dest='active', action='store_true')
    group_connected.add_argument('--show-all', help="Flag to show all stations",dest='active', action='store_false')
    group_label = parser.add_mutually_exclusive_group()
    group_label.add_argument('--label', help="Flag to label stations in graph (default).", dest='label', action='store_true')
    group_label.add_argument('--no-label', help="Flag to not label stations in graph.", dest='label', action='store_false')
    group_type_label = parser.add_mutually_exclusive_group()
    group_type_label.add_argument('--show-name', help="Set label_type to station_name", dest='label_type',
                                  action='store_const', const='station_name')
    group_type_label.add_argument('--show-number', help="Set label_type to station_number", dest='label_type',
                                  action='store_const', const='antenna_number')

    # database arguments
    parser.add_argument('-u', '--update',help="Update station records.  Format station0:col0:val0, [station1:]col1:val1...  [None]", default=None)
    parser.add_argument('--add-new-geo', help="Flag to enable adding of a new geo_location under update.  [False]", 
                        dest='add_new_geo', action='store_true')

    # set some defaults and parse it
    parser.set_defaults(label=True, active=True, label_type='antenna_number')
    args = parser.parse_args()

    # fix up some things
    args.xgraph = args.xgraph.upper()
    args.ygraph = args.ygraph.upper()
    args.verbosity = args.verbosity.lower()

    # take action
    # ... setup some stuff
    if args.cofa:
        cofa = geo_handling.cofa(show_cofa=True)
    if args.show:
        args.graph = args.background
        args.locate = args.show
    if args.since_date: #First one before args.graph
        args.graph = args.background
        new_antennas = geo_handling.get_since_date(args)

    # ... graph it if arg'd
    if args.graph:
        fignm = geo_handling.plot_station_types(args,label_station=args.label)

    # ... plot over that if desired
    if args.since_date: #Second one after args.graph
        geo_handling.plot_stations(args,new_antennas,fignm,'b','*','14',label_station = True)
    if args.locate:
        located = geo_handling.locate_station(args, show_location=True)
    if args.graph and args.locate:
        geo_handling.overplot(args,located,fignm)
    if args.graph:
        geo_handling.show_it_now(fignm)

    if args.update:
        you_are_sure = cm_utils._query_yn("Warning:  Update is best done via a script -- are you sure you want to do this? ", 'n')
        if you_are_sure:
            geo_handling.update(args, data)
