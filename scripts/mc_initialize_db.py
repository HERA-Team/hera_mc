#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

import hera_mc.mc as mc

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

if not hasattr(db, 'create_tables'):
    raise SystemExit ('error: you can only set up a database that\'s '
                      'configured to be in "testing" mode')

db.create_tables()
