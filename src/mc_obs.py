
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from astropy.time import Time
import ephem
import math


def add_obs_mc(db_address, start_jd, stop_jd):
    Base = automap_base()
    engine = create_engine(db_address)
    Base.prepare(engine, reflect=True)
    hera_obs = Base.classes.hera_obs
    session = Session(engine)

    t_start = Time(start_jd, scale='utc', format='jd')
    t_stop = Time(stop_jd, scale='utc', format='jd')
    obsid = math.floor(t_start.gps)
    hera = ephem.Observer()
    hera.lon = '21.411'
    hera.lat = '-30.721'
    hera.date = t_start
    lst_start = float(repr(hera.sidereal_time()))/(15*ephem.degree)

    session.add(hera_obs(obsid=obsid, starttime=t_start.jd, stoptime=t_stop.jd,
                         lststart=lst_start))
    session.commit()

    # u1 = session.query(hera_obs).filter(hera_obs.obsid == obsid)
    # print(u1.obsid)
