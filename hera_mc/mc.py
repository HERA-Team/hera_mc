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
    """Little function to read a JSON config file."""
    handle = open(config_file)
    config_dict = json.loads(handle.read())

    return config_dict['test_db'], config_dict['mc_db']


class HeraObs(DEC_BASE):
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

    def add_obs(self, obsid=None, starttime=None, stoptime=None, session=None):
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

    def get_obs(self, obsid=None, all=False, session=None):

        if session is None:
            session = self.DBSession()

        if all is True:
            obs_list = session.query(HeraObs).all()
        else:
            obs_list = session.query(HeraObs).filter_by(
                obsid=obsid).all()
        session.close()

        nrows = len(obs_list)
        if nrows > 0:
            for row in obs_list:
                print('obsid: ', row.obsid, ', LST start: ', row.lststart)

        return obs_list


class DB_declarative(DB):

    def __init__(self, config_file=default_config_file, use_test=True):
        self.Base = DEC_BASE
        super(DB_declarative, self).__init__(config_file=config_file,
                                             use_test=use_test)
        self.DBSession.configure(bind=self.engine)

    def create_tables(self):
        self.Base.metadata.create_all(self.engine)

    def drop_tables(self):
        self.Base.metadata.bind = self.engine
        self.Base.metadata.drop_all(self.engine)


class DB_automap(DB):

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
