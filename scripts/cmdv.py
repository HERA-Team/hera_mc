#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Wrapper to allow some different data views of cm database.
Methods are in cm_dataview.
"""

from __future__ import absolute_import, division, print_function
from hera_mc import mc, cm_dataview, cm_utils, part_connect


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  fc-view, file-view, info [fc_view]", default='fc-view')
    parser.add_argument('-p', '--parts', help="Part list (comma-separated,no spaces) [HH0]", default='HH0')
    parser.add_argument('--dt', help="Time resolution (in days) of view.  [1]", default=1.0)
    parser.add_argument('--file', help="Write data to file --file [None].", dest='file', default=None)
    parser.add_argument('--output', help="Type of data output, either flag or corr", choices=['flag', 'corr'], default='flag')
    parser.add_argument('--full-req', help="Parts to include in for full connection.", dest='full_req', default='default')
    cm_utils.add_date_time_args(parser)
    parser.add_argument('--date2', help="UTC YYYY/MM/DD or '<' or '>' or 'n/a' or 'now' [now]", default='now')
    parser.add_argument('--time2', help="UTC hh:mm or float (hours)", default=0.0)
    args = parser.parse_args()

    args.action = args.action.lower()[:2]

    if args.action == 'in':
        print(
            """
        Available actions are (only need first two letters) [fcview]:
            fc-view:  fully-connected view of part --part(-p) between date and date2.
                     both default to 'now', so at least date must be changed.
                     if --file is set, it will write a file with the data, which is either:
                         --output flag [default] or
                         --output corr
            file-view:  plot file(s)
            info:  Print this information and exit.
        """
        )
        sys.exit()

    if isinstance(args.dt, str):
        args.dt = float(args.dt)
    if args.full_req == 'default':
        args.full_req = part_connect.full_connection_parts_paper
    else:
        args.full_req = cm_utils.listify(args.full_req)

    if args.action == 'fc':
        # start session
        db = mc.connect_to_mc_db(args)
        session = db.sessionmaker()
        args.parts = cm_utils.listify(args.parts)
        start_date = cm_utils._get_astropytime(args.date, args.time)
        stop_date = cm_utils._get_astropytime(args.date2, args.time2)
        fc_map = cm_dataview.read_db(args.parts, start_date, stop_date, args.dt, args.full_req, session)
        if args.file is not None:
            cm_dataview.write_file(args.file, args.parts, fc_map, output=args.output, session=session)
        cm_dataview.plot_data(args.parts, fc_map)

    elif args.action == 'fi':
        args.file = cm_utils.listify(args.file)
        parts, fc_map = cm_dataview.read_files(args.file)
        cm_dataview.plot_data(parts, fc_map)
