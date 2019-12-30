# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.autocorrelations`."""
from __future__ import absolute_import, division, print_function

import pytest
import datetime
import numpy as np
from math import floor
from astropy.time import Time, TimeDelta
from hera_mc import autocorrelations, cm_sysutils

import six
if six.PY3:
    from plotly import graph_objects as go
else:
    from plotly import graph_objs as go


@pytest.fixture(scope='function')
def test_figure(mcsession):
    test_session = mcsession
    figure = autocorrelations.plot_HERA_autocorrelations_for_plotly(
        test_session, offline_testing=True
    )
    yield figure

    del figure


@pytest.fixture(scope='module')
def autocorrs():
    return {
        "4": {
            "time": Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 739322), format='datetime'),
            "antenna_number": 4,
            "antenna_feed_pol": "e",
            "measurement_type": "median",
            "value": 12.3687
        },
        "31": {
            "time": Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 739322), format='datetime'),
            "antenna_number": 31,
            "antenna_feed_pol": "n",
            "measurement_type": autocorrelations.MeasurementTypes.median,
            "value": 876.44509
        }
    }


@pytest.mark.parametrize("antnum", [4, 31])
def test_autos_added(mcsession, autocorrs, antnum, capsys):
    test_session = mcsession
    for ant in autocorrs:
        corr = autocorrs[ant]
        test_session.add_autocorrelation(
            time=corr["time"],
            antenna_number=corr["antenna_number"],
            antenna_feed_pol=corr["antenna_feed_pol"],
            measurement_type=corr["measurement_type"],
            value=corr["value"]
        )

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
              format='datetime')
    result = test_session.get_autocorrelation(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 2

    ant_key = "{:d}".format(antnum)
    expected = autocorrelations.HeraAuto(
        time=int(floor(t1.gps)),
        antenna_number=antnum,
        antenna_feed_pol=autocorrs[ant_key]["antenna_feed_pol"],
        measurement_type=autocorrelations.MeasurementTypes.median,
        value=autocorrs[ant_key]["value"]
    )
    result = test_session.get_autocorrelation(antenna_number=antnum)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    print(result)
    captured = capsys.readouterr()
    repr = (
        "<HeraAuto time={result.time} antenna_number={result.antenna_number} "
        "polarization={result.antenna_feed_pol} measurement_type={result.measurement_type_name} "
        "value={result.value}>"
        .format(result=result)
    )
    assert captured.out.startswith(repr)


@pytest.mark.parametrize(
    "args,err_type,err_msg", [
        (
            [Time(2458843, format='jd').gps, 4, "e", 0, 12.1],
            ValueError,
            "time must be an astropy Time object."
        ),
        (
            [Time(2458843, format='jd'), 4, "x", 0, 12.1],
            ValueError,
            "antenna_feed_pol must be 'e' or 'n'."
        ),
        (
            [Time(2458843, format='jd'), 4, "e", "bad", 12.1],
            ValueError,
            "Autocorrelation type bad not supported"
        ),
        (
            [Time(2458843, format='jd'), 4, "e", -1, 12.1],
            ValueError,
            "Input measurement type is not in range of accepted values. "
        )
    ]
)
def test_add_autocorrelations_errors(mcsession, args, err_type, err_msg):
    test_session = mcsession
    with pytest.raises(err_type) as cm:
        test_session.add_autocorrelation(*args)
    assert str(cm.value).startswith(err_msg)


@pytest.mark.parametrize("antnum", [4, 31])
def test_add_old_autos(mcsession, autocorrs, antnum, capsys):
    test_session = mcsession
    for ant in autocorrs:
        corr = autocorrs[ant]
        ac = autocorrelations.Autocorrelations()
        ac.id = int(ant) + 2
        ac.time = corr["time"].datetime
        ac.antnum = corr["antenna_number"]
        ac.polarization = corr["antenna_feed_pol"]
        ac.value = corr["value"]
        ac.measurement_type = autocorrelations.MeasurementTypes.median
        test_session.add(ac)

    result = (
        test_session.query(autocorrelations.Autocorrelations).
        filter(autocorrelations.Autocorrelations.measurement_type == 0).
        order_by(autocorrelations.Autocorrelations.time).
        all()
    )

    assert len(result) == 2

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
              format='datetime')

    ant_key = "{:d}".format(antnum)
    expected = autocorrelations.Autocorrelations()
    expected.id = antnum + 2
    expected.time = t1.datetime
    expected.antnum = antnum
    expected.polarization = autocorrs[ant_key]["antenna_feed_pol"]
    expected.measurement_type = autocorrelations.MeasurementTypes.median
    expected.value = autocorrs[ant_key]["value"]
    result = (
        test_session.query(autocorrelations.Autocorrelations).
        filter(autocorrelations.Autocorrelations.measurement_type == 0).
        filter(autocorrelations.Autocorrelations.antnum == antnum).
        order_by(autocorrelations.Autocorrelations.time).
        all()
    )
    assert len(result) == 1
    result = result[0]
    print(result)
    print(expected)
    # cannot use the isclose command because `datetime` objects cannot be coerced by numpy.isclose
    assert expected.id == result.id
    assert expected.antnum == result.antnum
    assert expected.polarization == result.polarization
    assert expected.measurement_type == result.measurement_type
    assert np.isclose(expected.value, result.value)
    assert (
        Time(expected.time, format='datetime')
        - Time(result.time, format='datetime')
        < TimeDelta(1, format='sec')
    )

    print(result)
    captured = capsys.readouterr()
    repr = (
        "<Autocorrelations id={result.id} time={result.time} antnum={result.antnum} "
        "polarization={result.polarization} measurement_type={result.measurement_type_name} "
        "value={result.value}>"
        .format(result=result)
    )
    assert captured.out.startswith(repr)


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
            value=corr["value"]
        )
    # This test is a little tautological however it does check that all
    # antennas we "think" are connected have autocorrelations.
    # the test session has no entries in this table so it should be null
    figure = figure = autocorrelations.plot_HERA_autocorrelations_for_plotly(
        test_session, offline_testing=True
    )

    ants_in_fig = sorted([d.name for d in figure.data])

    assert ants_in_fig == ["31n", "4e"]
