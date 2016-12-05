#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to generate table initialization files.
"""
import pandas as pd
from hera_mc import mc, geo_location, part_connect
import os.path, csv
import sys

parser = mc.get_mc_argument_parser()
parser.add_argument('--maindb', help="flag for change from main db, with user-generated key", default=None)
parser.add_argument('--tables', help="name of table for which to initialize", default='all')
parser.add_argument('--base', help="can define a base set of initialization data files", action='store_true')
args = parser.parse_args()

cm_tables = {'part_info':[part_connect.PartInfo,0],
             'connections':[part_connect.Connections,1],
             'parts_paper':[part_connect.Parts,2],
             'geo_location':[geo_location.GeoLocation,3],
             'station_meta':[geo_location.StationMeta,4]}

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
tables_to_init = list(reversed(tables_to_read))

db = mc.connect_to_mc_db(args)
check_localdb = 'need to do this'
if args.maindb:
    print('localdb should be the main db, if not terminate')
    sys.exit()
else:
    print('localdb should not be the main db, if so terminate')

if args.base:
    data_prefix = 'initialization_base_data_'
else:
    data_prefix = 'initialization_data_'

#Prep tables
for table in tables_to_read:
    data_filename = os.path.join(mc.data_path,data_prefix+table+'.csv')
    dbkey = check_data_file(data_filename)
    if not dbkey:
        print('Initialization for %s not found' % (table))
        continue
    ##################################HANDLE MAINDB CASE###############################
    if args.maindb:
        if dbkey != args.maindb:
            print('Invalid key for maindb')
            continue
        print('How do we want to handle this?')
    ##################################HANDLE REMOTE CASE###############################
    else:
        if dbkey != '$_remote_$':
            print('Skipping since maindb keyed file; mainly out of obstinance')
            print('\t',data_filename)
            continue
        with db.sessionmaker() as session:
            num_rows_deleted = session.query(cm_tables[table][0]).delete()

#Initialize tables
for table in tables_to_init:
    data_filename = os.path.join(mc.data_path,data_prefix+table+'.csv')
    dbkey = check_data_file(data_filename)
    if not dbkey:
        print('Initialization for %s not found' % (table))
        continue
    ##################################HANDLE MAINDB CASE###############################
    if args.maindb:
        if dbkey != args.maindb:
            print('Invalid key for maindb')
            continue
        print('How do we want to handle this?')
    ##################################HANDLE REMOTE CASE###############################
    else:
        if dbkey != '$_remote_$':
            print("Skipping since maindb keyed file; mainly out of obstinance")
            print("since it shouldn't really hurt anything.")
            print('\t',data_filename)
            continue
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
                        continue
                    for i,r in enumerate(row):
                        if r=='':
                            r = None
                        setattr(table_inst,field_name[i],r)
                    session.add(table_inst)

            


