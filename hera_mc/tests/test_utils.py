# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import numpy as np
import numpy.testing as npt
import pytest

from astropy.time import Time
from astropy.units import Quantity

from .. import utils


def test_LSTScheduler_lstbinsize():
    """
    test that two bins have the right time separation
    """
    LSTbin_size = 10
    # pick a date far in the past just in case IERS is down
    starttime1 = Time("2015-9-19T05:05:05.0", format="isot", scale="utc")
    scheduletime1, hour1 = utils.LSTScheduler(starttime1, LSTbin_size)
    starttime2 = Time("2015-9-19T05:05:15.0", format="isot", scale="utc")
    scheduletime2, hour2 = utils.LSTScheduler(starttime2, LSTbin_size)
    assert np.isclose((hour2 - hour1).hour * 3600, LSTbin_size)
    # length of sidereal second in SI seconds.
    sidesec = Quantity(1, "sday").to("day").value
    npt.assert_almost_equal(
        (scheduletime2 - scheduletime1).value * 24 * 3600,
        LSTbin_size * sidesec,
        decimal=5,
    )

    with pytest.raises(TypeError, match="starttime is not a valid Astropy Time object"):
        utils.LSTScheduler("foo", LSTbin_size)


def test_LSTScheduler_multiday():
    """
    test that two bins are at the same LST on different days
    """
    LSTbin_size = 10
    # pick a date far in the past just in case IERS is down
    starttime1 = Time("2015-9-19T05:04:09.0", format="isot", scale="utc")
    scheduletime1, hour1 = utils.LSTScheduler(starttime1, LSTbin_size)
    # lst is 4 minutes earlier every day
    starttime2 = Time("2015-9-20T05:00:09.0", format="isot", scale="utc")
    scheduletime2, hour2 = utils.LSTScheduler(starttime2, LSTbin_size)
    assert np.isclose((hour2.hour - hour1.hour) * 3600, 0)


def test_get_iterable():
    assert utils.get_iterable(2) == (2,)
    assert utils.get_iterable([2]) == [2]
    assert utils.get_iterable([2, 3]) == [2, 3]
    assert utils.get_iterable("foo") == ("foo",)
    assert utils.get_iterable(["foo"]) == ["foo"]
    assert utils.get_iterable(["foo", "bar"]) == ["foo", "bar"]


def test_get_obsid_from_file(tmp_path):
    """
    Test the get_obsid_from_file function; requires h5py.
    """
    h5py = pytest.importorskip("h5py")

    # make a fake time array
    jd0 = 2457000
    t0 = Time(jd0, format="jd", scale="utc")
    times = np.linspace(jd0, jd0 + 0.5, num=10)
    output_file = str(tmp_path / "test.uvh5")
    with h5py.File(output_file, "w") as h5f:
        header = h5f.create_group("Header")
        times = header.create_dataset("time_array", data=times)

    # test function
    obsid = utils.get_obsid_from_file(output_file)
    assert obsid == int(np.floor(t0.gps))

    return
