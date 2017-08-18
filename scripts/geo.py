#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location (via geo_handling)

"""
from __future__ import absolute_import, division, print_function
from hera_mc import mc, geo_handling, cm_utils, cm_hookup, part_connect

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  geo, find, cofa, corr, since, info", default='geo')

    parser.add_argument('-l', '--loc', help="Location name", default=None)
    parser.add_argument('-g', '--graph', help="Graph station types [False]", action='store_true')
    cm_utils.add_verbosity_args(parser)
    cm_utils.add_date_time_args(parser)
    parser.add_argument('-x', '--xgraph', help="X-axis of graph. [E]",
                        choices=['N', 'n', 'E', 'e', 'Z', 'z'], default='E')
    parser.add_argument('-y', '--ygraph', help="Y-axis of graph. [N]",
                        choices=['N', 'n', 'E', 'e', 'Z', 'z'], default='N')
    parser.add_argument('-t', '--station-types', help="Station types used for input (csv_list or all) [HH]",
                        dest='station_types', default='HH')
    parser.add_argument('--show-state', help="Show only the 'active' stations or all [all]", dest='show_state',
                        default='all')
    parser.add_argument('--show-label', dest='show_label',
                        help="Label by station_name (name), ant_num (num) or serial_num (ser) or false [num]",
                        default='num')
    parser.add_argument('--fig-num', help="Provide a specific figure number to the plot [default]",
                        dest='fig_num', default='default')

    # database arguments
    parser.add_argument('--update', help="Update station records.  Format station0:col0:val0, [station1:]col1:val1...  [None]",
                        default=None)
    parser.add_argument('--add-new-geo', help="Flag to enable adding of a new "
                        "geo_location under update.  [False]", action='store_true')
    args = parser.parse_args()
    args.action = args.action.lower()[:3]

    if args.action == 'inf':
        print(
            """
        Available actions are (only need first tree letters) [geo]:
        """
        )
        sys.exit()

    # interpret args
    at_date = cm_utils._get_astropytime(args.date, args.time)
    if isinstance(args.loc, str) and ',' in args.loc:
        args.loc = args.loc.split(',')
    elif args.loc is not None:
        args.loc = [str(args.loc)]
    if ',' in args.station_types:
        args.station_types = args.station_types.split(',')
    else:
        args.station_types = [args.station_types]
    args.show_label = args.show_label.lower()
    if args.show_label == 'false':
        args.show_label = False
    if args.fig_num.lower() == 'default':
        args.fig_num = args.xgraph + args.ygraph
    show_fig = False

    # package up state to dictionary
    state_args = {'verbosity': args.verbosity.lower(),
                  'xgraph': args.xgraph.upper(),
                  'ygraph': args.ygraph.upper(),
                  'station_types': args.station_types,
                  'show_state': args.show_state.lower(),
                  'show_label': args.show_label,
                  'fig_num': args.fig_num}

    # process and start
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    h = geo_handling.Handling(session)
    hu = cm_hookup.Hookup(session)

    # Process action
    if args.action == 'geo' or args.graph:   # Go ahead and show
        show_fig = h.plot_station_types(at_date, state_args)
    if args.action == 'cof':
        cofa = h.cofa(show_cofa=True)
    elif args.action == 'fin':
        located = h.get_location(args.loc, at_date, show_location=True,
                                 verbosity=state_args['verbosity'])
        if args.graph and len(located) > 0:
            state_args['marker_size'] = 14
            h.overplot(located, state_args)
    elif args.action == 'cor' and isinstance(args.loc, list):
        for a2f in args.loc:
            h.get_fully_connected_location_at_date(self, a2f, at_date, hookup, fc=None,
                                                   full_req=part_connect.full_connection_parts_paper)
            print("Correlator inputs for {}:".format(a2f))
            for c in corin:
                print('\t' + c)
    elif args.action == 'cor':
        fully_connected = h.get_all_fully_connected_at_date(at_date)
        for fc in fully_connected:
            print("Station {} connected to x:{}, y:{}".format(fc['station_name'],
                  fc['correlator_input_x'], fc['correlator_input_y']))
    elif args.action == 'sin':
        new_antennas = h.get_ants_installed_since(query_date, state_args['background'])
        print("{} new antennas since {}".format(len(new_antennas), query_date))
        if len(new_antennas) > 0:
            s = ''
            for na in new_antennas:
                s += na + ', '
            s = s.strip().strip(',') + '\n'
            print(s)
            state_args['marker_color'] = 'b'
            state_args['marker_shape'] = '*'
            state_args['marker_size'] = 14
            show_fig = h.plot_stations(new_antennas, query_date, state_args)
    if show_fig:
        geo_handling.show_it_now(show_fig)
    h.close()

    if args.update:
        you_are_sure = cm_utils._query_yn("Warning:  Update is best done via a \
                                           script -- are you sure you want to do this? ", 'n')
        if you_are_sure:
            geo_location.update(args, data)
