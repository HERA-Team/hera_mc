#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location (via geo_handling)

"""
from __future__ import absolute_import, division, print_function
from hera_mc import mc, geo_handling, cm_utils, part_connect
import sys

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  geo, cofa, since", default='geo')
    parser.add_argument('-p', '--position', help="Position (i.e. station) name", default=None)
    parser.add_argument('-g', '--graph', help="Graph station types [False]", action='store_true')
    cm_utils.add_date_time_args(parser)
    parser.add_argument('-x', '--xgraph', help="X-axis of graph. [E]",
                        choices=['N', 'n', 'E', 'e', 'Z', 'z'], default='E')
    parser.add_argument('-y', '--ygraph', help="Y-axis of graph. [N]",
                        choices=['N', 'n', 'E', 'e', 'Z', 'z'], default='N')
    parser.add_argument('-t', '--station-types', help="Station types used for input (csv_list or 'all') Can use types or prefixes.  [HH, HA, HB]",
                        dest='station_types', default=['HH', 'HA', 'HB'])
    parser.add_argument('--show-state', help="Show only the 'active' stations or 'all' ['all']", dest='show_state',
                        choices=['active', 'all'], default='all')
    parser.add_argument('--show-label', dest='show_label',
                        help="Label by station_name (name), ant_num (num) or serial_num (ser) or false [num]",
                        choices=['name', 'num', 'ser', 'false'], default='num')
    args = parser.parse_args()
    args.action = args.action.lower()[:3]

    # interpret args
    at_date = cm_utils.get_astropytime(args.date, args.time)
    args.position = cm_utils.listify(args.position)
    args.station_types = cm_utils.listify(args.station_types)
    args.show_label = args.show_label.lower()
    if args.show_label.lower() == 'false':
        args.show_label = False
    show_fig = False
    xgraph = args.xgraph.upper()
    ygraph = args.ygraph.upper()
    show_state = args.show_state.lower()
    if args.action == 'sin':
        cutoff = at_date
        at_date = cm_utils.get_astropytime('now')

    # start session and instances
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    G = geo_handling.Handling(session)

    # If args.graph is set, you will always have this "background"
    if args.graph:
        show_fig = G.plot_station_types(query_date=at_date, station_types_to_use=args.station_types,
                                        xgraph=xgraph, ygraph=ygraph,
                                        show_state=show_state, show_label=args.show_label)
    # Process action.  Actions are:  geo, cofa, corr, since, info
    if args.action == 'geo' and args.position is not None:
        located = G.get_location(args.position, at_date)
        G.print_loc_info(located)
        if args.graph and len(located) > 0:
            G.plot_stations(args.position, at_date, xgraph=xgraph, ygraph=ygraph, show_label=args.show_label,
                            marker_color='k', marker_shape='*', marker_size=14)
    elif args.action == 'cof':
        cofa = G.cofa()
        G.print_loc_info(cofa)
        if args.graph:
            G.plot_stations([cofa[0].station_name], at_date, xgraph=xgraph, ygraph=ygraph, show_label='name',
                            marker_color='k', marker_shape='*', marker_size=14)
    elif args.action == 'sin':
        new_antennas = G.get_ants_installed_since(cutoff, args.station_types)
        print("{} new antennas since {}".format(len(new_antennas), cutoff))
        if len(new_antennas) > 0:
            s = ''
            for na in new_antennas:
                s += na + ', '
            s = s.strip().strip(',') + '\n'
            print(s)
            if args.graph:
                G.plot_stations(new_antennas, at_date, xgraph=xgraph, ygraph=ygraph, show_label=args.show_label,
                                marker_color='b', marker_shape='*', marker_size=14)

    if show_fig:
        geo_handling.show_it_now(show_fig)
    G.close()
