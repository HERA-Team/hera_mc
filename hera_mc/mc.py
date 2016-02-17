import os
import sys
from abc import ABCMeta
from six import add_metaclass
from sqlalchemy import Column, ForeignKey, BigInteger, String
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker, Session
import numpy as np
from astropy.time import Time
import math
import ephem
import json
from hera_mc.db_check import DEC_BASE, is_sane_database

HERA_LAT = '-30.721'
HERA_LON = '21.411'
default_config_file = os.path.expanduser('~/.hera_mc/mc_config.json')


def get_configs(config_file=default_config_file):
    """
    Little function to read a JSON config file.

    Config files should be located at: ~/.hera_mc/mc_config.json
    They should contain three elements:
        location: string giving location (e.g "karoo")
        test_db: url for an empty testing database
        mc_db: url for the M&C database containing the M&C tables

    Example:
    {
    "location":"myloc",
    "mc_db":"postgresql://username:password@localhost:5432/hera_mc",
    "test_db":"postgresql://username:password@localhost:5432/test"
    }
    """
    handle = open(config_file)
    config_dict = json.loads(handle.read())

    return config_dict['test_db'], config_dict['mc_db']


class HeraObs(DEC_BASE):
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
    starttime = Column(DOUBLE_PRECISION, nullable=False)
    stoptime = Column(DOUBLE_PRECISION, nullable=False)
    lststart = Column(DOUBLE_PRECISION, nullable=False)

    def __repr__(self):
        return ("<HeraObs('{self.obsid}', '{self.starttime}', "
                "'{self.stoptime}', '{self.lststart}')>".format(
                    self=self))

    def __eq__(self, other):
        return isinstance(other, HeraObs) and (
            other.obsid == self.obsid and
            np.allclose(other.starttime, self.starttime) and
            np.allclose(other.stoptime, self.stoptime) and
            np.allclose(other.lststart, self.lststart))


@add_metaclass(ABCMeta)
class DB(object):
    """
    Abstract Base Class for M&C database object

    Should be instantiated using either:
        DB_automap: if attaching to an existing database
        DB_declarative: if setting up a database from scratch
    """
    test_db = None
    mc_db = None

    engine = None
    DBSession = sessionmaker()
    Base = None

    def __init__(self, config_file=default_config_file, use_test=True):
        test_db, mc_db = get_configs(config_file=config_file)
        if use_test is True:
            db_name = test_db
        else:
            db_name = mc_db
        self.engine = create_engine(db_name)

    def add_obs(self, starttime, stoptime, obsid=None, session=None):
        """
        Add an observation to the M&C database.

        Parameters:
        ------------
        starttime: astropy time object
            observation starttime
        starttime: astropy time object
            observation stoptime
        obsid: long integer
            observation identification number. If not provided, will be set
            to the gps second corresponding to the starttime using floor.
        session: sqlalchemy session object
            if not set, a session will be generated based on self.DBSession
        """
        t_start = starttime.utc
        t_stop = stoptime.utc

        if obsid is None:
            obsid = math.floor(t_start.gps)

        hera = ephem.Observer()
        hera.lon = HERA_LON
        hera.lat = HERA_LAT
        hera.date = t_start.datetime
        lst_start = float(repr(hera.sidereal_time()))/(15*ephem.degree)

        new_obs = HeraObs(obsid=obsid, starttime=t_start.jd,
                          stoptime=t_stop.jd, lststart=lst_start)

        if session is None:
            session = self.DBSession()

        session.add(new_obs)
        session.commit()
        session.close()

    def get_obs(self, obsid=None, session=None):
        """
        Get observation(s) from the M&C database.

        Parameters:
        ------------
        obsid: long integer
            observation identification number, generally the gps second
            corresponding to the observation start time.
            if not set, all obsids will be returned.
        session: sqlalchemy session object
            if not set, a session will be generated based on self.DBSession

        Returns:
        --------
        list of HeraObs objects
        """
        if session is None:
            session = self.DBSession()

        if obsid is None:
            obs_list = session.query(HeraObs).all()
        else:
            obs_list = session.query(HeraObs).filter_by(
                obsid=obsid).all()
        session.close()

        return obs_list


class DB_declarative(DB):
    """
    Declarative M&C database object -- to create M&C database tables
    """
    def __init__(self, config_file=default_config_file, use_test=True):
        self.Base = DEC_BASE
        super(DB_declarative, self).__init__(config_file=config_file,
                                             use_test=use_test)
        self.DBSession.configure(bind=self.engine)

    def create_tables(self):
        """Create all M&C tables"""
        self.Base.metadata.create_all(self.engine)

    def drop_tables(self):
        """Drop all M&C tables"""
        self.Base.metadata.bind = self.engine
        self.Base.metadata.drop_all(self.engine)


class DB_automap(DB):
    """
    Automap M&C database object -- to attach to an existing M&C database.

    Will fail to initialize if the database table structure does not match
        the table structure defined above.
    """
    def __init__(self, config_file=default_config_file, use_test=False):
        self.Base = automap_base()
        super(DB_automap, self).__init__(config_file=config_file,
                                         use_test=use_test)
        self.Base.prepare(self.engine, reflect=True)
        self.DBSession.configure(bind=self.engine)

        # initialization should fail if the automapped database does not
        # match the delarative base
        session = self.DBSession()
        assert is_sane_database(DEC_BASE, session)
