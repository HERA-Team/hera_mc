import os
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
from astropy.coordinates import EarthLocation
import math
import json
from hera_mc.db_check import DEC_BASE, is_sane_database
from astropy.utils import iers
import hera_mc

data_path = op.join(hera_mc.__path__[0], 'data')

HERA_LAT = '-30.721'
HERA_LON = '21.411'
default_config_file = os.path.expanduser('~/.hera_mc/mc_config.json')
iers_a = iers.IERS_A.open(op.join(data_path, 'finals.all'))


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


class PaperTemperatures(DEC_BASE):
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
        stoptime: astropy time object
            observation stoptime
        obsid: long integer
            observation identification number. If not provided, will be set
            to the gps second corresponding to the starttime using floor.
        session: sqlalchemy session object
            if not set, a session will be generated based on self.DBSession
        """
        t_start = starttime.utc
        t_stop = stoptime.utc

        t_start.delta_ut1_utc = iers_a.ut1_utc(t_start)
        t_stop.delta_ut1_utc = iers_a.ut1_utc(t_stop)

        if obsid is None:
            obsid = math.floor(t_start.gps)

        t_start.location = EarthLocation.from_geodetic(HERA_LON, HERA_LAT)

        new_obs = HeraObs(obsid=obsid, start_time_jd=t_start.jd,
                          stop_time_jd=t_stop.jd,
                          lst_start_hr=t_start.sidereal_time('apparent').hour)

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

    def add_paper_temps(self, read_time, temp_list, session=None):
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

        if session is None:
            session = self.DBSession()

        session.add(new_ptemp)
        session.commit()
        session.close()

    def get_paper_temps(self, starttime, stoptime=None, session=None):
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

        if session is None:
            session = self.DBSession()

        if stoptime is not None:
            ptemp_list = session.query(PaperTemperatures).filter(
                PaperTemperatures.gps_time.between(t_start.gps, t_stop.gps)).all()
        else:
            ptemp_list = session.query(PaperTemperatures).filter(
                PaperTemperatures.gps_time >= t_start.gps).order_by(
                    PaperTemperatures.gps_time).limit(1).all()
        session.close()

        return ptemp_list


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
