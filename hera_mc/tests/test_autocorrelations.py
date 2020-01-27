# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.autocorrelations`."""
from __future__ import absolute_import, division, print_function

import pytest
import datetime
from math import floor
from astropy.time import Time, TimeDelta
from hera_mc import autocorrelations

import six

if six.PY3:
    from plotly import graph_objects as go
else:
    from plotly import graph_objs as go


standard_query_time = Time(
    datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format="datetime"
)


@pytest.fixture(scope="function")
def test_figure(mcsession):
    test_session = mcsession
    figure = autocorrelations.plot_HERA_autocorrelations_for_plotly(
        test_session, offline_testing=True
    )
    yield figure

    del figure


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
        "400:e": [l - 12.3687 for l in range(-8, 9)],
        "400:n": [l - 15.5739 for l in range(-8, 9)],
        "710:e": [l - 44.5873 for l in range(-8, 9)],
        "710:n": [l - 66.4509 for l in range(-8, 9)],
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


def test_figure_is_created(test_figure):
    assert isinstance(test_figure, go.Figure)


def test_ants_in_figure(mcsession, autocorrs):
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
    # This test is a little tautological however it does check that all
    # antennas we "think" are connected have autocorrelations.
    # the test session has no entries in this table so it should be null
    figure = figure = autocorrelations.plot_HERA_autocorrelations_for_plotly(
        test_session, offline_testing=True
    )

    ants_in_fig = sorted([d.name for d in figure.data])

    assert ants_in_fig == ["31n", "4e"]


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
    "starttime", [standard_query_time - TimeDelta(3.0, format="sec"), None],
)
def test_add_autos_from_redis(mcsession, starttime, auto_dict, antnum, antpol, expected):
    test_session = mcsession
    hera_auto_list = test_session.add_autocorrelations_from_redis(
        hera_autos_dict=auto_dict, testing=True,
    )
    for obj in hera_auto_list:
        test_session.add(obj)
    result = test_session.get_autocorrelation(starttime=starttime, antenna_number=antnum)
    assert len(result) == 2

    result = [res for res in result if res.antenna_feed_pol == antpol][0]

    assert result.isclose(expected)


def test_add_autos_from_redis_errors(mcsession, auto_dict):
    test_session = mcsession
    auto_dict.pop('timestamp')
    with pytest.raises(ValueError) as cm:
        test_session.add_autocorrelations_from_redis(
            hera_autos_dict=auto_dict, testing=True,
        )
    assert str(cm.value).startswith("No timestamp found in hera_autos_dict. ")
