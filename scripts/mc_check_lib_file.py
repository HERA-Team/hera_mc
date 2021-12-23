#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 The HERA Collaboration
# Licensed under the 2-clause BSD License
"""
Check that input files are safely in the librarian.

This script takes a list of input files and returns the list of those
found in the HERA_MC.lib_files table.

NOTE: Assumes that lib_files is a faithful list of files uploaded to the Librarian
"""

import os

from hera_mc import mc


ap = mc.get_mc_argument_parser()
ap.description = """Check that listed files are safely in librarian."""
ap.add_argument("files", type=str, default=None, nargs="*", help="list of files")


args = ap.parse_args()
db = mc.connect_to_mc_db(args)

found_files = []
with db.sessionmaker() as session:
    for pathname in args.files:
        filename = os.path.basename(pathname)
        out = session.get_lib_files(filename)
        if len(out) > 0:
            print(pathname)  # if we have a file, say so
