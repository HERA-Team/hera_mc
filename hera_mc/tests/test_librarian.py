# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.librarian`."""
import os
from math import floor

import pytest
from astropy.time import Time, TimeDelta

from ..librarian import (
    LibStatus,
    LibRAIDStatus,
    LibRAIDErrors,
    LibRemoteStatus,
    LibFiles,
)
from .. import utils


@pytest.fixture(scope="module")
def status():
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(6 * 60, format="sec")
        status_names = [
            "time",
            "num_files",
            "data_volume_gb",
            "free_space_gb",
            "upload_min_elapsed",
            "num_processes",
            "git_version",
            "git_hash",
        ]
        status_values = [time, 135, 3.6, 8.2, 12.2, 3, "v0.0.1", "lskdjf24l"]
        status_columns = dict(zip(status_names, status_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def raidstatus():
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(6 * 60, format="sec")
        raid_status_names = ["time", "hostname", "num_disks", "info"]
        raid_status_values = [time, "raid_1", 16, "megaraid controller is happy"]
        raid_status_columns = dict(zip(raid_status_names, raid_status_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def raiderror():
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(6 * 60, format="sec")
        raid_error_names = ["id", "time", "hostname", "disk", "log"]
        raid_error_values = [1, time, "raid_1", "d4", "unhappy disk"]
        raid_error_columns = dict(zip(raid_error_names, raid_error_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def remote():
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(6 * 60, format="sec")
        remote_status_names = [
            "time",
            "remote_name",
            "ping_time",
            "num_file_uploads",
            "bandwidth_mbs",
        ]
        remote_status_values = [time, "nrao", 0.13, 5, 56.4]
        remote_status_columns = dict(zip(remote_status_names, remote_status_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def file():
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(6 * 60, format="sec")
        obsid = utils.calculate_obsid(time)
        observation_names = ["starttime", "stoptime", "obsid"]
        observation_values = [time, time + TimeDelta(10 * 60, format="sec"), obsid]
        observation_columns = dict(zip(observation_names, observation_values))

        file_names = ["filename", "obsid", "time", "size_gb"]
        file_values = ["file1", obsid, time, 2.4]
        file_columns = dict(zip(file_names, file_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


def test_add_lib_status(mcsession, status):
    test_session = mcsession
    test_session.add_lib_status(*status.status_values)

    exp_columns = status.status_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = LibStatus(**exp_columns)

    # test with starttime
    result = test_session.get_lib_status(
        starttime=status.status_columns["time"] - TimeDelta(2, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    # test with most_recent
    result = test_session.get_lib_status()
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    new_status_time = status.status_columns["time"] + TimeDelta(5 * 60, format="sec")
    test_session.add_lib_status(
        new_status_time,
        status.status_columns["num_files"] + 2,
        status.status_columns["data_volume_gb"] + 0.2,
        status.status_columns["free_space_gb"] - 0.2,
        2.2,
        status.status_columns["num_processes"],
        status.status_columns["git_version"],
        status.status_columns["git_hash"],
    )

    result_mult = test_session.get_lib_status(
        starttime=status.status_columns["time"] - TimeDelta(2, format="sec"),
        stoptime=new_status_time,
    )
    assert len(result_mult) == 2

    result2 = test_session.get_lib_status(
        starttime=new_status_time - TimeDelta(2, format="sec")
    )
    assert len(result2) == 1
    result2 = result2[0]
    assert not result2.isclose(expected)

    # test most_recent matches 2nd status
    result2_most_recent = test_session.get_lib_status(most_recent=True)
    result2_most_recent = result2_most_recent[0]
    assert result2.isclose(result2_most_recent)


def test_errors_lib_status(mcsession, status):
    test_session = mcsession
    pytest.raises(
        ValueError, test_session.add_lib_status, "foo", *status.status_values[1:]
    )

    test_session.add_lib_status(*status.status_values)
    pytest.raises(ValueError, test_session.get_lib_status, starttime="unhappy")
    pytest.raises(
        ValueError,
        test_session.get_lib_status,
        starttime=status.status_columns["time"],
        stoptime="unhappy",
    )


def test_add_raid_status(mcsession, raidstatus):
    test_session = mcsession
    exp_columns = raidstatus.raid_status_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = LibRAIDStatus(**exp_columns)

    test_session.add_lib_raid_status(*raidstatus.raid_status_values)

    result = test_session.get_lib_raid_status(
        starttime=(
            raidstatus.raid_status_columns["time"] - TimeDelta(2 * 60, format="sec")
        )
    )
    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    test_session.add_lib_raid_status(
        raidstatus.raid_status_values[0], "raid_2", *raidstatus.raid_status_values[2:]
    )
    result_host = test_session.get_lib_raid_status(
        starttime=(raidstatus.raid_status_columns["time"] - TimeDelta(2, format="sec")),
        hostname=raidstatus.raid_status_columns["hostname"],
        stoptime=(
            raidstatus.raid_status_columns["time"] + TimeDelta(2 * 60, format="sec")
        ),
    )
    assert len(result_host) == 1
    result_host = result_host[0]
    assert result_host.isclose(expected)

    result_mult = test_session.get_lib_raid_status(
        starttime=(raidstatus.raid_status_columns["time"] - TimeDelta(2, format="sec")),
        stoptime=(
            raidstatus.raid_status_columns["time"] + TimeDelta(2 * 60, format="sec")
        ),
    )

    assert len(result_mult) == 2

    result2 = test_session.get_lib_raid_status(
        starttime=(raidstatus.raid_status_columns["time"] - TimeDelta(2, format="sec")),
        hostname="raid_2",
    )
    assert len(result2) == 1
    result2 = result2[0]

    assert not result2.isclose(expected)

    result2_most_recent = test_session.get_lib_raid_status(hostname="raid_2")
    result2_most_recent = result2_most_recent[0]
    assert result2 == result2_most_recent


def test_errors_lib_raid_status(mcsession, raidstatus):
    test_session = mcsession
    pytest.raises(
        ValueError,
        test_session.add_lib_raid_status,
        "foo",
        *raidstatus.raid_status_values[1:]
    )

    test_session.add_lib_raid_status(*raidstatus.raid_status_values)
    pytest.raises(ValueError, test_session.get_lib_raid_status, starttime="foo")
    pytest.raises(
        ValueError,
        test_session.get_lib_raid_status,
        starttime=raidstatus.raid_status_columns["time"],
        stoptime="foo",
    )


def test_add_raid_error(mcsession, raiderror):
    test_session = mcsession
    exp_columns = raiderror.raid_error_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = LibRAIDErrors(**exp_columns)

    test_session.add_lib_raid_error(*raiderror.raid_error_values[1:])

    result = test_session.get_lib_raid_error(
        starttime=(
            raiderror.raid_error_columns["time"] - TimeDelta(2 * 60, format="sec")
        )
    )
    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    test_session.add_lib_raid_error(
        raiderror.raid_error_values[1], "raid_2", *raiderror.raid_error_values[3:]
    )
    result_host = test_session.get_lib_raid_error(
        starttime=(raiderror.raid_error_columns["time"] - TimeDelta(2, format="sec")),
        hostname=raiderror.raid_error_columns["hostname"],
        stoptime=(
            raiderror.raid_error_columns["time"] + TimeDelta(2 * 60, format="sec")
        ),
    )
    assert len(result_host) == 1
    result_host = result_host[0]
    assert result_host.isclose(expected)

    result_mult = test_session.get_lib_raid_error(
        starttime=(raiderror.raid_error_columns["time"] - TimeDelta(2, format="sec")),
        stoptime=(
            raiderror.raid_error_columns["time"] + TimeDelta(2 * 60, format="sec")
        ),
    )

    assert len(result_mult) == 2
    ids = [res.id for res in result_mult]
    assert ids == [1, 2]

    result2 = test_session.get_lib_raid_error(
        starttime=(raiderror.raid_error_columns["time"] - TimeDelta(2, format="sec")),
        hostname="raid_2",
    )[0]

    assert not result2.isclose(expected)


def test_errors_lib_raid_error(mcsession, raiderror):
    test_session = mcsession
    pytest.raises(
        ValueError,
        test_session.add_lib_raid_error,
        "foo",
        *raiderror.raid_error_values[2:]
    )

    test_session.add_lib_raid_error(*raiderror.raid_error_values[1:])
    pytest.raises(ValueError, test_session.get_lib_raid_error, starttime="foo")
    pytest.raises(
        ValueError,
        test_session.get_lib_raid_error,
        starttime=raiderror.raid_error_columns["time"],
        stoptime="foo",
    )


def test_add_remote_status(mcsession, remote):
    test_session = mcsession
    exp_columns = remote.remote_status_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = LibRemoteStatus(**exp_columns)

    test_session.add_lib_remote_status(*remote.remote_status_values)

    result = test_session.get_lib_remote_status(
        starttime=remote.remote_status_columns["time"] - TimeDelta(2 * 60, format="sec")
    )
    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    test_session.add_lib_remote_status(
        remote.remote_status_values[0], "penn", *remote.remote_status_values[2:]
    )
    result_remote = test_session.get_lib_remote_status(
        starttime=(remote.remote_status_columns["time"] - TimeDelta(2, format="sec")),
        remote_name=remote.remote_status_columns["remote_name"],
        stoptime=remote.remote_status_columns["time"] + TimeDelta(2 * 60, format="sec"),
    )

    assert len(result_remote) == 1
    result_remote = result_remote[0]
    assert result_remote.isclose(expected)

    result_mult = test_session.get_lib_remote_status(
        starttime=(remote.remote_status_columns["time"] - TimeDelta(2, format="sec")),
        stoptime=remote.remote_status_columns["time"] + TimeDelta(2 * 60, format="sec"),
    )

    assert len(result_mult) == 2

    result_mult_most_recent = test_session.get_lib_remote_status()
    assert result_mult == result_mult_most_recent

    result2 = test_session.get_lib_remote_status(
        starttime=remote.remote_status_columns["time"] - TimeDelta(2, format="sec"),
        remote_name="penn",
    )
    assert len(result2) == 1
    result2 = result2[0]

    assert not result2.isclose(expected)


def test_errors_lib_remote_status(mcsession, remote):
    test_session = mcsession
    pytest.raises(
        ValueError,
        test_session.add_lib_remote_status,
        "foo",
        *remote.remote_status_values[1:]
    )

    test_session.add_lib_remote_status(*remote.remote_status_values)
    pytest.raises(ValueError, test_session.get_lib_remote_status, starttime="foo")
    pytest.raises(
        ValueError,
        test_session.get_lib_remote_status,
        starttime=remote.remote_status_columns["time"],
        stoptime="foo",
    )


def test_add_lib_file(mcsession, file, tmpdir):
    test_session = mcsession

    test_session.add_obs(*file.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    test_session.add_lib_file(*file.file_values)

    exp_columns = file.file_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = LibFiles(**exp_columns)

    result_file = test_session.get_lib_files(filename=file.file_columns["filename"])[0]
    assert result_file.isclose(expected)

    result = test_session.get_lib_files(
        starttime=file.file_columns["time"] - TimeDelta(2, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_obsid = test_session.get_lib_files(
        starttime=file.file_columns["time"] - TimeDelta(2, format="sec"),
        obsid=file.file_columns["obsid"],
    )
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result_obsid.isclose(expected)

    new_file_time = file.file_columns["time"] + TimeDelta(3 * 60, format="sec")
    new_file = "file2"
    test_session.add_lib_file(new_file, file.file_values[1], new_file_time, 1.4)
    result_obsid = test_session.get_lib_files(obsid=file.file_columns["obsid"])
    assert len(result_obsid) == 2

    filename = os.path.join(tmpdir, "test_lib_file_record_file.csv")
    test_session.get_lib_files(
        obsid=file.file_columns["obsid"], write_to_file=True, write_filename=filename
    )
    os.remove(filename)

    result_all = test_session.get_lib_files()
    assert len(result_obsid) == len(result_all)
    for i in range(0, len(result_obsid)):
        assert result_obsid[i].isclose(result_all[i])


def test_lib_file_null_obsid(mcsession, file):
    test_session = mcsession
    test_session.add_obs(*file.observation_values)

    time = Time.now()
    file.file_values = ["nullobsfile", None, time, 1.234]
    test_session.add_lib_file(*file.file_values)

    expected = LibFiles(
        filename=file.file_values[0],
        obsid=None,
        time=int(floor(time.gps)),
        size_gb=file.file_values[3],
    )

    result = test_session.get_lib_files(filename=file.file_values[0])
    assert len(result) == 1
    assert result[0].isclose(expected)

    # Clean up so as not to step on toes of `test_add_lib_file()` test.
    test_session.delete(result[0])
    test_session.commit()


def test_errors_add_lib_file(mcsession, file, status):
    test_session = mcsession
    test_session.add_obs(*file.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    pytest.raises(
        ValueError,
        test_session.add_lib_file,
        status.status_values[0],
        status.status_values[1],
        "foo",
        status.status_values[3],
    )

    test_session.add_lib_file(*file.file_values)
    pytest.raises(ValueError, test_session.get_lib_files, starttime="foo")
    pytest.raises(
        ValueError,
        test_session.get_lib_files,
        starttime=file.file_columns["time"],
        stoptime="bar",
    )
