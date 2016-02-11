from astropy.time import Time
import math
import ephem

from hera_mc.db_setup import HeraObs

HERA_LAT = '-30.721'
HERA_LON = '21.411'


def add_obs(starttime=None, stoptime=None, session=None):
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

    session.add(new_obs)
    session.commit()
    session.close()


def get_obs(obsid=None, all=False, session=None):

    if all is True:
        obs_list = session.query(HeraObs).all()
    else:
        obs_list = session.query(HeraObs).filter_by(obsid=obsid).all()
    session.close()

    nrows = len(obs_list)
    if nrows > 0:
        for row in obs_list:
            print(row.obsid, row.lststart)

    return obs_list
