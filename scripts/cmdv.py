#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Allows some different data views of cm database.
Currently this is only to look at the full connections of parts looped over time,
either via db calls or pre-written files.
"""

from __future__ import absolute_import, division, print_function
from hera_mc import mc, geo_handling, cm_utils, cm_revisions, part_connect
from astropy.time import Time, TimeDelta
import numpy as np
import matplotlib.pyplot as plt


def write_file(filename, parts_list, fc_map):
    p0 = parts_list[0]
    ndate = len(fc_map[p0][0])
    print("Writing {}".format(filename))
    fp = open(filename, 'w')
    fp.write('Date            \t')
    for p in parts_list:
        fp.write('{}\t'.format(p))
    fp.write('\n')
    for i in range(ndate):
        fp.write('{:%Y-%m-%d %H:%M}\t'.format(fc_map[p0][0][i]))
        for p in parts_list:
            fp.write('{:d}\t'.format(fc_map[p][1][i]))
        fp.write('\n')
    fp.close()


def read_files(filenames):
    fc_map = {}
    parts = []
    for fn in filenames:
        try:
            fp = open(fn, 'r')
        except IOError:
            print('{} not found.'.format(fn))
            continue
        print("Reading {}".format(fn))
        part_fn = fp.readline().split()
        del(part_fn[0])
        for p in part_fn:
            if p not in fc_map.keys():
                fc_map[p] = [[], []]
                parts.append(p)
        for line in fp:
            data = line.split()
            date = cm_utils._get_astropytime(data[0], data[1])
            del(data[0:2])
            for i in range(len(data)):
                fc_map[part_fn[i]][0].append(date.datetime)
                fc_map[part_fn[i]][1].append(int(data[i]))
    return parts, fc_map


def plot_data(parts, fc_map, separate=True):
    dy = 1.0 / len(parts)
    for i, p in enumerate(parts):
        y = np.array(fc_map[p][1])
        if separate:
            y = y * (2.0 - i * dy)
        plt.plot(fc_map[p][0], y, 'o', label=p)
    plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left')
    plt.grid()


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('action', nargs='?', help="Actions are:  fc-view, file-view, info [fc_view]", default='fc-view')
    parser.add_argument('-p', '--parts', help="Part list (comma-separated,no spaces) [HH0]", default='HH0')
    parser.add_argument('--dt', help="Time resolution (in days) of view.  [1]", default=1.0)
    parser.add_argument('--file', help="Write data to file --file [None].", dest='file', default=None)
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
            file-view:  plot file
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
        stop_date = cm_utils._get_astropytime(args.date2, args.time2)
        fc_map = {}
        for p in args.parts:
            print("Finding ", p)
            fc_map[p] = [[], [], []]
            at_date = cm_utils._get_astropytime(args.date, args.time)
            while at_date < stop_date:
                fc = cm_revisions.get_full_revision(p, at_date, args.full_req, session)
                fc_map[p][0].append(at_date.datetime)
                fc_map[p][1].append(len(fc))
                fc_map[p][2].append(fc)
                at_date += TimeDelta(args.dt * 24 * 3600, format='sec')
        if args.file is not None:
            write_file(args.file, args.parts, fc_map)
        plot_data(args.parts, fc_map)
        plt.show()

    elif args.action == 'fi':
        args.file = cm_utils.listify(args.file)
        parts, fc_map = read_files(args.file)
        plot_data(parts, fc_map)
        plt.show()
