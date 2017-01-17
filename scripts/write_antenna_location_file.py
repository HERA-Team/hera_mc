#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to write out antenna locations for use in cal files.
"""
import pandas as pd
from hera_mc import mc

parser = mc.get_mc_argument_parser()
parser.add_argument('file', help="file name to save antenna locations to")
args = parser.parse_args()
filename = args.file
db = mc.connect_to_mc_db(args)

ant_locs = pd.read_sql_table('geo_location', db.engine)

ant_locs.to_csv(filename, index=False)
