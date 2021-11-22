#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location (via geo_handling)

"""

from hera_mc import mc, geo_handling, cm_utils

if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "fg_action",
        nargs="*",
        default=["active"],
        help="Actions for foreground listing:  "
        "a[ctive], i[nstalled], p[osition] <csv-list>, c[ofa], "
        "s[ince], n[one] (active)",
    )
    parser.add_argument(
        "-b",
        "--background",
        help="Set background type (layers)",
        choices=["none", "installed", "layers", "all"],
        default="installed",
    )
    parser.add_argument(
        "-g", "--graph", help="Graph (plot) station types (False)", action="store_true"
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Name of file to write out 'foreground' antenna positions",
        default=None,
    )
    cm_utils.add_date_time_args(parser)
    parser.add_argument(
        "-x",
        "--xgraph",
        help="X-axis of graph. [E]",
        choices=["N", "n", "E", "e", "Z", "z"],
        default="E",
    )
    parser.add_argument(
        "-y",
        "--ygraph",
        help="Y-axis of graph. [N]",
        choices=["N", "n", "E", "e", "Z", "z"],
        default="N",
    )
    parser.add_argument(
        "-t",
        "--station-types",
        help="Station types searched (csv_list or 'all') "
        "Can use types or prefixes. (default)",
        dest="station_types",
        default="default",
    )
    parser.add_argument(
        "--label",
        choices=["name", "num", "ser", "none"],
        default="num",
        help="Label by station_name (name), ant_num (num) "
        "serial_num (ser) or none (none) (num)",
    )
    parser.add_argument(
        "--hookup-type",
        dest="hookup_type",
        help="Hookup type to use for active antennas.",
        default=None,
    )
    args = parser.parse_args()
    if len(args.fg_action) > 1:
        position = cm_utils.listify(args.fg_action[1])
    args.fg_action = args.fg_action[0].lower()
    args.background = args.background.lower()
    args.station_types = args.station_types.lower()
    args.label = args.label.lower()
    at_date = cm_utils.get_astropytime(args.date, args.time, args.format)
    if args.station_types not in ["default", "all"]:
        args.station_types = cm_utils.listify(args.station_types)
    if args.label == "false" or args.label == "none":
        args.label = False
    xgraph = args.xgraph.upper()
    ygraph = args.ygraph.upper()
    if args.fg_action.startswith("s"):
        cutoff = at_date
        at_date = cm_utils.get_astropytime("now")

    # start session and instances
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    G = geo_handling.Handling(session)

    # If args.graph is set, apply background
    if args.graph:
        G.set_graph(True)
        if args.background == "all" or args.background == "layers":
            G.plot_all_stations()
        if not args.fg_action.startswith("i"):
            if args.background == "installed" or args.background == "layers":
                G.plot_station_types(
                    station_types_to_use=args.station_types,
                    query_date=at_date,
                    xgraph=xgraph,
                    ygraph=ygraph,
                    label=args.label,
                )

    # Process foreground action.
    fg_markersize = 10
    if args.file is not None:
        G.start_file(args.file)

    if args.fg_action.startswith("a"):
        located = G.get_active_stations(
            station_types_to_use=args.station_types,
            query_date=at_date,
            hookup_type=args.hookup_type,
        )
        G.plot_stations(
            located,
            xgraph=xgraph,
            ygraph=ygraph,
            label=args.label,
            marker_color="k",
            marker_shape="*",
            marker_size=fg_markersize,
        )
    elif args.fg_action.startswith("i"):
        G.plot_station_types(
            station_types_to_use=args.station_types,
            query_date=at_date,
            xgraph=xgraph,
            ygraph=ygraph,
            label=args.label,
        )
    elif args.fg_action.startswith("p"):
        located = G.get_location(position, at_date)
        G.print_loc_info(located)
        G.plot_stations(
            located,
            xgraph=xgraph,
            ygraph=ygraph,
            label=args.label,
            marker_color="k",
            marker_shape="*",
            marker_size=fg_markersize,
        )
    elif args.fg_action.startswith("c"):
        cofa = G.cofa()
        G.print_loc_info(cofa)
        G.plot_stations(
            cofa,
            xgraph=xgraph,
            ygraph=ygraph,
            label="name",
            marker_color="k",
            marker_shape="*",
            marker_size=fg_markersize,
        )
    elif args.fg_action.startswith("s"):
        new_antennas = G.get_ants_installed_since(cutoff, args.station_types)
        G.plot_stations(
            new_antennas,
            xgraph=xgraph,
            ygraph=ygraph,
            label=args.label,
            marker_color="b",
            marker_shape="*",
            marker_size=fg_markersize,
        )
        print("{} new antennas since {}".format(len(new_antennas), cutoff))
        s = ""
        for na in new_antennas:
            s += na.station_name + ", "
        s = s.strip().strip(",") + "\n"
        print(s)

    if args.graph:
        geo_handling.show_it_now()
    G.close()
