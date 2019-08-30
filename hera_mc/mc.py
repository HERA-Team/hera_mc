# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Setup and manage the M&C database.

See INSTALL.md in the Git repository for instructions on how to initialize
your database and configure M&C to find it.

"""
from __future__ import absolute_import, division, print_function

import os.path as op
import os
import sys
from abc import ABCMeta
from six import add_metaclass
from sqlalchemy import create_engine, update
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker, Session

from . import MCDeclarativeBase
from .mc_session import MCSession

data_path = op.join(op.dirname(__file__), 'data')
test_data_path = op.join(data_path, 'test_data')
default_config_file = op.expanduser('~/.hera_mc/mc_config.json')
mc_log_file = op.expanduser('~/.hera_mc/mc_log.txt')
cm_log_file = op.expanduser('~/.hera_mc/cm_log.txt')


@add_metaclass(ABCMeta)
class DB(object):
    """Abstract base class for M&C database object.

    This ABC is only instantiated through the AutomappedDB or DeclarativeDB
    subclasses.

    """
    engine = None
    sessionmaker = sessionmaker(class_=MCSession)
    sqlalchemy_base = None

    def __init__(self, sqlalchemy_base, db_url):
        self.sqlalchemy_base = MCDeclarativeBase
        self.engine = create_engine(db_url)
        self.sessionmaker.configure(bind=self.engine)


class DeclarativeDB(DB):
    """
    Declarative M&C database object -- to create M&C database tables
    """

    def __init__(self, db_url):
        super(DeclarativeDB, self).__init__(MCDeclarativeBase, db_url)

    def create_tables(self):
        """Create all M&C tables"""
        self.sqlalchemy_base.metadata.create_all(self.engine)

    def drop_tables(self):
        """Drop all M&C tables"""
        self.sqlalchemy_base.metadata.bind = self.engine
        self.sqlalchemy_base.metadata.drop_all(self.engine)


class AutomappedDB(DB):
    """Automapped M&C database object -- attaches to an existing M&C database.

    This is intended for use with the production M&C database. __init__()
    raises an exception if the existing database does not match the schema
    defined in the SQLAlchemy initialization magic.

    """

    def __init__(self, db_url):
        super(AutomappedDB, self).__init__(automap_base(), db_url)

        from .db_check import is_valid_database

        with self.sessionmaker() as session:
            if not is_valid_database(MCDeclarativeBase, session):
                raise RuntimeError('database {0} does not match expected schema'
                                   .format(db_url))


def get_mc_argument_parser():
    """Get an `argparse.ArgumentParser` object that includes some predefined
    arguments global to all scripts that interact with the M&C system.

    Currently, these are the path to the M&C config file, and the name of the
    M&C database connection to use.

    Once you have parsed arguments, you can pass the resulting object to a
    function like `connect_to_mc_db()` to automatically use the settings it
    encodes.

    """
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('--config', dest='mc_config_path', type=str,
                   default=default_config_file,
                   help='Path to the mc_config.json configuration file.')
    p.add_argument('--db', dest='mc_db_name', type=str,
                   help='Name of the database to connect to. The default is used if unspecified.')
    return p


def get_cm_csv_path(mc_config_file=None, testing=False):
    """
    Returns the full path to csv files read from the mc config file

    Parameters:
    -------------
    mc_config_file:  pass a different config file if desired.  None goes to default.
    """

    if mc_config_file is None:
        mc_config_file = default_config_file

    import json

    with open(mc_config_file) as f:
        config_data = json.load(f)

    if testing:
        return test_data_path

    try:
        cm_csv_path = '/{}'.format(config_data.get('databases')['hera_mc_sqlite']['url'].lstrip('sqlite:////').rstrip('/hera_mc.db'))
    except KeyError:
        cm_csv_path = config_data.get('cm_csv_path')
    return cm_csv_path


def connect_to_mc_db(args, forced_db_name=None, check_connect=True):
    """Return an instance of the `DB` class providing access to the M&C database.

    *args* should be the result of calling `parse_args` on an
     `argparse.ArgumentParser` instance created by calling
     `get_mc_argument_parser()`. Alternatively, it can be None to use the full
     defaults.

    """
    if args is None:
        config_path = default_config_file
        db_name = None
    else:
        config_path = args.mc_config_path
        db_name = args.mc_db_name

    if forced_db_name is not None:
        db_name = forced_db_name

    import json

    with open(config_path) as f:
        config_data = json.load(f)

    if db_name is None:
        db_name = config_data.get('default_db_name')
        if db_name is None:
            raise RuntimeError('cannot connect to M&C database: no DB name '
                               'provided, and no default listed in {0!r}'
                               .format(config_path))

    db_data = config_data.get('databases')
    if db_data is None:
        raise RuntimeError('cannot connect to M&C database: no "databases" '
                           'section in {0!r}'.format(config_path))

    db_data = db_data.get(db_name)
    if db_data is None:
        raise RuntimeError('cannot connect to M&C database: no DB named {0!r} in the '
                           '"databases" section of {1!r}'.format(db_name, config_path))

    db_url = db_data.get('url')
    if db_url is None:
        raise RuntimeError('cannot connect to M&C database: no "url" item for the DB '
                           'named {0!r} in {1!r}'.format(db_name, config_path))

    db_mode = db_data.get('mode')
    if db_mode is None:
        raise RuntimeError('cannot connect to M&C database: no "mode" item for the DB '
                           'named {0!r} in {1!r}'.format(db_name, config_path))

    if db_mode == 'testing':
        db = DeclarativeDB(db_url)
    elif db_mode == 'production':
        db = AutomappedDB(db_url)
    else:
        raise RuntimeError('cannot connect to M&C database: unrecognized mode {0!r} for'
                           'the DB named {1!r} in {2!r}'.format(db_mode, db_name,
                                                                config_path))

    if check_connect:
        # Test database connection
        with db.sessionmaker() as session:
            from . import db_check
            if not db_check.check_connection(session):
                raise RuntimeError('Could not establish valid connection to database.')

    return db


def connect_to_mc_testing_db(forced_db_name='testing'):
    return connect_to_mc_db(None, forced_db_name=forced_db_name)
