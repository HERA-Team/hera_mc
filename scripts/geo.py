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
    parser.add_argument('action', nargs='?', help="Actions are:  geo, cofa, since, update, info", default='geo')
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

            since: Provides a list of all antennas installed --since DATE
                 geo.py since --date DATE             will provide a list of all antennas built --since DATE
                 geo.py since --date DATE --graph(-g)  will provide a list/plot those antennas

            info:  Print this information and exit.
                geo.py info

        usage: geo.py [-h]
                      [-l LOC] [-g]
                      [-v {l,m,h}]
                      [--date DATE] [--time TIME]
                      [-x {N,n,E,e,Z,z}]
                      [-y {N,n,E,e,Z,z}]
                      [-t STATION_TYPES]
                      [--show-state {active,all}]
                      [--show-label {name,num,ser}]
                      [--fig-num FIG_NUM] [--update UPDATE] [--add-new-geo]
                      [action]

                positional arguments:
                action                Actions are: geo, cofa, since, update, info

                optional arguments:
                -h, --help            show this help message and exit
                -l LOC, --loc LOC     Location name
                -g, --graph           Graph station types [False]
                -v {l,m,h}, --verbosity {l,m,h}
                                    Verbosity level: 'l', 'm', or 'h'. [h].
                --date DATE           UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' [now]
                --time TIME           UTC hh:mm or float (hours)
                -x {N,n,E,e,Z,z}, --xgraph {N,n,E,e,Z,z}
                                    X-axis of graph. [E]
                -y {N,n,E,e,Z,z}, --ygraph {N,n,E,e,Z,z}
                                    Y-axis of graph. [N]
                -t STATION_TYPES, --station-types STATION_TYPES
                                    Station types used for input (csv_list or all) [HH]
                --show-state {active,all}
                                    Show only the 'active' stations or 'all' ['all']
                --show-label {name,num,ser}
                                    Label by station_name (name), ant_num (num) or
                                    serial_num (ser) or false [num]
                --fig-num FIG_NUM     Provide a specific figure number to the plot [default]
                --update UPDATE       Update station records. Format station0:col0:val0,
                                    [station1:]col1:val1... [None]
                --add-new-geo         Flag to enable adding of a new geo_location under
                                    update. [False]
        """
        )
        sys.exit()

    # interpret args
    at_date = cm_utils.get_astropytime(args.date, args.time)
    args.loc = cm_utils.listify(args.loc)
    args.station_types = cm_utils.listify(args.station_types)
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
        cofa = h.cofa()
        h.print_loc_info(cofa, args.verbosity)
        if args.graph:
            show_fig = h.plot_station_types(at_date, state_args)
            state_args['marker_color'] = 'g'
            state_args['marker_shape'] = '*'
            state_args['marker_size'] = 14
            state_args['show_label'] = 'name'
            show_fig = h.plot_stations([cofa[0].station_name], at_date, state_args)

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
        you_are_sure = cm_utils.query_yn("Warning:  Update is best done via a \
                                           script -- are you sure you want to do this? ", 'n')
        if you_are_sure:
            geo_location.update(session, data, args.add_new_geo)

    if show_fig:
        geo_handling.show_it_now(show_fig)
    h.close()
