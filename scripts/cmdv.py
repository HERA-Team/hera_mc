#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Wrapper to allow some different data views of cm database.
Methods are in cm_dataview.
"""

from hera_mc import mc, cm_utils, cm_dataview


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', help='type to chart:  connected and/or ants')
    parser.add_argument('--dt', help="timestep in days", default=30)
    cm_utils.add_date_time_args(parser)
    parser.add_argument('--date2',
                        help="UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' "
                        "or gps or julian [now]",
                        default='now')
    parser.add_argument('--time2',
                        help="UTC hh:mm or float (hours) ignored unless date of YYYY/MM/DD format",
                        default=0.0)
    parser.add_argument('--output_date_format',
                        help="Output date format.  Either 'jd' or 'ymd'", default='jd')
    parser.add_argument('--hookup_type',
                        help='parts_hera or parts_paper', default='parts_hera')
    args = parser.parse_args()

    if isinstance(args.dt, str):
        args.dt = float(args.dt)

    date_1 = cm_utils.get_astropytime(args.date, args.time)
    date_2 = cm_utils.get_astropytime(args.date2, args.time2)

    # start session
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    dv = cm_dataview.Dataview(session)

    if 'connected' in args.action:
        dv.connected_by_day(date_1, date_2, args.dt,
                            output='connected.txt',
                            station_types_to_check='default',
                            output_date_format=args.output_date_format,
                            hookup_type=args.hookup_type)
    if 'ants' in args.action:
        dv.ants_by_day(date_1, date_2, args.dt,
                       output='ants.txt',
                       output_date_format=args.output_date_format)
