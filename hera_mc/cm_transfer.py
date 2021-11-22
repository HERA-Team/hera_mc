#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Definitions to generate table initialization files.

Used in scripts cm_init.py, cm_pack.py
"""

import os.path
from math import floor
import subprocess
from astropy.time import Time
import csv
from sqlalchemy import Column, BigInteger, String

from . import MCDeclarativeBase, mc, cm_table_info, cm_utils


class CMVersion(MCDeclarativeBase):
    """
    Definition of cm_version table.

    This table simply stores the git hash of the repository to which the
    cm tables were packaged from the onsite database.

    For offsite & test databases, this table is populated by the cm initialization
    code using the git hash of the repository used for the initialization.

    Attributes
    ----------
    update_time : BigInteger Column
        gps time of the cm update (long integer) Primary key.
    git_hash : String Column
        cm repo git hash (String)

    """

    __tablename__ = "cm_version"
    update_time = Column(BigInteger, primary_key=True, autoincrement=False)
    git_hash = Column(String(64), nullable=False)

    @classmethod
    def create(cls, time, git_hash):
        """
        Create a new cm version object.

        Parameters
        ----------
        time: astropy time object
            time of update
        git_hash: String
            git hash of cm repository

        Returns
        -------
        object
            cm_version object with time/git_hash
        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object")
        time = int(floor(time.gps))

        # In Python 3, we sometimes get Unicode, sometimes bytes
        if isinstance(git_hash, bytes):
            git_hash = git_hash.decode("utf8")

        return cls(update_time=time, git_hash=git_hash)


def package_db_to_csv(session=None, tables="all"):
    """
    Get the configuration management tables and package them to csv files.

    The csv files are read by initialize_db_from_csv.

    Parameters
    ----------
    session : object or None
        session on current database. If session is None, a new session
        on the default database is created and used.
    tables: string
        comma-separated list of names of tables to initialize or 'all'.

    Returns
    -------
    list
        list of filenames written

    """
    import pandas

    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()

    data_prefix = cm_table_info.data_prefix
    cm_tables = cm_table_info.cm_tables

    if tables == "all":
        tables_to_write = cm_tables.keys()
    else:
        tables_to_write = tables.split(",")

    print("Writing packaged files to current directory.")
    print(
        "--> If packing from qmaster, be sure to use 'cm_pack.py --go' to "
        "copy, commit and log the change."
    )
    print("    Note:  this works via the hera_cm_db_updates repo.")
    files_written = []
    for table in tables_to_write:
        data_filename = data_prefix + table + ".csv"
        table_data = pandas.read_sql_table(table, session.get_bind())
        print("\tPackaging:  " + data_filename)
        table_data.to_csv(data_filename, index=False)
        files_written.append(data_filename)
    return files_written


