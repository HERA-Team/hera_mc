#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to generate table initialization files (package from db to csv).
"""

from hera_mc import mc, cm_transfer

parser = mc.get_mc_argument_parser()
parser.add_argument(
    "--tables",
    help="name of table for which to generate " "initialization data file",
    default="all",
)
parser.add_argument(
    "--go",
    help="If set, will move files to dist directory, commit and add \
                                 hash to table.",
    action="store_true",
)
parser.add_argument(
    "--cm_csv_path", help="Available if you want to redirect 'go' dir.", default=None
)
args = parser.parse_args()

files_written = cm_transfer.package_db_to_csv(tables=args.tables)

if args.go:
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    if args.cm_csv_path is None:
        args.cm_csv_path = mc.get_cm_csv_path(None)
    cm_transfer.pack_n_go(session, args.cm_csv_path)
