#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

import hera_mc.mc as mc
from sqlalchemy import create_engine
from sqlalchemy.engine import reflection

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)
db_url = db.engine.url

print('creating engine')
this_engine = create_engine(db_url)
print('reflecting engine into inspector')
insp = reflection.Inspector.from_engine(this_engine)

print(db_url)
print(insp.get_table_names())
