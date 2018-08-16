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
import subprocess
import six
from astropy.time import Time
import pandas as pd
import csv
from sqlalchemy import Column, BigInteger, String

from . import MCDeclarativeBase, mc, cm_table_info, cm_utils, utils


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

        # In Python 3, we sometimes get Unicode, sometimes bytes
        if isinstance(git_hash, six.binary_type):
            git_hash = utils.bytes_to_str(git_hash)

        return cls(update_time=time, git_hash=git_hash)


def package_db_to_csv(session=None, tables='all'):
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
    """
    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()

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


def initialize_db_from_csv(session=None, tables='all', maindb=False):
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
    maindb: boolean or string
        Either False or the password to change from main db. Default is False
    """

    print("This will erase and rewrite the configuration management tables.")
    you_are_sure = cm_utils.query_yn("Are you sure you want to do this? ", 'n')
    if you_are_sure:
        success = _initialization(session=session, cm_csv_path=None,
                                  tables=tables, maindb=maindb)
    else:
        print("Exit with no rewrite.")
        success = False
    return success


def check_if_main(session, config_path=None, expected_hostname='qmaster',
                  test_db_name='testing'):
    # the 'hostname' call on qmaster returns the following value:
    import socket
    import json
    hostname = socket.gethostname()
    is_main_host = (hostname == expected_hostname)

    session_db_url = session.bind.engine.url

    if config_path is None:
        config_path = mc.default_config_file

    with open(config_path) as f:
        config_data = json.load(f)

    testing_db_url = config_data.get('databases').get(test_db_name)
    is_test_db = (session_db_url == testing_db_url)

    if is_main_host:
        if is_test_db:
            is_main_db = False
        else:
            is_main_db = True
    else:
        is_main_db = False

    if is_main_db:
        print('Found main db at hostname {} and DB url {}'.format(hostname, session_db_url))
    return is_main_db


def db_validation(maindb_pw, session):
    """
    Check if you are working on the main db and if so if you have the right password
    """
    is_maindb = check_if_main(session)

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


def _initialization(session=None, cm_csv_path=None, tables='all', maindb=False):
    """
    Internal initialization method, should be called via initialize_db_from_csv

    Parameters:
    ------------
    session: Session object
        session on current database. If session is None, a new session
             on the default database is created and used.
    tables: string
        comma-separated list of names of tables to initialize or 'all'. Default is 'all'
    maindb: boolean or string
        Either False or password to change from main db. Default is False
    """

    if session is None:
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
    if cm_csv_path is None:
        cm_csv_path = mc.get_cm_csv_path(None)

    if not db_validation(maindb, session):
        print("cm_init not allowed.")
        return False

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
    data_prefix = cm_table_info.data_prefix

    use_table = []
    for table in tables_to_read:
        csv_table_name = data_prefix + table + '.csv'
        use_table.append([table, os.path.join(cm_csv_path, csv_table_name)])

    # add this cm git hash to cm_version table
    session.add(CMVersion.create(Time.now(), cm_git_hash))

    # Delete tables in this order
    for table, data_filename in use_table:
        num_rows_deleted = session.query(cm_tables[table][0]).delete()
        print("%d rows deleted in %s" % (num_rows_deleted, table))

    # Initialize tables in reversed order
    for table, data_filename in reversed(use_table):
        cm_utils.log('cm_initialization: ' + data_filename)
        field_row = True  # This is the first row
        with open(data_filename, 'rt') as csvfile:
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
