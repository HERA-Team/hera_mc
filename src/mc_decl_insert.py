from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mc_declarative import HeraObs, Base

HERA_LAT = '-30.721'
HERA_LON = '21.411'

engine = create_engine('postgresql://bryna:bryna@localhost:5432/bryna')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

def add_obs(start_jd, stop_jd):
    t_start = Time(start_jd, scale='utc', format='jd')
    t_stop = Time(stop_jd, scale='utc', format='jd')
    obsid = math.floor(t_start.gps)

    hera = ephem.Observer()
    hera.lon = HERA_LON
    hera.lat = HERA_LAT
    hera.date = t_start
    lst_start = float(repr(hera.sidereal_time()))/(15*ephem.degree)

    new_obs = HeraObs(obsid=obsid, starttime=t_start.jd, stoptime=t_stop.jd,
                      lststart=lst_start)
    session.add(new_obs)
    session.commit()
