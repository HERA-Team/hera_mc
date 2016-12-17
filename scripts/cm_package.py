#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to generate table initialization files.
"""
import pandas as pd
from hera_mc import mc, cm_table_info
import os, os.path

parser = mc.get_mc_argument_parser()
parser.add_argument('--maindb',help="user-generated key to allow change to main db",default=None)
parser.add_argument('--tables', help="name of table for which to generate initialization data file",default='all')
parser.add_argument('--base', help="can define a base set of initialization data files",action='store_true')
args = parser.parse_args()

tmp_filename = '__tmp_initfile.tmp'

if args.base:
    data_prefix = cm_table_info.base_data_prefix
else:
    data_prefix = cm_table_info.data_prefix
cm_tables = cm_table_info.cm_tables

db = mc.connect_to_mc_db(args)
if args.tables == 'all':
    tables_to_write = cm_tables.keys()
else:
    tables_to_write = args.tables.split(',')

for table in tables_to_write:
    data_filename = os.path.join(mc.data_path,data_prefix+table+'.csv')
    table_data = pd.read_sql_table(table, db.engine)
    if args.maindb:
        table_data.to_csv(tmp_filename, index=False)
    else:
        table_data.to_csv(data_filename, index=False)
    if args.maindb:  ###Put key in first line
        fpout = open(data_filename,'w')
        fpin = open(tmp_filename,'r')
        keyline = '$_maindb_$:'+args.maindb+'\n'
        fpout.write(keyline)
        for line in fpin:
            fpout.write(line)
        fpin.close()
        fpout.close()
        os.remove(tmp_filename)
