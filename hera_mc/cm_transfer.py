#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Definitions to generate table initialization files.
Used in scripts cm_init.py, cm_pack.py
"""
from __future__ import absolute_import, division, print_function

import os.path
from math import floor
from astropy.time import Time
import pandas as pd
import csv
from sqlalchemy import Column, BigInteger, String
from hera_mc import MCDeclarativeBase, mc, geo_location, part_connect, cm_table_info, cm_utils
import subprocess


class CMVersion(MCDeclarativeBase):
    """
    Definition of cm_version table. This table simply stores the git hash of the
        repository to which the cm tables were packaged from the onsite database.

    For offsite & test databases, this table is populated by the cm initialization
        code using the git hash of the repository used for the initialization.

    update_time: gps time of the cm update (long integer) Primary key.
    git_hash: cm repo git hash (String)
    """
    __tablename__ = 'cm_version'
    update_time = Column(BigInteger, primary_key=True, autoincrement=False)
    git_hash = Column(String(64), nullable=False)

    @classmethod
    def create(cls, time, git_hash):
        """
        Create a new cm version object.

        Parameters:
        ------------
        time: astropy time object
            time of update
        git_hash: String
            git hash of cm repository
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = int(floor(time.gps))

        return cls(update_time=time, git_hash=git_hash)


def package_db_to_csv(session=None, tables='all', base=False):
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
    """
    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()

    if base:
        data_prefix = cm_table_info.base_data_prefix
    else:
        data_prefix = cm_table_info.data_prefix
    cm_tables = cm_table_info.cm_tables

    if tables == 'all':
        tables_to_write = cm_tables.keys()
    else:
        tables_to_write = tables.split(',')

    print("Writing packaged files to current directory.")
    print("--> If packing from qmaster, be sure to use 'cm_pack.py --go' to copy, commit and log the change.")
    print("    Note:  this works via the hera_cm_db_updates repo.")
    for table in tables_to_write:
        data_filename = data_prefix + table + '.csv'
        table_data = pd.read_sql_table(table, session.get_bind())
        print("\tPackaging:  " + data_filename)
        table_data.to_csv(data_filename, index=False)


def pack_n_go(session, cm_csv_path):
    """
    This module will move the csv files to the distribution directory, commit them
    and put the new commit hash into the database

    Parameters:
    ------------
    cm_csv_path:  path to csv distribution directory
    """

    # move files over to dist dir
    cmd = "mv -f *.csv {}".format(cm_csv_path)
    subprocess.call(cmd, shell=True)

    # commit new csv files
    cmd = "git -C {} commit -am 'updating csv to repo.'".format(cm_csv_path)
    subprocess.call(cmd, shell=True)

    # get hash of this commit
    cm_git_hash = cm_utils.get_cm_repo_git_hash(cm_csv_path=cm_csv_path)

    # add this cm git hash to cm_version table
    session.add(CMVersion.create(Time.now(), cm_git_hash))
    session.commit()


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
        Either False or the password to change from main db. Default is False
    """

    print("This will erase and rewrite the configuration management tables.")
    you_are_sure = cm_utils._query_yn("Are you sure you want to do this? ", 'n')
    if you_are_sure:
        success = _initialization(session=session, cm_csv_path=None,
                                  tables=tables, base=base, maindb=maindb)
    else:
        print("Exit with no rewrite.")
        success = False
    return success


def check_if_main():
    # the 'hostname' call on qmaster returns the following value:
    import socket
    return (socket.gethostname() == 'per210-1')


def db_validation(maindb_pw):
    """
    Check if you are working on the main db and if so if you have the right password
    """
    is_maindb = check_if_main()

    if not is_maindb:
        return True

    allowed = True
    if maindb_pw is False:
        print('Error:  attempting access to main db without a password')
        allowed = False
    elif maindb_pw != 'pw4maindb':
        print('Error:  incorrect password for main db')
        allowed = False
    return allowed


def _initialization(session=None, cm_csv_path=None, tables='all', base=False,
                    maindb=False):
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
        Either False or password to change from main db. Default is False
    """
    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
    if cm_csv_path is None:
        cm_csv_path = mc.get_cm_csv_path(None)

    cm_git_hash = cm_utils.get_cm_repo_git_hash(cm_csv_path=cm_csv_path)

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

    use_table = []
    for table in tables_to_read:
        csv_table_name = data_prefix + table + '.csv'
        use_table.append([table, os.path.join(cm_csv_path, csv_table_name)])
    valid_to_proceed = db_validation(maindb)

    if not valid_to_proceed:
        return False

    # add this cm git hash to cm_version table
    session.add(CMVersion.create(Time.now(), cm_git_hash))

    # Delete tables in this order
    for table, data_filename in use_table:
        num_rows_deleted = session.query(cm_tables[table][0]).delete()
        print("%d rows deleted in %s" % (num_rows_deleted, table))

    # Initialize tables in reversed order
    for table, data_filename in reversed(use_table):
        cm_utils._log('cm_initialization: ' + data_filename)
        field_row = True  # This is the first row
        with open(data_filename, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                table_inst = cm_tables[table][0]()
                if field_row:
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