def pack_n_go(session, cm_csv_path):  # pragma: no cover
    """
    Move the csv files to the distribution directory, commit them and update the hash.

    Puts the new commit hash into the M&C database

    Parameters
    ----------
    cm_csv_path : str
        Path to csv distribution directory

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


def initialize_db_from_csv(
    session=None, tables="all", maindb=False, testing=False, cm_csv_path=None
):  # pragma: no cover
    """
    Read the csv files and repopulate the configuration management database.

    This entry module provides a double-check entry point to read the csv files and
    repopulate the configuration management database.  It destroys all current entries,
    hence the double-check

    Parameters
    ----------
    session: Session object
        session on current database. If session is None, a new session
        on the default database is created and used.
    tables: str
        comma-separated list of names of tables to initialize or 'all'.
    maindb: bool or str
        Either False or the password to change from main db.
    testing : bool
        Flag to cover testing
    cm_csv_path : str or None
        Path where the csv files reside.  If None uses default.

    Returns
    -------
    bool
        Success, True or False

    """
    print("This will erase and rewrite the configuration management tables.")
    you_are_sure = input("Are you sure you want to do this (y/n)? ")
    if you_are_sure == "y":
        success = _initialization(
            session=session,
            cm_csv_path=cm_csv_path,
            tables=tables,
            maindb=maindb,
            testing=testing,
        )
    else:
        print("Exit with no rewrite.")
        success = False
    return success


def check_if_main(
    session, config_path=None, expected_hostname="qmaster", test_db_name="testing"
):
    """
    Determine if the code is running on the site main computer or not.

    Parameters
    ----------
    session : object
        Session object required
    config_path : str or None
        Full path to location of config file.  Default is None, which goes to default path.
    expected_hostname : str
        Name of the expected main host.  Default is 'qmaster'
    test_db_name : str
        Name of test database.  Default is 'testing'

    Returns
    -------
    bool
        True if main host, False if not.

    """
    # the 'hostname' call on qmaster returns the following value:
    import socket
    import json

    if isinstance(session, str) and session == "testing_not_main":
        return False
    if isinstance(session, str) and session == "testing_main":
        return True

    hostname = socket.gethostname()
    is_main_host = hostname == expected_hostname

    session_db_url = session.bind.engine.url.render_as_string(hide_password=False)

    if config_path is None:
        config_path = mc.default_config_file

    with open(config_path) as f:
        config_data = json.load(f)

    testing_db_url = config_data.get("databases").get(test_db_name).get("url")
    is_test_db = session_db_url == testing_db_url

    if is_main_host:  # pragma: no cover
        if is_test_db:
            is_main_db = False
        else:
            is_main_db = True
    else:
        is_main_db = False

    if is_main_db:  # pragma: no cover
        print(
            "Found main db at hostname {} and DB url {}".format(
                hostname, session_db_url
            )
        )
    return is_main_db


def db_validation(maindb_pw, session):
    """
    Check if you are working on the main db and if so if you have the right password.

    Parameters
    ----------
    maindb_pw : str
        password to allow access to main
    session : object
        Session object

    Returns
    -------
    bool
        True means you are allowed to modify main database.  False not.

    """
    is_maindb = check_if_main(session)

    if not is_maindb:
        return True

    if maindb_pw is False:
        raise ValueError("Error:  attempting access to main db without a password")
    if maindb_pw != "pw4maindb":
        raise ValueError("Error:  incorrect password for main db")

    return True


def _initialization(
    session=None, cm_csv_path=None, tables="all", maindb=False, testing=False
):
    """
    Initialize the database.

    This is an internal initialization method, it should be called via initialize_db_from_csv.

    Parameters
    ----------
    session : Session object
        session on current database. If session is None, a new session
             on the default database is created and used.
    tables : str
        comma-separated list of names of tables to initialize or 'all'.
    maindb : bool or str
        Either False or password to change from main db.
    testing : bool
        Flag to allow for testing.

    Returns
    -------
    bool
        Success, True or False

    """
    if session is None:  # pragma: no cover
        db = mc.connect_to_mc_db(None)
        session = db.sessionmaker()
    if cm_csv_path is None:
        cm_csv_path = mc.get_cm_csv_path(mc_config_file=None, testing=testing)

    if not db_validation(maindb, session):
        print("cm_init not allowed.")
        return False

    cm_git_hash = cm_utils.get_cm_repo_git_hash(
        cm_csv_path=cm_csv_path, testing=testing
    )

    if tables != "all":  # pragma: no cover
        print("You may encounter foreign_key issues by not using 'all' tables.")
        print("If it doesn't complain though you should be ok.")

    # Get tables to deal with in proper order
    cm_tables = cm_table_info.cm_tables
    if tables == "all":
        tables_to_read_unordered = cm_tables.keys()
    else:  # pragma: no cover
        tables_to_read_unordered = tables.split(",")
    tables_to_read = cm_table_info.order_the_tables(tables_to_read_unordered)
    data_prefix = cm_table_info.data_prefix

    use_table = []
    for table in tables_to_read:
        csv_table_name = data_prefix + table + ".csv"
        use_table.append([table, os.path.join(cm_csv_path, csv_table_name)])

    # add this cm git hash to cm_version table
    session.add(CMVersion.create(Time.now(), cm_git_hash))

    # Delete tables in this order
    for table, data_filename in use_table:
        num_rows_deleted = session.query(cm_tables[table][0]).delete()
        print("%d rows deleted in %s" % (num_rows_deleted, table))

    # Initialize tables in reversed order
    for table, data_filename in reversed(use_table):
        cm_utils.log("cm_initialization: " + data_filename)
        field_row = True  # This is the first row
        with open(data_filename, "rt") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                table_inst = cm_tables[table][0]()
                if field_row:
                    field_name = row
                    field_row = False
                else:
                    for i, r in enumerate(row):
                        if r == "":
                            r = None
                        elif "gpstime" in field_name[i]:
                            # Needed since pandas does not have an integer representation
                            #  of NaN, so it outputs a float, which the database won't allow
                            r = int(float(r))
                        setattr(table_inst, field_name[i], r)
                    session.add(table_inst)
                    session.commit()
