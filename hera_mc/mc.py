# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Connecting to and managing the M&C database.

The database connection is specified in a configuration file. The default
location for this file is `~/.hera_mc/mc_config.json`. The structure of that
file should be of this form:

{
  "default_db_name": "sampledb",
  "databases": {
    "sampledb": {
      "url": "postgresql://user:pass@host:/db_name",
      "mode": "production"
    },
    "testing": {
      "url": "postgresql://user:pass@host:/test_db_name",
      "mode": "testing"
    }
  }
}

The test rig will always connect to a database named "testing", which must
have a "mode" of "testing" as well.

"""

from __future__ import absolute_import, division, print_function

import os.path as op
import sys
from abc import ABCMeta
from six import add_metaclass
from sqlalchemy import Column, ForeignKey, BigInteger, String, Float
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
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

data_path = op.join(op.dirname (hera_mc.__file__), 'data')

HERA_LAT = Angle('-30d43m17.5s').degree
HERA_LON = Angle('21d25m41.9s').degree
"value taken from capo/cals/hsa7458_v000.py, comment reads KAT/SA  (GPS)"
default_config_file = op.expanduser('~/.hera_mc/mc_config.json')
# iers_a = iers.IERS_A.open(op.join(data_path, 'finals.all'))


class HeraObs(MCDeclarativeBase):
    """
    Definition of hera_obs table.

    obsid: observation identification number, generally equal to the
        start time in gps seconds (long integer)
    starttime: observation start time in jd (float)
    stoptime: observation stop time in jd (float)
    lststart: observation start time in lst (float)
    """
    __tablename__ = 'hera_obs'
    obsid = Column(BigInteger, primary_key=True)
    start_time_jd = Column(DOUBLE_PRECISION, nullable=False)
    stop_time_jd = Column(DOUBLE_PRECISION, nullable=False)
    lst_start_hr = Column(DOUBLE_PRECISION, nullable=False)

    def __repr__(self):
        return ("<HeraObs('{self.obsid}', '{self.start_time_jd}', "
                "'{self.stop_time_jd}', '{self.lst_start_hr}')>".format(
                    self=self))

    def __eq__(self, other):
        return isinstance(other, HeraObs) and (
            other.obsid == self.obsid and
            np.allclose(other.start_time_jd, self.start_time_jd) and
            np.allclose(other.stop_time_jd, self.stop_time_jd) and
            np.allclose(other.lst_start_hr, self.lst_start_hr))


class PaperTemperatures(MCDeclarativeBase):
    """
    Definition of paper_temperatures table.

    gps_time: GPS second of observation (float)
    jd_time: JD time of observation (to 5 decimals, <0.05 sec accuracy) (float)
    balun_east: temperature at a balun east of the hut (float)
    cable_east: temperature of the underside of a feed cable east of the hut (float)
    balun_west: temperature at a balun west of the hut (float)
    cable_west: temperature of the underside of a feed cable west of the hut (float)
    rcvr_1a: 1st temperature in receiverator 1
    rcvr_1b: 2nd temperature in receiverator 1
    .
    .
    .
    rcvr_8a: 1st temperature in receiverator 8
    rcvr_8b: 2nd temperature in receiverator 8
    """
    __tablename__ = 'paper_temperatures'
    gps_time = Column(DOUBLE_PRECISION, nullable=False, primary_key=True)
    jd_time = Column(DOUBLE_PRECISION, nullable=False)
    balun_east = Column(Float)
    cable_east = Column(Float)
    balun_west = Column(Float)
    cable_west = Column(Float)
    rcvr_1a = Column(Float)
    rcvr_1b = Column(Float)
    rcvr_2a = Column(Float)
    rcvr_2b = Column(Float)
    rcvr_3a = Column(Float)
    rcvr_3b = Column(Float)
    rcvr_4a = Column(Float)
    rcvr_4b = Column(Float)
    rcvr_5a = Column(Float)
    rcvr_5b = Column(Float)
    rcvr_6a = Column(Float)
    rcvr_6b = Column(Float)
    rcvr_7a = Column(Float)
    rcvr_7b = Column(Float)
    rcvr_8a = Column(Float)
    rcvr_8b = Column(Float)

    def __repr__(self):
        return ("<PaperTemperatures('{self.gps_time}', '{self.jd_time}', "
                "'{self.balun_east}', '{self.cable_east}', "
                "'{self.balun_west}', '{self.cable_west}', "
                "'{self.rcvr_1a}', '{self.rcvr_1b}', "
                "'{self.rcvr_2a}', '{self.rcvr_2b}', "
                "'{self.rcvr_3a}', '{self.rcvr_3b}', "
                "'{self.rcvr_4a}', '{self.rcvr_4b}', "
                "'{self.rcvr_5a}', '{self.rcvr_5b}', "
                "'{self.rcvr_6a}', '{self.rcvr_6b}', "
                "'{self.rcvr_7a}', '{self.rcvr_7b}', "
                "'{self.rcvr_8a}', '{self.rcvr_8b}')>".format(self=self))

    def __eq__(self, other):
        if isinstance(other, PaperTemperatures):
            attribute_list = [a for a in dir(self) if not a.startswith('__') and
                              not callable(getattr(self, a))]
            isequal = True
            for a in attribute_list:
                if isinstance(a, Column):
                    self_col = getattr(self, a)
                    other_col = getattr(other, a)
                    if self_col != other_col:
                        print('column {col} does not match. Left is {lval} '
                              'and right is {rval}'.
                              format(col=a, lval=str(self_col),
                                     rval=str(other_col)))
                        isequal = False
            return isequal
        else:
            return False


class MCSession(Session):
    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etb):
        if etype is not None:
            self.rollback() # exception raised
        else:
            self.commit() # success
        self.close()
        return False # propagate exception if any occurred


    def add_obs(self, starttime, stoptime, obsid=None):
        """
        Add an observation to the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            observation starttime
        stoptime: astropy time object
            observation stoptime
        obsid: long integer
            observation identification number. If not provided, will be set
            to the gps second corresponding to the starttime using floor.
        """
        t_start = starttime.utc
        t_stop = stoptime.utc

        # t_start.delta_ut1_utc = iers_a.ut1_utc(t_start)
        # t_stop.delta_ut1_utc = iers_a.ut1_utc(t_stop)

        if obsid is None:
            obsid = math.floor(t_start.gps)

        t_start.location = EarthLocation.from_geodetic(HERA_LON, HERA_LAT)

        new_obs = HeraObs(obsid=obsid, start_time_jd=t_start.jd,
                          stop_time_jd=t_stop.jd,
                          lst_start_hr=t_start.sidereal_time('apparent').hour)

        self.add(new_obs)

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
        list of HeraObs objects
        """
        if obsid is None:
            obs_list = self.query(HeraObs).all()
        else:
            obs_list = self.query(HeraObs).filter_by(obsid=obsid).all()

        return obs_list

    def add_paper_temps(self, read_time, temp_list):
        """
        Add a set of temperature records to the paper_temperatures table.

        Parameters:
        ------------
        read_time: float or astropy time object
            if float: jd time of temperature read

        temp_list: List of temperatures as written to text file (see below,
            contains extra columns we don't save

        From the wiki: description of columns in text file: (temp list is cols 1-28)
        Col 0:   Julian date to 5 decimal places
        Col 1:   Balun East
        Col 2:   Cable East
        Col 3:   Balun West
        Col 4:   Cable West
        Col 5:   junk
        Col 6:   junk
        Col 7:   junk
        Col 8:   Rcvr 1-A
        Col 9:   Rcvr 1-B
        Col 10:  Rcvr 2-A
        Col 11:  Rcvr 2-B
        Col 12:  Rcvr 3-A
        Col 13:  Rcvr 3-B
        Col 14:  junk
        Col 15:  Rcvr 4-A
        Col 16:  Rcvr 4-B
        Col 17:  Rcvr 5-A
        Col 18:  Rcvr 5-B
        Col 19:  Rcvr 6-A
        Col 20:  Rcvr 6-B
        Col 21:  junk
        Col 22:  Rcvr 7-A
        Col 23:  Rcvr 7-B
        Col 24:  Rcvr 8-A
        Col 25:  Rcvr 8-B
        Col 26:  junk
        Col 27:  junk
        Col 28:  junk
        """
        if isinstance(read_time, Time):
            t_read = read_time.utc
        elif isinstance(read_time, float):
            t_read = Time(read_time, format='jd', scale='utc')
        else:
            raise ValueError('read_time can be an astropy Time object or a '
                             'jd time')

        temp_colnames = ['balun_east', 'cable_east',
                         'balun_west', 'cable_west',
                         'rcvr_1a', 'rcvr_1b', 'rcvr_2a', 'rcvr_2b',
                         'rcvr_3a', 'rcvr_3b', 'rcvr_4a', 'rcvr_4b',
                         'rcvr_5a', 'rcvr_5b', 'rcvr_6a', 'rcvr_6b',
                         'rcvr_7a', 'rcvr_7b', 'rcvr_8a', 'rcvr_8b']
        temp_indices = (np.array([1, 2, 3, 4, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18,
                                 19, 20, 22, 23, 24, 25]) - 1).tolist()

        temp_values = [temp_list[i] for i in temp_indices]

        temp_dict = dict(zip(temp_colnames, temp_values))

        new_ptemp = PaperTemperatures(gps_time=t_read.gps, jd_time=t_read.jd,
                                      **temp_dict)

        self.add(new_ptemp)

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
        if isinstance(starttime, Time):
            t_start = starttime.utc
        elif isinstance(starttime, float):
            t_start = Time(starttime, format='jd', scale='utc')

        if stoptime is not None:
            if isinstance(stoptime, Time):
                t_stop = stoptime.utc
            elif isinstance(starttime, float):
                t_stop = Time(stoptime, format='jd', scale='utc')

        if stoptime is not None:
            ptemp_list = self.query(PaperTemperatures).filter(
                PaperTemperatures.gps_time.between(t_start.gps, t_stop.gps)).all()
        else:
            ptemp_list = self.query(PaperTemperatures).filter(
                PaperTemperatures.gps_time >= t_start.gps).order_by(
                    PaperTemperatures.gps_time).limit(1).all()

        return ptemp_list


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
                raise RuntimeError('database {0} does not match expected schema'.format (db_url))


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
    p.add_argument ('--config', dest='mc_config_path', type=str,
                    default=default_config_file,
                    help='Path to the mc_config.json configuration file.')
    p.add_argument ('--db', dest='mc_db_name', type=str,
                    help='Name of the database to connect to. The default is used if unspecified.')
    return p


