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
