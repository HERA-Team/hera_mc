#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to generate table initialization files.
"""
import pandas as pd
from hera_mc import mc, geo_location, part_connect, cm_table_info
import os.path, csv
import sys

parser = mc.get_mc_argument_parser()
parser.add_argument('--maindb', help="flag for change from main db, with user-generated key", default=None)
parser.add_argument('--tables', help="name of table for which to initialize", default='all')
parser.add_argument('--base', help="can define a base set of initialization data files", action='store_true')
args = parser.parse_args()

def check_data_file(data_filename):
    try:
        fp = open(data_filename,'r')
    except IOError:
        return None
    firstline = fp.readline()
    if firstline.split(':')[0] == '$_maindb_$':
        dbkey = firstline.split(':')[1]
    else:
        dbkey = '$_remote_$'
    fp.close()
    return dbkey

###Get tables to deal with in proper order
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
        print(table,'not found')
while 'NULL' in tables_to_read:
    tables_to_read.remove('NULL')

###Check that db flag and actual db agree for remote v main
db = mc.connect_to_mc_db(args)
is_maindb = False
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

#Check tables and reduce list to valid use_table
use_table = list(tables_to_read)
for table in tables_to_read:
    data_filename = os.path.join(mc.data_path,data_prefix+table+'.csv')
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
                    num_rows_deleted = session.query(cm_tables[table][0]).delete()

tables_to_init = list(reversed(use_table))
###Initialize tables
for table in tables_to_init:
    data_filename = os.path.join(mc.data_path,data_prefix+table+'.csv')
    ##################################HANDLE MAINDB CASE###############################
    if args.maindb:
        with db.sessionmaker() as session:
            key_row = True
            field_row = False
            field_name = []
            with open(data_filename,'rb') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    table_inst = cm_tables[table][0]()
                    if key_row:
                        key_row = False
                        field_row = True
                    elif field_row:
                        field_name = row
                        field_row=False
                    else:
                        for i,r in enumerate(row):
                            if r=='':
                                r = None
                            print('########################################')
                            print('# Here is where the logic etc would go #')
                            print('# ...maybe use part_handling functions #')
                            #setattr(table_inst,field_name[i],r)
                            print('#      cm_initialization: line 115     #')
                            print('########################################')
                        #session.add(table_inst)
    ##################################HANDLE REMOTE CASE###############################
    else:
        with db.sessionmaker() as session:
            field_row = True
            field_name = []
            with open(data_filename,'rb') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    table_inst = cm_tables[table][0]()
                    if field_row:
                        field_name = row
                        field_row=False
                    else:
                        for i,r in enumerate(row):
                            if r=='':
                                r = None
                            setattr(table_inst,field_name[i],r)
                        session.add(table_inst)

            


