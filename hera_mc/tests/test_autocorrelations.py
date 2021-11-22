# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.autocorrelations`."""

import pytest
import datetime
from math import floor
from astropy.time import Time, TimeDelta
from hera_mc import autocorrelations

from ..tests import requires_redis, requires_default_redis, TEST_DEFAULT_REDIS_HOST

standard_query_time = Time(
    datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format="datetime"
)


@pytest.fixture(scope="module")
def autocorrs():
    return {
        "4": {
            "time": Time(
                datetime.datetime(2016, 1, 5, 20, 44, 52, 739322), format="datetime"
            ),
            "antenna_number": 4,
            "antenna_feed_pol": "e",
            "measurement_type": "median",
            "value": 12.3687,
        },
        "31": {
            "time": Time(
                datetime.datetime(2016, 1, 5, 20, 44, 52, 739322), format="datetime"
            ),
            "antenna_number": 31,
            "antenna_feed_pol": "n",
            "measurement_type": "median",
            "value": 876.44509,
        },
    }


@pytest.fixture()
def auto_dict():
    return {
        "timestamp": Time(
            datetime.datetime(2016, 1, 5, 20, 44, 52, 739322), format="datetime"
        ).jd,
        "400:e": [level - 12.3687 for level in range(-8, 9)],
        "400:n": [level - 15.5739 for level in range(-8, 9)],
        "710:e": [level - 44.5873 for level in range(-8, 9)],
        "710:n": [level - 66.4509 for level in range(-8, 9)],
    }


@pytest.mark.parametrize("antnum", [4, 31])
def test_autos_added(mcsession, autocorrs, antnum):
    test_session = mcsession
    for ant in autocorrs:
        corr = autocorrs[ant]
        test_session.add_autocorrelation(
            time=corr["time"],
            antenna_number=corr["antenna_number"],
            antenna_feed_pol=corr["antenna_feed_pol"],
            measurement_type=corr["measurement_type"],
            value=corr["value"],
        )

    t1 = standard_query_time
    result = test_session.get_autocorrelation(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(result) == 2

    ant_key = "{:d}".format(antnum)
    expected = autocorrelations.HeraAuto(
        time=int(floor(t1.gps)),
        antenna_number=antnum,
        antenna_feed_pol=autocorrs[ant_key]["antenna_feed_pol"],
        measurement_type="median",
        value=autocorrs[ant_key]["value"],
    )
    result = test_session.get_autocorrelation(antenna_number=antnum)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


@pytest.mark.parametrize(
    "args,err_type,err_msg",
    [
        (
            [Time(2458843, format="jd").gps, 4, "median", 0, 12.1],
            ValueError,
            "time must be an astropy Time object.",
        ),
        (
            [Time(2458843, format="jd"), 4, "x", "median", 12.1],
            ValueError,
            "antenna_feed_pol must be 'e' or 'n'.",
        ),
        (
            [Time(2458843, format="jd"), 4, "e", 0, 12.1],
            ValueError,
            "measurement_type must be a string",
        ),
        (
            [Time(2458843, format="jd"), 4, "e", "bad", 12.1],
            ValueError,
            "Autocorrelation type bad not supported.",
        ),
    ],
)
def test_add_autocorrelations_errors(mcsession, args, err_type, err_msg):
    test_session = mcsession
    with pytest.raises(err_type) as cm:
        test_session.add_autocorrelation(*args)
    assert str(cm.value).startswith(err_msg)


# check all four HeraAuto objects which should be created
# also check each one with a starttime defined and with the "most_recent"
# setting in the get_autocorrelation function
@pytest.mark.parametrize(
    "antnum,antpol,expected",
    [
        (
            400,
            "e",
            autocorrelations.HeraAuto(
                time=floor(standard_query_time.gps),
                antenna_number=400,
                antenna_feed_pol="e",
                measurement_type="median",
                value=-12.3687,
            ),
        ),
        (
            400,
            "n",
            autocorrelations.HeraAuto(
                time=floor(standard_query_time.gps),
                antenna_number=400,
                antenna_feed_pol="n",
                measurement_type="median",
                value=-15.5739,
            ),
        ),
        (
            710,
            "e",
            autocorrelations.HeraAuto(
                time=floor(standard_query_time.gps),
                antenna_number=710,
                antenna_feed_pol="e",
                measurement_type="median",
                value=-44.5873,
            ),
        ),
        (
            710,
            "n",
            autocorrelations.HeraAuto(
                time=floor(standard_query_time.gps),
                antenna_number=710,
                antenna_feed_pol="n",
                measurement_type="median",
                value=-66.4509,
            ),
        ),
    ],
)
@pytest.mark.parametrize(
    "starttime",
    [standard_query_time - TimeDelta(3.0, format="sec"), None],
)
def test_add_autos_from_redis(
    mcsession, starttime, auto_dict, antnum, antpol, expected
):
    test_session = mcsession
    hera_auto_list = test_session.add_autocorrelations_from_redis(
        hera_autos_dict=auto_dict,
        testing=True,
    )
    for obj in hera_auto_list:
        test_session.add(obj)
    result = test_session.get_autocorrelation(
        starttime=starttime, antenna_number=antnum
    )
    assert len(result) == 2

    result = [res for res in result if res.antenna_feed_pol == antpol][0]

    assert result.isclose(expected)


def test_add_autos_from_redis_errors(mcsession, auto_dict):
    test_session = mcsession
    auto_dict.pop("timestamp")
    with pytest.raises(ValueError) as cm:
        test_session.add_autocorrelations_from_redis(
            hera_autos_dict=auto_dict,
            testing=True,
        )
    assert str(cm.value).startswith("No timestamp found in hera_autos_dict. ")


@requires_redis
def test_with_redis_add_autos_from_redis_errors(mcsession):
    test_session = mcsession

    test_session.add_autocorrelations_from_redis(redishost=TEST_DEFAULT_REDIS_HOST)
    result = test_session.get_autocorrelation(most_recent=True)
    assert len(result) >= 1


@requires_redis
@requires_default_redis
def test_add_autos_from_redis_default_redishost(mcsession):
    test_session = mcsession

    test_session.add_autocorrelations_from_redis()
    result = test_session.get_autocorrelation(most_recent=True)
    assert len(result) >= 1
