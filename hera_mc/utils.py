# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.
"""
Common utility fuctions

"""
from astropy.time import Time
from math import floor
import collections


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
        if isinstance(x, collections.Iterable):
            return x
        else:
            return (x,)
