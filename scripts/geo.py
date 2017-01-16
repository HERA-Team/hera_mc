#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location

"""
from __future__ import absolute_import, division, print_function
import datetime
from hera_mc import mc, geo_location

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        '-g', '--graph', help="Graph data of all elements (per xgraph, ygraph args). [False]", action='store_true')
    parser.add_argument(
        '-s', '--show', help="Graph and locate a station (same as geo.py -gl XX). [None]", default=None)
    parser.add_argument('-l', '--locate',
                        help="Location of given station_name or antenna_number (assumed if <int>).  [None]", default=None)
    parser.add_argument('-u', '--update',
                        help="Update station records.  Format station0:col0:val0, [station1:]col1:val1...  [None]", default=None)
    parser.add_argument('-v', '--verbosity', help="Set verbosity. [m].", choices=[
                        'L', 'l', 'm', 'M', 'h', 'H'], default='m')
    parser.add_argument('-x', '--xgraph', help="X-axis of graph. [E]", choices=[
                        'N', 'n', 'E', 'e', 'Z', 'z'], default='E')
    parser.add_argument('-y', '--ygraph', help="Y-axis of graph. [N]", choices=[
                        'N', 'n', 'E', 'e', 'Z', 'z'], default='N')
    parser.add_argument(
        '--add_new_geo', help="Flag to enable adding of a new geo_location under update.  [False]", action='store_true')
    parser.add_argument('--date', help="MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="hh:mm or now [now]", default='now')
    connected_group = parser.add_mutually_exclusive_group()
    connected_group.add_argument('--show-active', help="Flag to show only the active stations (default)",
                                 dest='active', action='store_true')
    connected_group.add_argument('--show-all', help="Flag to show all stations",
                                 dest='active', action='store_false')
    label_group = parser.add_mutually_exclusive_group()
    label_group.add_argument(
        '--label', help="Flag to label stations in graph (default).", dest='label', action='store_true')
    label_group.add_argument(
        '--no-label', help="Flag to not label stations in graph.", dest='label', action='store_false')
    label_type_group = parser.add_mutually_exclusive_group()
    label_type_group.add_argument('--show-name', help="Set label_type to station_name", dest='label_type',
                                  action='store_const', const='station_name')
    label_type_group.add_argument('--show-number', help="Set label_type to station_number", dest='label_type',
                                  action='store_const', const='station_number')
    label_type_group.add_argument(
        '--label_type', help="Use 'station_name' or 'antenna_number' [antenna_number]")
    parser.set_defaults(label=True, active=True, label_type='antenna_number')
    args = parser.parse_args()
    args.xgraph = args.xgraph.upper()
    args.ygraph = args.ygraph.upper()
    args.verbosity = args.verbosity.lower()
    located = None
    if args.update:
        data = geo_location.parse_update_request(args.update)
        geo_location.update(args, data)
    if args.show:
        args.locate = args.show
        args.graph = True
    if args.locate:
        located = geo_location.locate_station(args, show_geo=True)
    if args.graph:
        geo_location.plot_arrays(args, located, label_station=args.label)
