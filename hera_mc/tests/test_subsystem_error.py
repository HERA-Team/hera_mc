# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.subsystem_error`."""
from math import floor
import pytest

from astropy.time import Time, TimeDelta

from ..subsystem_error import SubsystemError


@pytest.fixture(scope="module")
def subsys():
    class DataHolder(object):
        time = Time.now()
        subsystem_error_names = [
            "id",
            "time",
            "subsystem",
            "mc_time",
            "severity",
            "log",
        ]
        subsystem_error_values = [1, time, "librarian", time, 1, "bad problem"]
        subsystem_error_columns = dict(
            zip(subsystem_error_names, subsystem_error_values)
        )

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


def test_add_subsystem_error(mcsession, subsys):
    test_session = mcsession
    exp_columns = subsys.subsystem_error_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    exp_columns["mc_time"] = int(floor(exp_columns["mc_time"].gps))
    expected = SubsystemError(**exp_columns)

    # try testing mode
    error_obj = test_session.add_subsystem_error(
        subsys.subsystem_error_values[1],
        subsys.subsystem_error_values[2],
        *subsys.subsystem_error_values[4:],
        testing=True
    )

    # error_obj.id isn't set because that's autoincremented by the database
    error_obj.id = expected.id

    # mc times may be different, set them equal to test the rest
    expected.mc_time = error_obj.mc_time

    assert error_obj.isclose(expected)

    test_session.add_subsystem_error(
        subsys.subsystem_error_values[1],
        subsys.subsystem_error_values[2],
        *subsys.subsystem_error_values[4:]
    )
    # now actually add it
    result = test_session.get_subsystem_error(
        starttime=subsys.subsystem_error_columns["time"]
        - TimeDelta(2 * 60, format="sec")
    )
    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    test_session.add_subsystem_error(
        subsys.subsystem_error_values[1], "rtp", *subsys.subsystem_error_values[4:]
    )
    result_subsystem = test_session.get_subsystem_error(
        starttime=subsys.subsystem_error_columns["time"] - TimeDelta(2, format="sec"),
        subsystem=subsys.subsystem_error_columns["subsystem"],
        stoptime=subsys.subsystem_error_columns["time"]
        + TimeDelta(2 * 60, format="sec"),
    )
    assert len(result_subsystem) == 1
    result_subsystem = result_subsystem[0]
    assert result_subsystem.isclose(expected)

    result_mult = test_session.get_subsystem_error(
        starttime=subsys.subsystem_error_columns["time"] - TimeDelta(2, format="sec"),
        stoptime=subsys.subsystem_error_columns["time"]
        + TimeDelta(2 * 60, format="sec"),
    )

    assert len(result_mult) == 2
    ids = [res.id for res in result_mult]
    assert ids == [1, 2]
    subsystems = [res.subsystem for res in result_mult]
    assert subsystems == ["librarian", "rtp"]

    result2 = test_session.get_subsystem_error(
        starttime=subsys.subsystem_error_columns["time"] - TimeDelta(2, format="sec"),
        subsystem="rtp",
    )[0]

    assert not result2.isclose(expected)


def test_errors_subsystem_error(mcsession, subsys):
    test_session = mcsession
    pytest.raises(
        ValueError,
        test_session.add_subsystem_error,
        "foo",
        subsys.subsystem_error_values[2],
        *subsys.subsystem_error_values[4:]
    )

    test_session.add_subsystem_error(
        subsys.subsystem_error_values[1],
        subsys.subsystem_error_values[2],
        *subsys.subsystem_error_values[4:]
    )
    pytest.raises(ValueError, test_session.get_subsystem_error, starttime="foo")
    pytest.raises(
        ValueError,
        test_session.get_subsystem_error,
        starttime=subsys.subsystem_error_columns["time"],
        stoptime="foo",
    )
