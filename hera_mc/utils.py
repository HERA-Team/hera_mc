# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.
"""
Common utility fuctions

"""
from __future__ import absolute_import, division, print_function

import collections
from math import floor
import six
from astropy.time import Time


if six.PY2:
    def str_to_bytes(s):
        return s

    def bytes_to_str(b):
        return b
else:
    def str_to_bytes(s):
        return s.encode('utf8')

    def bytes_to_str(b):
        return b.decode('utf8')

from astropy.time import Time
from astropy.time import TimeDelta
from astropy import coordinates as coord
from astropy import units as u
import numpy as np
import datetime



def LSTScheduler(starttime, LSTbin_size, longitude=21.25):
    """
    Round a time to the nearest LST bin.

    LSTbins start at 0 and step according to LSTbin_size.

    Inputs:
        starttime: astropy time object
        LSTbin_size: lst bin size in seconds
        longitude: degrees

    Returns:
        time of nearest lst bin (astropy.time.Time), lst bin in hours (astropy.coord.Angle)
    """

    sidesec = u.Quantity(1, 'sday').to('day').value  # length of sidereal second in SI seconds.
    locate = coord.EarthLocation(lon=longitude * u.deg, lat=-30 * u.deg)  # HERA location, #XXX get the HERA location programmatically
        raise TypeError("starttime is not a valid Astropy Time object")
    starttime.location = locate
    numChunks=(24*60*60)/LSTbin_size #seconds in a day
    lstGrid=np.linspace(0,int(numChunks), int(numChunks)+1, dtype=int) * LSTbin_size
    hmsList=[None]*(int(numChunks+1))

    #convert the grid in seconds to HMS
    for i, sec in enumerate(lstGrid): #make a grid of our evenly chunked LST times starting from 00h00m00s on the current day
        hrs=int(lstGrid[i]/3600)
        mins=int((lstGrid[i]%3600)/60)
        secs=int(lstGrid[i]-int(hrs*3600)-int(mins*60))
        if hrs==24: hrs=int(0)
        hms_str='%02dh%02dm%02ds' % (hrs,mins,secs)
        hmsList[i]=hms_str
    lstAngleGrid=coord.Angle(hmsList) #turn LST grid into angle array
    for i, hour in enumerate(lstAngleGrid):
        if hour>=starttime.sidereal_time('apparent'): #Find the timeslot our target is in
            diffSide=hour-starttime.sidereal_time('apparent') #get difference in sidereal
            diffSecs=diffSide.hms[2]*sidesec #convert difference to SI seconds
            break
    dt=TimeDelta((diffSecs), format='sec')
    scheduleTime=starttime+dt #adjust target time by difference to get start time
    return scheduleTime,hour



def calculate_obsid(starttime):
    """
    Create a new obsid using Astropy to compute the gps second.

    Parameters:
    ------------
    starttime: astropy time object
      observation starttime

    Returns:
    --------
    obid
    """
    if not isinstance(starttime, Time):
        raise ValueError('starttime must be an astropy Time object')

    return int(floor(starttime.gps))


def get_iterable(x):
    """Helper function to ensure iterability."""
    if isinstance(x, str):
        return (x,)
    else:
        try:
            iter(x)
        except TypeError:
            return (x,)
    return x


def _reraise_context(fmt, *args):
    """Reraise an exception with its message modified to specify additional context.

    This function tries to help provide context when a piece of code
    encounters an exception while trying to get something done, and it wishes
    to propagate contextual information farther up the call stack. It is a
    consistent way to do it for both Python 2 and 3, since Python 2 does not
    provide Python 3’s `exception chaining <https://www.python.org/dev/peps/pep-3134/>`_ functionality.
    Instead of that more sophisticated infrastructure, this function just
    modifies the textual message associated with the exception being raised.
    If only a single argument is supplied, the exception text is prepended with
    the stringification of that argument. If multiple arguments are supplied,
    the first argument is treated as an old-fashioned ``printf``-type
    (``%``-based) format string, and the remaining arguments are the formatted
    values.
    Borrowed from pwkit (https://github.com/pkgw/pwkit/blob/master/pwkit/__init__.py)
    Example usage::
      from hera_mc.utils import reraise_context
      filename = 'my-filename.txt'
      try:
        f = filename.open('rt')
        for line in f.readlines():
          # do stuff ...
      except Exception as e:
        reraise_context('while reading "%r"', filename)
        # The exception is reraised and so control leaves this function.
    If an exception with text ``"bad value"`` were to be raised inside the
    ``try`` block in the above example, its text would be modified to read
    ``"while reading \"my-filename.txt\": bad value"``.
    """
    import sys

    if len(args):
        cstr = fmt % args
    else:
        cstr = six.text_type(fmt)

    ex = sys.exc_info()[1]

    if isinstance(ex, EnvironmentError):
        ex.strerror = '%s: %s' % (cstr, ex.strerror)
        ex.args = (ex.errno, ex.strerror)
    else:
        if len(ex.args):
            cstr = '%s: %s' % (cstr, ex.args[0])
        ex.args = (cstr, ) + ex.args[1:]

    raise
