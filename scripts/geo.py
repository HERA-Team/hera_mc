#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location

"""
from __future__ import absolute_import, division, print_function

from hera_mc import geo_location, mc

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-g', '--graph', help="Graph data of all elements (per xgraph, ygraph args)", action='store_true')
    parser.add_argument('-s', '--show', help='Graph and locate a station (same as geo.py -gl XX)', default=False)
    parser.add_argument('-l', '--locate', help="Location of given s_name or s_number (assumed if <int>). Prepend with 'h' for HH s_name.", default=False)
    parser.add_argument('-u', '--update', help="Update station records.  Format station0:col0:val0, [station1:]col1:val1...", default=None)
    parser.add_argument('-v', '--verbosity', help="Set verbosity {l, m, h} [m].", default="m")
    parser.add_argument('-x', '--xgraph', help='X-axis of graph {N, E, Z} [E]', default='E')
    parser.add_argument('-y', '--ygraph', help='Y-axis of graph {N, E, Z} [N]', default='N')
    args = parser.parse_args()
    args.xgraph = args.xgraph.upper()
    args.ygraph = args.ygraph.upper()
    located = None
    if args.update:
        data = geo_location.parse_update_request(args.update)
        geo_location.update(args,data)
    if args.show:
        args.locate = args.show
        args.graph = True
    if args.locate:
        args.locate = args.locate.upper()
        located = geo_location.locate_station(args, show_geo=True)
    if args.graph:
        geo_location.plot_arrays(args, located)
