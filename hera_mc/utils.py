# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.
"""Common utility fuctions."""

from math import floor
from collections.abc import Iterable

from astropy.time import Time
from astropy.time import TimeDelta
from astropy import coordinates as coord
from astropy import units as u
import numpy as np


def LSTScheduler(starttime, LSTbin_size, longitude=21.25):
    """
    Round a time to the nearest LST bin for a given longitude on the globe.

    LSTbins run from 0 to 24 hours and step according to LSTbin_size.

    Parameters
    ----------
    starttime : astropy.time.Time
        Target schedule time.
    LSTbin_size : float
        LST bin size in seconds.
    longitude : float
        Telescope longitude in degrees.

    Returns
    -------
    schedule time :  astropy.time.Time
        Time of next LST bin.
    schedule sidereal time :  astropy.coord.Angle
        Sidereal time of next LST bin.

    """
    sidesec = (
        u.Quantity(1, "sday").to("day").value
    )  # length of sidereal second in SI seconds.
    # HERA location, #XXX get the HERA location programmatically
    locate = coord.EarthLocation(lon=longitude * u.deg, lat=-30 * u.deg)
    if not isinstance(starttime, Time):
        raise TypeError("starttime is not a valid Astropy Time object")
    starttime.location = locate
    numChunks = (24 * 60 * 60) / LSTbin_size  # seconds in a day
    lstGrid = (
        np.linspace(0, int(numChunks), int(numChunks) + 1, dtype=int) * LSTbin_size
    )
    hmsList = [None] * (int(numChunks + 1))

    # convert the grid in seconds to HMS
    # make a grid of our evenly chunked LST times starting from 00h00m00s on the current day
    for i, sec in enumerate(lstGrid):
        hrs = int(lstGrid[i] / 3600)
        mins = int((lstGrid[i] % 3600) / 60)
        secs = int(lstGrid[i] - int(hrs * 3600) - int(mins * 60))
        if hrs == 24:
            hrs = int(0)
        hms_str = "%02dh%02dm%02ds" % (hrs, mins, secs)
        hmsList[i] = hms_str
    lstAngleGrid = coord.Angle(hmsList)  # turn LST grid into angle array
    for i, hour in enumerate(lstAngleGrid):
        # Find the timeslot our target is in
        if hour >= starttime.sidereal_time("apparent"):
            # get difference in sidereal
            diffSide = hour - starttime.sidereal_time("apparent")
            # convert difference to SI seconds
            diffSecs = diffSide.hms[2] * sidesec
            break
    dt = TimeDelta((diffSecs), format="sec")
    scheduleTime = starttime + dt  # adjust target time by difference to get start time
    return scheduleTime, hour


def calculate_obsid(starttime):
    """
    Create a new obsid using Astropy to compute the gps second.

    Parameters
    ----------
    starttime : astropy.time.Time
      Observation starttime.

    Returns
    -------
    long
        obsid

    """
    if not isinstance(starttime, Time):
        raise ValueError("starttime must be an astropy Time object")

    return int(floor(starttime.gps))


def get_iterable(x):
    """Get an interable form of input."""
    if isinstance(x, str):
        return (x,)
    else:
        if isinstance(x, Iterable):
            return x
        else:
            return (x,)


def get_obsid_from_file(filename):
    """
    Extract obsid from a UVH5 file.

    This method assumes that the file is a UVH5 file, though there is no
    explicit checking done.

    Parameters
    ----------
    filename : str
        The full path to the file.

    Returns
    -------
    obsid : int
        The obsid of the file.

    """
    try:
        import h5py
    except ImportError:  # pragma: no cover
        msg = (
            "h5py is needed for `get_obsid_from_file`. Please install it "
            "explicitly or run `pip install .[all]` from the top-level of hera_mc."
        )
        raise ImportError(msg)
    with h5py.File(filename, "r") as h5f:
        time_array = h5f["Header/time_array"][()]
    t0 = np.unique(time_array)[0]
    time0 = Time(t0, format="jd", scale="utc")
    obsid = int(np.floor(time0.gps))
    return obsid
