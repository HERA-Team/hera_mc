#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This dumps a csv with current connections

"""
from __future__ import absolute_import, division, print_function

from hera_mc import part_connect, cm_handling, cm_hookup, cm_utils, mc
import os.path

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    cm_utils.add_date_time_args(parser)
    parser.add_argument('-r','--revision', help="Specify revision for hpn (it's a letter).  [LAST]", default='LAST')
    active_group = parser.add_mutually_exclusive_group()
    active_group.add_argument('--show-active', help="Flag to show only the active parts/connections (default)",dest='active', action='store_true')
    active_group.add_argument('--show-all', help="Flag to show all parts/connections",dest='active', action='store_false')
    parser.set_defaults(active=True)
    args = parser.parse_args()

    args.hpn = 'RI1A3'
    args.mapr = args.hpn
    args.exact_match = False
    args.specify_port = 'all'
    args.show_levels = False
    args.mapr_cols = 'station,antenna,cable_receiverin,cable_container,f_engine'
    # Execute script
    handling = cm_handling.Handling(args)
    hookup = cm_hookup.Hookup(args)
    hookup_dict = hookup.get_hookup(show_hookup=True)
    for i in hookup_dict:
        print("-------------",i)
        for j in hookup_dict[i]:
            print(j)
#        print('\t',i,hookup_dict[i][1][0],hookup_dict[i][1][1])
