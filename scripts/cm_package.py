#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to generate table initialization files.
"""
import pandas as pd
from hera_mc import mc
import os, os.path

parser = mc.get_mc_argument_parser()
parser.add_argument('--maindb',help="flag for change to main db, with user-generated key",default=None)
parser.add_argument('--tables', help="name of table for which to generate initialization data file",default=None)
parser.add_argument('--base', help="can define a base set of initialization data files",action='store_true')
args = parser.parse_args()

first_filename = '__initfile.tmp'

if args.base:
    data_prefix = 'initialization_base_data_'
else:
    data_prefix = 'initialization_data_'

db = mc.connect_to_mc_db(args)
if args.maindb or args.tables:
    tables_to_write = args.tables.split(',')
else:
    tables_to_write = ['geo_location','station_meta','parts_paper','part_info','connections']

for table in tables_to_write:
    data_filename = os.path.join(mc.data_path,data_prefix+table+'.csv')
    table_data = pd.read_sql_table(table, db.engine)
    if args.maindb:
        file_to_write = first_filename
    else:
        file_to_write = data_filename
    table_data.to_csv(file_to_write, index=False)
    if args.maindb:
        fpout = open(data_filename,'w')
        fpin = open(first_filename,'r')
        keyline = '$_maindb_$:'+key+'\n'
        fpout.write(keyline)
        for line in fpin:
            fpout.write(line)
        fpin.close()
        fpout.close()
        os.remove(first_filename)
