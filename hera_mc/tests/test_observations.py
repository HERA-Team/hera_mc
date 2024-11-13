# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.observations`."""
import re
from math import floor

import pytest
from astropy.coordinates import EarthLocation
from astropy.time import Time, TimeDelta

from .. import geo_handling, utils
from ..observations import Observation, allowed_tags

# Sometimes a connection is closed, which is handled and doesn't produce an error
# or even a warning under normal testing. But for the warnings test where we
# pass `-W error`, the warning causes an error so we filter it out here.
pytestmark = pytest.mark.filterwarnings("ignore:connection:ResourceWarning:psycopg")


def test_new_obs(mcsession):
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")

    t3 = t1 + TimeDelta(1e-3, format="sec")
    t4 = t2 + TimeDelta(1e-3, format="sec")

    h = geo_handling.Handling(session=mcsession)
    hera_cofa = h.cofa()[0]

    obs1 = Observation.create(t1, t2, utils.calculate_obsid(t1), hera_cofa, "science")
    obs2 = Observation.create(t3, t4, utils.calculate_obsid(t3), hera_cofa, "science")
    assert obs1 != obs2


def test_add_obs(mcsession):
    test_session = mcsession
    t1 = Time(
        "2016-01-10 01:15:23",
        scale="utc",
        location=EarthLocation.from_geodetic(21.4283038269, -30.7215261207),
    )
    t2 = t1 + TimeDelta(120.0, format="sec")

    # generated test hera_lat, hera_lon using the output of geo.py -c
    # with this website:
    # http://www.uwgb.edu/dutchs/usefuldata/ConvertUTMNoOZ.HTM

    obsid_calc = int(floor(t1.gps))
    obsid = utils.calculate_obsid(t1)
    assert obsid_calc == obsid

    expected = Observation(
        obsid=obsid,
        starttime=t1.gps,
        stoptime=t2.gps,
        jd_start=t1.jd,
        lst_start_hr=t1.sidereal_time("apparent").hour,
        tag="science",
    )

    test_session.add_obs(t1, t2, obsid, "science")
    result = test_session.get_obs()
    assert len(result) == 1
    result = result[0]
    assert result.length == 120.0
    assert result.isclose(expected)

    t3 = t1 + TimeDelta(10 * 60.0, format="sec")
    t4 = t2 + TimeDelta(10 * 60.0, format="sec")
    test_session.add_obs(t3, t4, utils.calculate_obsid(t3), "engineering")

    result_mult = test_session.get_obs_by_time(starttime=t1, stoptime=t4)
    assert len(result_mult) == 2

    result_most_recent = test_session.get_obs_by_time(most_recent=True)
    assert result_most_recent[0] == result_mult[1]

    result_orig = test_session.get_obs(obsid=obsid)
    assert len(result_orig) == 1
    result_orig = result_orig[0]
    assert result_orig.isclose(expected)

    result_orig = test_session.get_obs(tag="science")
    assert len(result_orig) == 1
    result_orig = result_orig[0]
    assert result_orig.isclose(expected)


def test_error_obs(mcsession):
    test_session = mcsession
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")
    with pytest.raises(ValueError, match="starttime must be an astropy Time object"):
        test_session.add_obs("foo", t2, utils.calculate_obsid(t1), "science")
    with pytest.raises(ValueError, match="stoptime must be an astropy Time object"):
        test_session.add_obs(t1, "foo", utils.calculate_obsid(t1), "science")
    with pytest.raises(ValueError, match="obsid must be an integer"):
        test_session.add_obs(t1, t2, "foo", "engineering")
    with pytest.raises(ValueError, match="starttime must be an astropy Time object"):
        utils.calculate_obsid("foo")
    with pytest.raises(
        ValueError, match="obsid should be close to the starttime in gps seconds"
    ):
        test_session.add_obs(t1, t2, utils.calculate_obsid(t1) + 2, "science")
    with pytest.raises(TypeError, match="most_recent must be None or a boolean"):
        test_session.get_obs_by_time(most_recent=t1)
    with pytest.raises(
        ValueError, match=re.escape(f"Tag is foo, should be one of: {allowed_tags}")
    ):
        test_session.add_obs(t1, t2, utils.calculate_obsid(t1), "foo")
