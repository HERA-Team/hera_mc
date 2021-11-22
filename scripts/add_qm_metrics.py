#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to add quality metrics file to M&C database.
"""
import hera_mc.mc as mc

parser = mc.get_mc_argument_parser()
parser.add_argument(
    "files",
    metavar="files",
    type=str,
    nargs="+",
    help="json files to read and enter into db.",
)
parser.add_argument(
    "--type",
    dest="type",
    type=str,
    default=None,
    help='File type to add to db. Options = ["ant", "firstcal", "omnical"]',
)
args = parser.parse_args()
db = mc.connect_to_mc_db(args)
session = db.sessionmaker()

for f in args.files:
    session.ingest_metrics_file(f, args.type)

session.commit()