def connect_to_mc_db (args, forced_db_name=None):
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

    with open (config_path) as f:
        config_data = json.load (f)

    if db_name is None:
        db_name = config_data.get ('default_db_name')
        if db_name is None:
            raise RuntimeError ('cannot connect to M&C database: no DB name provided, and no '
                                'default listed in {0!r}'.format (config_path))

    db_data = config_data.get ('databases')
    if db_data is None:
        raise RuntimeError ('cannot connect to M&C database: no "databases" '
                            'section in {0!r}'.format (config_path))

    db_data = db_data.get (db_name)
    if db_data is None:
        raise RuntimeError ('cannot connect to M&C database: no DB named {0!r} in the '
                            '"databases" section of {1!r}'.format (db_name, config_path))

    db_url = db_data.get ('url')
    if db_url is None:
        raise RuntimeError ('cannot connect to M&C database: no "url" item for the DB '
                            'named {0!r} in {1!r}'.format (db_name, config_path))

    db_mode = db_data.get ('mode')
    if db_mode is None:
        raise RuntimeError ('cannot connect to M&C database: no "mode" item for the DB '
                            'named {0!r} in {1!r}'.format (db_name, config_path))

    if db_mode == 'testing':
        db = DeclarativeDB (db_url)
    elif db_mode == 'production':
        db = AutomappedDB (db_url)
    else:
        raise RuntimeError ('cannot connect to M&C database: unrecognized mode {0!r} for'
                            'the DB named {1!r} in {2!r}'.format (db_mode, db_name, config_path))

    return db


def connect_to_mc_testing_db(forced_db_name='testing'):
    return connect_to_mc_db(None, forced_db_name=forced_db_name)
