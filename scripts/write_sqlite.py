#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.
"""Update the sqlite db from the psql database."""
import argparse
from hera_mc import cm_gen_sqlite

ap = argparse.ArgumentParser()
ap.add_argument("--force", help="Force sqlite db write.", action="store_true")
args = ap.parse_args()

sqlu = cm_gen_sqlite.SqliteHandling()

if args.force or sqlu.different_table_hash_dict():
    sqlu.update_sqlite()
    sqlu.write_table_hash_dict()
