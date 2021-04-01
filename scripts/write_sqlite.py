#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.
"""Update the sqlite db from the psql database."""
import argparse
from hera_mc import cm_gen_sqlite

ap = argparse.ArgumentParser()
ap.add_argument('--force', help='Force sqlite db write.', action='store_true')
args = ap.parse_args()


hash_dict = cm_gen_sqlite.get_table_hash_info()
if args.force:
    write_database = True
else:
    write_database = not cm_gen_sqlite.same_table_hash_info(hash_dict)


if write_database:
    cm_gen_sqlite.update_sqlite()
    cm_gen_sqlite.write_table_hash_info(hash_dict)
