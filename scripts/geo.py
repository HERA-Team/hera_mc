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
    parser.add_argument('action', nargs='?', help="Actions are:  geo, cofa, corr, since, update, info", default='geo')

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
    parser.add_argument('--show-state', help="Show only the 'active' stations or 'all' ['all']", dest='show_state',
                        choices=['active', 'all'], default='all')
    parser.add_argument('--show-label', dest='show_label',
                        help="Label by station_name (name), ant_num (num) or serial_num (ser) or false [num]",
                        choices=['name', 'num', 'ser'], default='num')
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
        See geo.py -h for all arguments.  This information summarizes the actions.
        Available actions are (only need first three letters) [geo]:
            geo:  This has several possibilities, depending on the arguments --loc (-l) and --graph (-g)
                  It is the default action, so not including this positional argument sets the action to geo.
                geo.py [geo] --loc(-l) HPN           will list location information on part HPN
                geo.py [geo] --loc(-l) --graph(-g)   will list and plot, with "background" locations
                                                     from --station-types
                geo.py [geo] [--graph(-g)]           will just make the "background" plot (i.e. just typing
                                                     geo.py will do this).

            cofa:  Provides info on the center of the array
                geo.py cofa              will provide the cofa information
                geo.py cofa --graph(-g)  will plot cofa with "background" set in --station-types

            corr:  Provides information on the correlator hookups.
                geo.py corr:  will provide a list of correlator inputs for stations in --station-types
                geo.py corr --loc(-l)              will provide the correlator input for --loc
                geo.py corr --loc(-l) --graph(-g)  will provide/plot correlator info for --loc

            since: Provides a list of all antennas installed --since DATE
                 geo.py since --date DATE             will provide a list of all antennas built --since DATE
                 geo.py since --date DATE --graph(-g)  will provide a list/plot those antennas

            info:  Print this information and exit.
                geo.py info
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

    # start session and instances
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    h = geo_handling.Handling(session)

    # Process action.  Actions are:  geo, cofa, corr, since, info
    if args.action == 'geo':
        if args.graph:
            show_fig = h.plot_station_types(at_date, state_args)
        if args.loc is not None:
            located = h.get_location(args.loc, at_date)
            h.print_loc_info(located, args.verbosity)
            if args.graph and len(located) > 0:
                state_args['marker_color'] = 'g'
                state_args['marker_shape'] = '*'
                state_args['marker_size'] = 14
                show_fig = h.plot_stations(args.loc, at_date, state_args)

    elif args.action == 'cof':
        cofa = h.cofa(show_cofa=True)
        h.print_loc_info(cofa, args.verbosity)
        if args.graph:
            show_fig = h.plot_station_types(at_date, state_args)
            state_args['marker_color'] = 'g'
            state_args['marker_shape'] = '*'
            state_args['marker_size'] = 14
            show_fig = h.plot_stations(cofa, at_date, state_args)

    elif args.action == 'cor':
        from hera_mc import cm_hookup
        hookup = cm_hookup.Hookup(session)
        if isinstance(args.loc, list):
            for a2f in args.loc:
                c = h.get_fully_connected_location_at_date(a2f, at_date, hookup, fc=None,
                                                           full_req=part_connect.full_connection_parts_paper)
                print("Correlator inputs for {}:  x:{}, y:{}".format(a2f, c['correlator_input_x'], c['correlator_input_y']))
        else:
            fully_connected = h.get_all_fully_connected_at_date(at_date)
            for fv in fully_connected:
                print("Station {} connected to x:{}, y:{}".format(fv['station_name'],
                      fv['correlator_input_x'], fv['correlator_input_y']))

    elif args.action == 'sin':
        new_antennas = h.get_ants_installed_since(at_date, state_args['station_types'])
        print("{} new antennas since {}".format(len(new_antennas), at_date))
        if len(new_antennas) > 0:
            s = ''
            for na in new_antennas:
                s += na + ', '
            s = s.strip().strip(',') + '\n'
            print(s)
            if args.graph:
                show_fig = h.plot_station_types('now', state_args)
                state_args['marker_color'] = 'b'
                state_args['marker_shape'] = '*'
                state_args['marker_size'] = 14
                show_fig = h.plot_stations(new_antennas, 'now', state_args)

    elif args.update:
        you_are_sure = cm_utils._query_yn("Warning:  Update is best done via a \
                                           script -- are you sure you want to do this? ", 'n')
        if you_are_sure:
            geo_location.update(session, data, args.add_new_geo)

    if show_fig:
        geo_handling.show_it_now(show_fig)
    h.close()
