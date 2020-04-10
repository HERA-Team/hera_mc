# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import numpy as np
import numpy.testing as npt

from astropy.time import Time
from astropy.units import Quantity

from .. import utils


def test_LSTScheduler_lstbinsize():
    """
    test that two bins have the right time separation
    """
    LSTbin_size = 10
    # pick a date far in the past just in case IERS is down
    starttime1 = Time('2015-9-19T05:05:05.0', format='isot', scale='utc')
    scheduletime1, hour1 = utils.LSTScheduler(starttime1, LSTbin_size)
    starttime2 = Time('2015-9-19T05:05:15.0', format='isot', scale='utc')
    scheduletime2, hour2 = utils.LSTScheduler(starttime2, LSTbin_size)
    assert np.isclose((hour2 - hour1).hour * 3600, LSTbin_size)
    # length of sidereal second in SI seconds.
    sidesec = Quantity(1, 'sday').to('day').value
    npt.assert_almost_equal((scheduletime2 - scheduletime1).value * 24 * 3600,
                            LSTbin_size * sidesec, decimal=5)


def test_LSTScheduler_multiday():
    """
    test that two bins are at the same LST on different days
    """
    LSTbin_size = 10
    # pick a date far in the past just in case IERS is down
    starttime1 = Time('2015-9-19T05:04:09.0', format='isot', scale='utc')
    scheduletime1, hour1 = utils.LSTScheduler(starttime1, LSTbin_size)
    # lst is 4 minutes earlier every day
    starttime2 = Time('2015-9-20T05:00:09.0', format='isot', scale='utc')
    scheduletime2, hour2 = utils.LSTScheduler(starttime2, LSTbin_size)
    assert np.isclose((hour2.hour - hour1.hour) * 3600, 0)
