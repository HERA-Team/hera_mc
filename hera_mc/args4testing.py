#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is an import module used to test code within the python environment, rather than as a script.
It is for debugging purposes.

"""
from __future__ import absolute_import, division, print_function

from hera_mc import part_connect, cm_handling, cm_hookup, cm_utils, mc
import os.path
import sys

parser = mc.get_mc_argument_parser()
parser.add_argument('-p','--hpn', help="Get part information. [None]", default=None)
parser.add_argument('-t','--hptype', help="List the hera part types. [False]", action='store_true')
cm_utils.add_verbosity_args(parser)
parser.add_argument('-c','--connection', help="Show all connections directly to a part. [None]", default=None)
parser.add_argument('-u','--update', 
                    help="Update part number records.  Format hpn0:[rev0]:col0:val0, [hpn1:[rev1]]col1:val1...  [None]", default=None)
parser.add_argument('-m','--mapr', help="Show full hookup chains from given part. [None]", default=None)
parser.add_argument('-r','--revision', help="Specify revision for hpn (it's a letter).  [LAST]", default='LAST')
parser.add_argument('--specify-port', help="Define desired port(s) for hookup. [all]", dest='specify_port', default='all')
parser.add_argument('--show-levels', help="Show power levels if enabled (and able) [False]", dest='show_levels', action='store_true')
parser.add_argument('--exact-match', help="Force exact matches on part numbers, not beginning N char. [False]", dest='exact_match', 
                    action='store_true')
parser.add_argument('--add-new-part', help="Flag to allow update to add a new record.  [False]", dest='add_new_part', action='store_true')
parser.add_argument('--mapr-cols', help="Specify a subset of parts to show in mapr, comma-delimited no-space list. [all]", 
                    dest='mapr_cols', default='all')
parser.add_argument('--levels-testing', help="Set to test filename if correlator levels not accessible [levels.tst]", 
                    dest='levels_testing', default='levels.tst')
parser.add_argument('--date', help="UTC YYYY/MM/DD or now [now]", default='now')
parser.add_argument('--time', help="UTC hh:mm or now [now]", default='now')
active_group = parser.add_mutually_exclusive_group()
active_group.add_argument('--show-active', help="Flag to show only the active parts/connections (default)",dest='active', action='store_true')
active_group.add_argument('--show-all', help="Flag to show all parts/connections",dest='active', action='store_false')
parser.set_defaults(active=True)
sys.argv = []
args = parser.parse_args()


args.hpn = 'A113'
#args.connection = args.connection.upper()
args.mapr = args.hpn.upper()
args.verbosity = args.verbosity.lower()
args.mapr_cols = args.mapr_cols.lower()
args.revision = args.revision.upper()
args.active = False
args.levels_testing = False
args.levels_testing = os.path.join(mc.test_data_path, 'levels.tst')


