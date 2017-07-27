#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Definitions to generate table initialization files.
Used in scripts cm_init.py, cm_package.py
"""
from __future__ import absolute_import, division, print_function

import pandas as pd
from hera_mc import mc, geo_location, part_connect, cm_table_info, cm_utils
import os.path
import csv


def package_db_to_csv(session=None, tables='all', base=False, maindb=False):
    """
    This will get the configuration management tables from the database
       and package them to csv files to be read by initialize_db_from_csv

    Parameters:
    ------------
    session: Session object
        session on current database. If session is None, a new session
             on the default database is created and used.
    tables: string
        comma-separated list of names of tables to initialize or 'all'. Default is 'all'
    base: boolean
        use base set of initialization data files. Default is False
    maindb: boolean or string
        Either False or a user-generated key to change from main db. Default is False
    """
    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()

    tmp_filename = '__tmp_initfile.tmp'

    if base:
        data_prefix = cm_table_info.base_data_prefix
    else:
        data_prefix = cm_table_info.data_prefix
    cm_tables = cm_table_info.cm_tables

    if tables == 'all':
        tables_to_write = cm_tables.keys()
    else:
        tables_to_write = tables.split(',')

    print("Writing packaged files to current directory.  Copy to hera_mc/data to distribute.")
    for table in tables_to_write:
        data_filename = data_prefix + table + '.csv'
        table_data = pd.read_sql_table(table, session.get_bind())
        if maindb:
            print("\tPackaging for maindb:  " + data_filename)
            table_data.to_csv(tmp_filename, index=False)
        else:
            print("\tPackaging:  " + data_filename)
            table_data.to_csv(data_filename, index=False)
        if maindb:  # Put key in first line
            fpout = open(data_filename, 'w')
            fpin = open(tmp_filename, 'r')
            keyline = '$_maindb_$:' + maindb + '\n'
            fpout.write(keyline)
            for line in fpin:
                fpout.write(line)
            fpin.close()
            fpout.close()
            os.remove(tmp_filename)


def initialize_db_from_csv(session=None, tables='all', base=False, maindb=False):
    """
    This entry module provides a double-check entry point to read the csv files and
       repopulate the configuration management database.  It destroys all current entries,
       hence the double-check

    Parameters:
    ------------
    session: Session object
        session on current database. If session is None, a new session
             on the default database is created and used.
    tables: string
        comma-separated list of names of tables to initialize or 'all'. Default is 'all'
    base: boolean
        use base set of initialization data files. Default is False
    maindb: boolean or string
        Either False or a user-generated key to change from main db. Default is False
    """

    print("This will erase and rewrite the configuration management tables.")
    you_are_sure = cm_utils._query_yn("Are you sure you want to do this? ", 'n')
    if you_are_sure:
        success = _initialization(session=session, tables=tables, base=base, maindb=maindb)
    else:
        print("Exit with no rewrite.")
        success = False
    return success


def check_if_main():
    import socket
    return (socket.gethostname() == 'per210-1')


def check_if_db_location_agrees(maindb_flagged):
    # the 'hostname' call on qmaster returns the following value:
    is_maindb = check_if_main()

    if maindb_flagged and not is_maindb:
        print('Error:  attempting main db access to remote db')
        success = False
    elif not maindb_flagged and is_maindb:
        print('Error:  attempting unkeyed access to main db')
        success = False
    else:
        success = True
    return success


def check_csv_file_and_get_key(data_filename):
    try:
        fp = open(data_filename, 'r')
    except IOError:
        return None
    firstline = fp.readline()
    if firstline.split(':')[0] == '$_maindb_$':
        dbkey = firstline.split(':')[1].strip()
    else:
        dbkey = '$_remote_$'
    fp.close()
    return dbkey


def _initialization(session=None, tables='all', base=False, maindb=False):
    """
    Internal initialization method, should be called via initialize_db_from_csv

    Parameters:
    ------------
    session: Session object
        session on current database. If session is None, a new session
             on the default database is created and used.
    tables: string
        comma-separated list of names of tables to initialize or 'all'. Default is 'all'
    base: boolean
        use base set of initialization data files. Default is False
    maindb: boolean or string
        Either False or a user-generated key to change from main db. Default is False
    """
    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()

    # Check that db flag and actual db agree for remote v main
    success = check_if_db_location_agrees(maindb)
    if not success:
        return success

    if tables != 'all':
        print("You may encounter foreign_key issues by not using 'all' tables.")
        print("If it doesn't complain though you should be ok.")
    # Get tables to deal with in proper order
    cm_tables = cm_table_info.cm_tables
    if tables == 'all':
        tables_to_read_unordered = cm_tables.keys()
    else:
        tables_to_read_unordered = tables.split(',')
    tables_to_read = cm_table_info.order_the_tables(tables_to_read_unordered)
    if base:
        data_prefix = cm_table_info.base_data_prefix
    else:
        data_prefix = cm_table_info.data_prefix

    # Check tables and reduce list to valid use_table
    use_table = list(tables_to_read)
    keyed_file = {}
    for table in tables_to_read:
        data_filename = os.path.join(mc.data_path, data_prefix + table + '.csv')
        dbkey = check_csv_file_and_get_key(data_filename)
        if not dbkey:
            print('Initialization for %s not found' % (table))
            use_table.remove(table)
        else:
            if maindb:
                if dbkey != maindb:
                    print('Invalid maindb key for %s  (%s)' % (table, dbkey))
                    use_table.remove(table)
                else:
                    keyed_file[table] = True
            else:
                keyed_file[table] = False
                if dbkey != '$_remote_$':
                    print('Allowing maindb access for remotedb table: ', table)
                    keyed_file[table] = True
    if len(use_table) != len(tables_to_read):
        print("All of the tables weren't valid to change, so for now none will be.")
        print("This will likely be changed in the future, but for now caution abounds.")
        print("(This possibility is why 'use_table' and 'tables_to_read' are both there.)")
        print(use_table)
        print(tables_to_read)
        return False

    for table in use_table:
        num_rows_deleted = session.query(cm_tables[table][0]).delete()
        print("%d rows deleted in %s" % (num_rows_deleted, table))

    tables_to_init = list(reversed(use_table))
    # Initialize tables
    for table in tables_to_init:
        data_filename = os.path.join(mc.data_path, data_prefix + table + '.csv')
        cm_utils._log('cm_initialization: ' + data_filename)
        key_row = keyed_file[table]
        field_row = not key_row
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
                        elif 'gpstime' in field_name[i]:
                            # Needed since pandas does not have an integer representation
                            #  of NaN, so it outputs a float, which the database won't allow
                            r = int(float(r))
                        setattr(table_inst, field_name[i], r)
                    session.add(table_inst)
                    session.commit()
