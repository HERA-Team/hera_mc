#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to read configuration management csv files and initialize tables.
"""

from hera_mc import mc, cm_transfer

parser = mc.get_mc_argument_parser()
parser.add_argument('--maindb', help="user-generated key to change from main db [False]",
                    default=False)
parser.add_argument('--tables', help="name of table for which to initialize or 'all' ['all']",
                    default='all')
args = parser.parse_args()

cm_transfer.initialize_db_from_csv(tables=args.tables, maindb=args.maindb)
