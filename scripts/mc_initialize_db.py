#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

import hera_mc.mc as mc
from hera_mc import cm_transfer

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

if not hasattr(db, 'create_tables'):
    raise SystemExit('error: you can only set up a database that\'s '
                     'configured to be in "testing" mode')

db.create_tables()

# Initialize configuration management tables
args.base = False
args.tables = 'all'
if cm_transfer.check_if_main():
    args.maindb = raw_input('You are initializing the main db. Please enter key:')
else:
    args.maindb = False
cm_transfer.__initialization(args)
