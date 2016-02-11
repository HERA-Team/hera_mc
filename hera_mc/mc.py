import os
import sys
from sqlalchemy import Column, ForeignKey, BigInteger, String
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker, Session
import numpy as np
from astropy.time import Time
import math
import ephem

Base = None

test_db = 'postgresql://bryna:bryna@localhost:5432/test'
default_db = 'postgresql://bryna:bryna@localhost:5432/hera_mc'

HERA_LAT = '-30.721'
HERA_LON = '21.411'

class HeraObs(Base):
    __tablename__ = 'hera_obs'
    obsid = Column(BigInteger, primary_key=True)
    starttime = Column(DOUBLE_PRECISION, nullable=False)
    stoptime = Column(DOUBLE_PRECISION, nullable=False)
    lststart = Column(DOUBLE_PRECISION, nullable=False)

    def __repr__(self):
        return ("<HeraObs('{self.obsid}', '{self.starttime}', "
                "'{self.stoptime}', '{self.lststart}')>".format(self=self))

    def __eq__(self, other):
        return isinstance(other, HeraObs) and (
            other.obsid == self.obsid and
            np.allclose(other.starttime, self.starttime) and
            np.allclose(other.stoptime, self.stoptime) and
            np.allclose(other.lststart, self.lststart))


class DB():
    engine = None
    DBSession = sessionmaker()

    def __init__(self, base, db_name=None):
        Base = base
        self.engine = create_engine(db_name)
        self.DBSession.configure(bind=self.engine)

    def add_obs(self, starttime=None, stoptime=None):
        t_start = starttime.utc
        t_stop = stoptime.utc
        obsid = math.floor(t_start.gps)

        hera = ephem.Observer()
        hera.lon = HERA_LON
        hera.lat = HERA_LAT
        hera.date = t_start.datetime
        lst_start = float(repr(hera.sidereal_time()))/(15*ephem.degree)

        new_obs = HeraObs(obsid=obsid, starttime=t_start.jd,
                          stoptime=t_stop.jd, lststart=lst_start)

        self.DBsession.add(new_obs)
        self.DBsession.commit()
        self.DBsession.close()


    def get_obs(self, obsid=None, all=False):

        if all is True:
            obs_list = self.DBsession.query(HeraObs).all()
        else:
            obs_list = self.DBsession.query(HeraObs).filter_by(obsid=obsid).all()
        self.DBsession.close()

        nrows = len(obs_list)
        if nrows > 0:
            for row in obs_list:
                print(row.obsid, row.lststart)

        return obs_list


class DB_declarative(DB):
    engine = None
    DBSession = sessionmaker()

    def __init__(self, db_name=test_db):
        Base = declarative_base()
        super(DB, self, Base, db_name=db_name)

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        Base.metadata.bind = self.engine
        Base.metadata.drop_all(self.engine)



class DB_automap(DB):
    engine = None
    DBSession = sessionmaker()

    def __init__(self, db_name=default_db):
        Base = automap_base()
        super(DB, self, Base, db_name=db_name)
        self.Base.prepare(self.engine, reflect=True)
        self.DBSession.configure(bind=self.engine)
