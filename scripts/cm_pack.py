#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to generate table initialization files (package from db to csv).
"""

from hera_mc import mc, cm_transfer

parser = mc.get_mc_argument_parser()
parser.add_argument('--maindb', help="user-generated key to allow change to main "
                    "db (written on remote) [False]", default=False)
parser.add_argument('--tables', help="name of table for which to generate "
                    "initialization data file", default='all')
parser.add_argument('--base', help="can define a base set of initialization "
                    "data files", action='store_true')
args = parser.parse_args()

cm_transfer.package_db_to_csv(tables=args.tables, base=args.base,
                              maindb=args.maindb)
