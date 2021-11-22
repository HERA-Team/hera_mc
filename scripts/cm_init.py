#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to read configuration management csv files and initialize tables.
"""

from hera_mc import mc, cm_transfer

parser = mc.get_mc_argument_parser()
parser.add_argument(
    "--maindb",
    help="password to initialize the main site database - admin only",
    default=False,
)
parser.add_argument(
    "--tables",
    help="name of table for which to initialize or 'all' ['all']",
    default="all",
)
parser.add_argument(
    "--testing",
    help="sets input file directory to the test_data_path",
    action="store_true",
)
args = parser.parse_args()

cm_transfer.initialize_db_from_csv(
    tables=args.tables, maindb=args.maindb, testing=args.testing
)
