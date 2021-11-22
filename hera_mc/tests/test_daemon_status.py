# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.daemon_status`."""
from math import floor

import pytest
from astropy.time import Time, TimeDelta

from ..daemon_status import DaemonStatus


@pytest.fixture(scope="function")
def daemon_data():

    column_names = ["name", "hostname", "time", "status"]
    column_values = ["test_daemon", "test_host", Time.now(), "good"]
    columns = dict(zip(column_names, column_values))

    return column_values, columns


def test_add_daemon_status(mcsession, daemon_data):
    test_session = mcsession
    column_values, columns = daemon_data
    exp_columns = columns.copy()
    exp_columns["jd"] = int(floor(exp_columns["time"].jd))
    exp_columns["time"] = int(floor(exp_columns["time"].gps))

    expected = DaemonStatus(**exp_columns)

    result = test_session.add_daemon_status(*column_values, testing=True)
    assert result.isclose(expected)

    test_session.add_daemon_status(*column_values)
    result = test_session.get_daemon_status(
        starttime=columns["time"] - TimeDelta(2, format="sec")
    )
    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    # update the existing record to a new time & status
    expected.time = int(floor(Time.now().gps))
    expected.status = "errored"

    # have to commit to get the updates to work
    test_session.commit()
    test_session.add_daemon_status(
        column_values[0], column_values[1], Time.now(), "errored"
    )
    test_session.commit()
    result = test_session.get_daemon_status(
        starttime=columns["time"] - TimeDelta(2, format="sec")
    )

    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    test_session.add_daemon_status("test_daemon2", *column_values[1:])
    result_host = test_session.get_daemon_status(
        starttime=columns["time"] - TimeDelta(2, format="sec"),
        daemon_name=columns["name"],
        stoptime=columns["time"] + TimeDelta(2 * 60, format="sec"),
    )
    assert len(result_host) == 1
    result_host = result_host[0]
    assert result_host.isclose(expected)

    result_mult = test_session.get_daemon_status(
        starttime=columns["time"] - TimeDelta(2, format="sec"),
        stoptime=columns["time"] + TimeDelta(2 * 60, format="sec"),
    )

    assert len(result_mult) == 2

    result2 = test_session.get_daemon_status(
        starttime=columns["time"] - TimeDelta(2, format="sec"),
        daemon_name="test_daemon2",
    )[0]

    assert not result2.isclose(expected)


def test_errors_daemon_status(mcsession, daemon_data):
    test_session = mcsession
    column_values, columns = daemon_data
    pytest.raises(
        ValueError,
        test_session.add_daemon_status,
        column_values[0],
        column_values[1],
        "foo",
        column_values[3],
    )

    pytest.raises(
        ValueError,
        test_session.add_daemon_status,
        column_values[0],
        column_values[1],
        column_values[2],
        "foo",
    )

    test_session.add_daemon_status(*column_values)
    pytest.raises(ValueError, test_session.get_daemon_status, starttime="test_host")
    pytest.raises(
        ValueError,
        test_session.get_daemon_status,
        starttime=columns["time"],
        stoptime="test_host",
    )
