# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.server_status`.

"""
from math import floor

import pytest
from astropy.time import Time, TimeDelta

from ..rtp import RTPServerStatus
from ..librarian import LibServerStatus


@pytest.fixture(scope="module")
def status():
    class DataHolder(object):
        column_names = [
            "hostname",
            "mc_time",
            "ip_address",
            "system_time",
            "num_cores",
            "cpu_load_pct",
            "uptime_days",
            "memory_used_pct",
            "memory_size_gb",
            "disk_space_pct",
            "disk_size_gb",
            "network_bandwidth_mbs",
        ]
        column_values = [
            "test_host",
            Time.now(),
            "0.0.0.0",
            Time.now(),
            16,
            20.5,
            31.4,
            43.2,
            32.0,
            46.8,
            510.4,
            10.4,
        ]
        columns = dict(zip(column_names, column_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


def test_repr(status):
    for sub in ["rtp", "lib"]:
        exp_columns = status.columns.copy()
        exp_columns["mc_time"] = int(floor(exp_columns["mc_time"].gps))
        exp_columns.pop("system_time")
        exp_columns["mc_system_timediff"] = 0

        if sub == "rtp":
            servstat = RTPServerStatus(**exp_columns)
            class_name = "RTPServerStatus"
        elif sub == "lib":
            servstat = LibServerStatus(**exp_columns)
            class_name = "LibServerStatus"

    rep_string = (
        "<"
        + class_name
        + "(test_host, "
        + str(exp_columns["mc_time"])
        + ", 0.0.0.0, "
        + str(exp_columns["mc_system_timediff"])
        + ", 16, 20.5, 31.4, 43.2, 32.0, 46.8, 510.4, 10.4)>"
    )
    assert str(servstat) == rep_string


def test_add_server_status(mcsession, status):
    test_session = mcsession
    for sub in ["rtp", "lib"]:
        exp_columns = status.columns.copy()
        exp_columns["mc_time"] = int(floor(Time.now().gps))
        exp_columns["mc_system_timediff"] = (
            exp_columns["mc_time"] - exp_columns["system_time"].gps
        )
        exp_columns.pop("system_time")

        if sub == "rtp":
            expected = RTPServerStatus(**exp_columns)
        elif sub == "lib":
            expected = LibServerStatus(**exp_columns)

        test_session.add_server_status(
            sub,
            status.column_values[0],
            *status.column_values[2:11],
            network_bandwidth_mbs=status.column_values[11]
        )
        result = test_session.get_server_status(
            sub, starttime=(status.columns["system_time"] - TimeDelta(2, format="sec"))
        )
        assert len(result) == 1
        result = result[0]

        if sub == "rtp":
            result = test_session.get_rtp_server_status(
                sub,
                starttime=status.columns["system_time"] - TimeDelta(2, format="sec"),
            )
        else:
            result = test_session.get_librarian_server_status(
                sub,
                starttime=status.columns["system_time"] - TimeDelta(2, format="sec"),
            )
        assert len(result) == 1
        result = result[0]

        # mc_system_timediff may not be identical. Check that they are close
        # and set them equal so the rest of the object can be tested
        mc_system_timediff_diff = abs(
            result.mc_system_timediff - expected.mc_system_timediff
        )
        assert mc_system_timediff_diff < 2
        if mc_system_timediff_diff > 0.001:
            expected.mc_system_timediff = result.mc_system_timediff

        # mc_time might be off by one between expected & result because of the
        # time between the commands
        mc_timediff = abs(result.mc_time - expected.mc_time)
        assert mc_timediff < 2
        if mc_timediff > 0.001:
            expected.mc_time = result.mc_time

        assert result.isclose(expected)

        test_session.add_server_status(
            sub,
            "test_host2",
            *status.column_values[2:11],
            network_bandwidth_mbs=status.column_values[11]
        )
        result_host = test_session.get_server_status(
            sub,
            starttime=(status.columns["system_time"] - TimeDelta(2, format="sec")),
            hostname=status.columns["hostname"],
            stoptime=(status.columns["system_time"] + TimeDelta(2 * 60, format="sec")),
        )
        assert len(result_host) == 1
        result_host = result_host[0]
        assert result_host.isclose(expected)

        result_mult = test_session.get_server_status(
            sub,
            starttime=(status.columns["system_time"] - TimeDelta(2, format="sec")),
            stoptime=(status.columns["system_time"] + TimeDelta(2 * 60, format="sec")),
        )

        assert len(result_mult) == 2

        result2 = test_session.get_server_status(
            sub,
            starttime=(status.columns["system_time"] - TimeDelta(2, format="sec")),
            hostname="test_host2",
        )[0]
        # mc_times will be different, so won't match. set them equal so that
        # we can test the rest
        expected.mc_time = result2.mc_time
        assert not result2.isclose(expected)


def test_errors_server_statuss(mcsession, status):
    test_session = mcsession
    for sub in ["rtp", "lib"]:
        pytest.raises(
            ValueError,
            test_session.add_server_status,
            sub,
            status.column_values[0],
            status.column_values[2],
            "foo",
            *status.column_values[4:11],
            network_bandwidth_mbs=status.column_values[11]
        )

        test_session.add_server_status(
            sub,
            status.column_values[0],
            *status.column_values[2:11],
            network_bandwidth_mbs=status.column_values[11]
        )
        pytest.raises(
            ValueError, test_session.get_server_status, sub, starttime="test_host"
        )
        pytest.raises(
            ValueError,
            test_session.get_server_status,
            sub,
            starttime=status.columns["system_time"],
            stoptime="test_host",
        )

        if sub == "rtp":
            pytest.raises(
                ValueError,
                RTPServerStatus.create,
                "foo",
                status.column_values[0],
                *status.column_values[2:11],
                network_bandwidth_mbs=status.column_values[11]
            )
        elif sub == "lib":
            pytest.raises(
                ValueError,
                LibServerStatus.create,
                "foo",
                status.column_values[0],
                *status.column_values[2:11],
                network_bandwidth_mbs=status.column_values[11]
            )

    pytest.raises(
        ValueError,
        test_session.add_server_status,
        "foo",
        status.column_values[0],
        *status.column_values[2:11],
        network_bandwidth_mbs=status.column_values[11]
    )
    pytest.raises(
        ValueError,
        test_session.get_server_status,
        "foo",
        starttime=status.column_values[1],
    )
