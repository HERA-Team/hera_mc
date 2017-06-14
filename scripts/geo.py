#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location (via geo_handling)

"""
from __future__ import absolute_import, division, print_function
import sys
from hera_mc import mc, geo_handling, cm_utils

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    # action arguments
    parser.add_argument('-c', '--cofa', help="Print out center of array information [False]", action='store_true')
    parser.add_argument('-f', '--find', help="Find location of given station_name(s) or antenna_number(s) (if # or A#); csv_list [None]", default=None)
    parser.add_argument('-g', '--graph', help="Graph station types [False]", action='store_true')
    parser.add_argument('-d', '--since_date', help="Only show antennas (set by background) installed since date/time [False]", action='store_true')

    # parameter state/value arguments
    cm_utils.add_verbosity_args(parser)
    parser.add_argument('-x', '--xgraph', help="X-axis of graph. [E]", choices=['N', 'n', 'E', 'e', 'Z', 'z'], default='E')
    parser.add_argument('-y', '--ygraph', help="Y-axis of graph. [N]", choices=['N', 'n', 'E', 'e', 'Z', 'z'], default='N')
    cm_utils.add_date_time_args(parser)
    parser.add_argument('--background', help="Station types used for graph (csv_list or all) [HH,PH,S]", default='HH,PH,S')
    parser.add_argument('--show_state', help="Show only the 'active' stations or all [all]", default='all')
    parser.add_argument('--show_label', help="Label by station_name (name), ant_num (num) or serial_num (ser) or false [num]", default='num')
    parser.add_argument('--fig_num', help="Provide a specific figure number to the plot [default]", default='default')

    # database arguments
    parser.add_argument('--update', help="Update station records.  Format station0:col0:val0, [station1:]col1:val1...  [None]", default=None)
    parser.add_argument('--add-new-geo', help="Flag to enable adding of a new geo_location under update.  [False]", action='store_true')
    args = parser.parse_args()

    # interpret args
    if args.find is not None:
        args.find = args.find.upper()
        if ',' in args.find:
            args.find = args.find.split(',')
        else:
            args.find = [args.find]
    query_date = cm_utils._get_datetime(args.date,args.time)
    args.background = args.background.upper()
    if ',' in args.background:
        args.background = args.background.split(',')
    else:
        args.background = [args.background]
    args.show_label = args.show_label.lower()
    if args.show_label.lower() == 'false':
        args.show_label = False
    if args.fig_num.lower() == 'default':
        args.fig_num = args.xgraph+args.ygraph
    show_fig = False

    # package up state to dictionary
    state_args = {'verbosity':args.verbosity.lower(),
                  'xgraph':args.xgraph.upper(),
                  'ygraph':args.ygraph.upper(),
                  'background':args.background,
                  'show_state':args.show_state.lower(),
                  'show_label':args.show_label,
                  'fig_num':args.fig_num}

    # process
    h = geo_handling.Handling(args)
    if args.graph:
        show_fig = h.plot_station_types(query_date, state_args)
    if args.cofa:
        cofa = h.cofa(show_cofa=True)
    if args.since_date:
        new_antennas = h.get_ants_installed_since(query_date, state_args['background'])
        print("{} new antennas since {}".format(len(new_antennas),query_date))
        if len(new_antennas)>0:
            s=''
            for na in new_antennas:
                s+=na+', '
            s=s.strip().strip(',')+'\n'
            print(s)
            state_args['marker_color']='b'
            state_args['marker_shape']='*'
            state_args['marker_size']=14
            show_fig = h.plot_stations(new_antennas, query_date, state_args)
    if args.find is not None:
        located = h.get_location(args.find, query_date, show_location=True, verbosity=state_args['verbosity'])
        if args.graph and len(located)>0:
            state_args['marker_size'] = 14
            h.overplot(located, state_args)

    if show_fig:
        geo_handling.show_it_now(show_fig)
    h.close()

    if args.update:
        you_are_sure = cm_utils._query_yn("Warning:  Update is best done via a script -- are you sure you want to do this? ", 'n')
        if you_are_sure:
            geo_location.update(args, data)
