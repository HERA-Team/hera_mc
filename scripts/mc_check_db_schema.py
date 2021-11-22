#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from hera_mc import MCDeclarativeBase, mc
from hera_mc.db_check import is_valid_database

parser = mc.get_mc_argument_parser()
args = parser.parse_args()

try:
    db = mc.connect_to_mc_db(args)
except RuntimeError as e:
    raise SystemExit(str(e))

# If the specified database is in "testing" mode, we won't have actually
# checked anything yet. It doesn't hurt to double-check if the DB is
# in production mode, so let's just check again.

with db.sessionmaker() as session:
    if not is_valid_database(MCDeclarativeBase, session):
        raise SystemExit(
            "database {0} does not match expected schema".format(db.engine.url)
        )
