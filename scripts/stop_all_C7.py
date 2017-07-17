#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle the ONE TIME disconnection of all 150m cables
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_utils, part_connect, cm_handling, geo_handling, cm_hookup, cm_part_revisions
import sys


def stop_connection(args, h, crev):
    """This adds stop times to the previous connections between:
           station and antenna rev A
           antenna revA and feed rev A
    """

    current = int(args.date.gps)
    data = []
    args.add_new_connection = False

    EN = ['eb','nb']
    for p in EN:
        C7RI = h.get_connections(crev[0],crev[1],p,True)
        print(C7RI)
        for ck in C7RI.keys():
            if crev[0] in ck:
                break
        else:
            ck = None
        if ck is not None:
            print("Stopping connection <{}:{}<{}|a>{}:{}>".format(crev[0],crev[1],p,C7RI[ck].downstream_part,C7RI[ck].down_part_rev))
            gps = C7RI[ck].start_gpstime
            stopping = [crev[0], crev[1], C7RI[ck].downstream_part, C7RI[ck].down_part_rev, p, 'a', gps, 'stop_gpstime', current]
            data.append(stopping)

    if args.actually_do_it:
        part_connect.update_connection(args, data)
    else:
        print(data)

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-s', '--station_name', help="Name of station (HH# for hera)", default=None)
    cm_utils.add_date_time_args(parser)
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()

    args.verbosity = args.verbosity.lower()
    args.date = cm_utils._get_datetime(args.date)

    # Add extra args needed for various things
    args.add_new_connection = True
    args.active = True
    args.specify_port = 'all'
    args.revision = 'A'
    args.show_levels = False
    args.mapr_cols = 'all'
    args.exact_match = True
    args.actually_do_it = True

    connect = part_connect.Connections()
    handling = cm_handling.Handling(args)

    for i in range(128):
        crev = ('C7F'+str(i),'A')
        stop_connection(args,handling,crev)
