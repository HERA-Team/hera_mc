# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Connecting to and managing the M&C database.

See INSTALL.md in the Git repository for instructions on how to initialize
your database and configure M&C to find it.

"""
from __future__ import absolute_import, division, print_function

import os.path as op
import sys
from abc import ABCMeta
from six import add_metaclass
from sqlalchemy import Column, ForeignKey, BigInteger, String, Float
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy import update
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker, Session
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation, Angle
import math
# from astropy.utils import iers
import hera_mc

from . import MCDeclarativeBase

data_path = op.join(op.split(op.abspath(hera_mc.__file__))[0], 'data')

HERA_LAT = Angle('-30d43m17.5s').degree
HERA_LON = Angle('21d25m41.9s').degree
"value taken from capo/cals/hsa7458_v000.py, comment reads KAT/SA  (GPS)"
default_config_file = op.expanduser('~/.hera_mc/mc_config.json')
# iers_a = iers.IERS_A.open(op.join(data_path, 'finals.all'))


class MCSession(Session):

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etb):
        if etype is not None:
            self.rollback()  # exception raised
        else:
            self.commit()  # success
        self.close()
        return False  # propagate exception if any occurred

    def get_obs(self, obsid=None):
        """
        Get observation(s) from the M&C database.

        Parameters:
        ------------
        obsid: long integer
            observation identification number, generally the gps second
            corresponding to the observation start time.
            if not set, all obsids will be returned.

        Returns:
        --------
        list of Observation objects
        """
        from .observations import Observation

        if obsid is None:
            obs_list = self.query(Observation).all()
        else:
            obs_list = self.query(Observation).filter_by(obsid=obsid).all()

        return obs_list

    def get_paper_temps(self, starttime, stoptime=None):
        """
        get sets of temperature records.

        If only starttime is specified, get first record after starttime,
           if both starttime and stoptime are specified, get records between
           starttime and stoptime.

        Parameters:
        ------------
        starttime: float or astropy time object
            if float: jd time of starttime

        stoptime: float or astropy time object
            if float: jd time of temperature read

        """
        from .temperatures import PaperTemperatures

        if isinstance(starttime, Time):
            t_start = starttime.utc
        elif isinstance(starttime, float):
            t_start = Time(starttime, format='jd', scale='utc')
        else:
            raise ValueError('unrecognized "starttime" value: %r' % (starttime,))

        if stoptime is not None:
            if isinstance(stoptime, Time):
                t_stop = stoptime.utc
            elif isinstance(starttime, float):
                t_stop = Time(stoptime, format='jd', scale='utc')
            else:
                raise ValueError('unrecognized "stoptime" value: %r' % (stoptime,))

        if stoptime is not None:
            ptemp_list = self.query(PaperTemperatures).filter(
                PaperTemperatures.gps_time.between(t_start.gps, t_stop.gps)).all()
        else:
            ptemp_list = self.query(PaperTemperatures).filter(
                PaperTemperatures.gps_time >= t_start.gps).order_by(
                    PaperTemperatures.gps_time).limit(1).all()

        return ptemp_list

    def get_station_meta(self):
        """
        returns a dictionary of sub-arrays
             [prefix]{'Description':'...', 'plot_marker':'...', 'stations':[]}
        """
        from .geo_location import GeoLocation
        from .geo_location import StationMeta

        station_data = self.query(StationMeta).all()
        stations = {}
        for sta in station_data:
            stations[sta.prefix] = {'Name': sta.meta_class_name, 'Description': sta.description, 
                                    'Marker': sta.plot_marker, 'Stations': []}
        locations = self.query(GeoLocation).all()
        for loc in locations:
            for k in stations.keys():
                if loc.station_name[:len(k)] == k:
                    stations[k]['Stations'].append(loc.station_name)
        return stations


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

        from .db_check import is_sane_database

        with self.sessionmaker() as session:
            if not is_sane_database(MCDeclarativeBase, session):
                raise RuntimeError('database {0} does not match expected schema'.format(db_url))

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


def connect_to_mc_db(args, forced_db_name=None):
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
            raise RuntimeError('cannot connect to M&C database: no DB name provided, and no '
                               'default listed in {0!r}'.format(config_path))

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
                           'the DB named {1!r} in {2!r}'.format(db_mode, db_name, config_path))

    return db


def connect_to_mc_testing_db(forced_db_name='testing'):
    return connect_to_mc_db(None, forced_db_name=forced_db_name)
