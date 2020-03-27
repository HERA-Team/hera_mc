#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Utility script to display node information.
"""
from __future__ import absolute_import, division, print_function

import argparse
from hera_mc import cm_sysutils, cm_utils

ap = argparse.ArgumentParser()
ap.add_argument('nodes', nargs='?', help="Node numbers:  csv-list or hyphen-range.",
                default='0-29')
cm_utils.add_date_time_args(ap)
ap.add_argument('--notes-start-date', dest='notes_start_date',
                help="<For notes> start_date for notes [<]",
                default='<')
ap.add_argument('--notes-start-time', dest='notes_start_time',
                help="<For notes> start_time for notes",
                default=0.0)
args = ap.parse_args()

if '-' in args.nodes:
    start, stop = args.nodes.split('-')
    args.nodes = range(int(start), int(stop) + 1)
else:
    args.nodes = [int(x) for x in args.nodes.split(',')]

date_query = cm_utils.get_astropytime(args.date, args.time)
notes_start_date = cm_utils.get_astropytime(args.notes_start_date,
                                            args.notes_start_time)
