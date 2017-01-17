#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to generate table initialization files.
"""
import pandas as pd
from hera_mc import mc, geo_location, part_connect, cm_table_info, cm_utils
import os.path
import csv
import sys

parser = mc.get_mc_argument_parser()
parser.add_argument('--maindb', help="user-generated key to change from main db [None]", default=None)
parser.add_argument('--tables', help="name of table for which to initialize or 'all' ['all']", default='all')
parser.add_argument('--base', help="use base set of initialization data files [False]", action='store_true')
parser.add_argument('--init_override', help="flag to override the 'are you sure' query [False]", action='store_true')
if __name__ == 'cm_initialization':
    parser.set_defaults(init_override=True)
args = parser.parse_args()

if not args.init_override:
    print("This will erase and rewrite the configuration management tables.")
    you_are_sure = cm_utils._query_yn(
        "Are you sure you want to do this? ", 'n')
    if you_are_sure:
        pass
    else:
        print("Exit with no rewrite.")
        sys.exit()


def check_if_maindb():
    if "obs" in os.path.expanduser('~'):
        return True
    else:
        return False


def check_data_file(data_filename):
    try:
        fp = open(data_filename, 'r')
    except IOError:
        return None
    firstline = fp.readline()
    if firstline.split(':')[0] == '$_maindb_$':
        dbkey = firstline.split(':')[1]
    else:
        dbkey = '$_remote_$'
    fp.close()
    return dbkey

# Get tables to deal with in proper order
cm_tables = cm_table_info.cm_tables
if args.tables == 'all':
    tables_to_read_unordered = cm_tables.keys()
else:
    tables_to_read_unordered = args.tables.split(',')
tables_to_read = []
for i in range(len(cm_tables.keys())):
    tables_to_read.append('NULL')
for table in tables_to_read_unordered:
    try:
        tables_to_read[cm_tables[table][1]] = table
    except KeyError:
        print(table, 'not found')
while 'NULL' in tables_to_read:
    tables_to_read.remove('NULL')

# Check that db flag and actual db agree for remote v main
db = mc.connect_to_mc_db(args)
is_maindb = check_if_maindb()
if args.maindb:
    if is_maindb == False:
        print('Error:  attempting main db access to remote db')
        sys.exit()
else:
    if is_maindb == True:
        print('Error:  attempting unkeyed access to main db')
        sys.exit()

if args.base:
    data_prefix = cm_table_info.base_data_prefix
else:
    data_prefix = cm_table_info.data_prefix

# Check tables and reduce list to valid use_table
use_table = list(tables_to_read)
for table in tables_to_read:
    data_filename = os.path.join(mc.data_path, data_prefix + table + '.csv')
    dbkey = check_data_file(data_filename)
    if not dbkey:
        print('Initialization for %s not found' % (table))
        use_table.remove(table)
    else:
        if args.maindb:
            if dbkey != args.maindb:
                print('Invalid maindb key:  ', table)
                use_table.remove(table)
        else:
            if dbkey != '$_remote_$':
                print('Invalid remotedb key:  ', table)
                use_table.remove(table)
            else:
                with db.sessionmaker() as session:
                    num_rows_deleted = session.query(
                        cm_tables[table][0]).delete()

tables_to_init = list(reversed(use_table))
# Initialize tables
for table in tables_to_init:
    data_filename = os.path.join(mc.data_path, data_prefix + table + '.csv')
    cm_utils._log('cm_initialization: ' + data_filename)
    if args.maindb:  # key_row/field_row toggle as db is read
        key_row = True
        field_row = False
    else:
        key_row = False
        field_row = True
    with db.sessionmaker() as session:
        field_name = []
        with open(data_filename, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                table_inst = cm_tables[table][0]()
                if key_row:
                    key_row = False
                    field_row = True
                elif field_row:
                    field_name = row
                    field_row = False
                else:
                    for i, r in enumerate(row):
                        if r == '':
                            r = None
                        setattr(table_inst, field_name[i], r)
                    session.add(table_inst)
