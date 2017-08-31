#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Wrapper to allow some different data views of cm database.
Methods are in cm_dataview.
"""

from __future__ import print_function
from hera_mc import mc, cm_utils
import sys

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  corr fc-view, file-view, info [fc_view]", default='corr')
    parser.add_argument('-p', '--parts', help="Part list (comma-separated,no spaces) or active [active]", default='active')
    parser.add_argument('--dt', help="Time resolution (in days) of view.  [1]", default=1.0)
    parser.add_argument('--file', help="Write data to file --file [None].", dest='file', default=None)
    parser.add_argument('--output', help="Type of data output, either flag or corr", choices=['flag', 'corr'], default='flag')
    cm_utils.add_date_time_args(parser)
    parser.add_argument('--date2', help="UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' [now]", default='now')
    parser.add_argument('--time2', help="UTC hh:mm or float (hours)", default=0.0)
    parser.add_argument('-t', '--station-types', help="Station types used for input (csv_list or all) [HH]",
                        dest='station_types', default='HH')
    args = parser.parse_args()

    args.action = args.action.lower()[:2]

    if args.action == 'in':
        print(
            """
        Available actions are (only need first two letters) [fc-view]:
            fc-view:  fully-connected view of part --parts(-p) between date and date2.
                     both default to 'now', so at least date must be changed.
                     if --parts == 'all', it will go through all currently active
                     if --file is set, it will write a file with the data, which is either:
                         --output flag [default] or
                         --output corr
            file-view:  plot file(s)
            corr:  Provides information on the correlator hookups for the supplied --date/--time.
                cmdv.py corr:  will provide a list of correlator inputs for stations in --station-types
                cmdv.py corr --parts(-p)  will provide correlator info for --parts
            info:  Print this information and exit.
        """
        )
        sys.exit()

    from hera_mc import cm_dataview, part_connect, geo_handling, cm_hookup

    if isinstance(args.dt, str):
        args.dt = float(args.dt)

    # start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    dv = cm_dataview.Dataview(session)
    geo = geo_handling.Handling(session)
    hookup = cm_hookup.Hookup(session)

    if args.action == 'co':
        at_date = cm_utils._get_astropytime(args.date, args.time)
        if args.parts.lower() == 'active':
            fully_connected = geo.get_all_fully_connected_at_date(at_date,
                                                                  station_types_to_check=args.station_types)
            dv.print_fully_connected(fully_connected)
        else:
            args.parts = cm_utils.listify(args.parts)
            fully_connected = []
            for a2f in args.parts:
                c = geo.get_fully_connected_location_at_date(a2f, at_date, hookup, fc=None)
                fully_connected.append(c)
            dv.print_fully_connected(fully_connected)

    elif args.action == 'fc':
        start_date = cm_utils._get_astropytime(args.date, args.time)
        stop_date = cm_utils._get_astropytime(args.date2, args.time2)
        args.station_types = cm_utils.listify(args.station_types)
        if args.parts.lower() == 'active':
            conn = geo.get_all_fully_connected_at_date('now', station_types_to_check=args.station_types)
            args.parts = []
            for c in conn:
                args.parts.append(c['station_name'])
            args.parts = sorted(args.parts)
        else:
            args.parts = cm_utils.listify(args.parts)
        fc_map = dv.read_db(args.parts, start_date, stop_date, args.dt)
        if args.file is not None:
            dv.write_fc_map_file(args.file, output=args.output)
        dv.plot_fc_map()

    elif args.action == 'fi':
        args.file = cm_utils.listify(args.file)
        parts, fc_map = dv.read_fc_map_files(args.file)
        dv.plot_fc_map()
