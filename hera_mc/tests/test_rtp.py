# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.rtp`."""
import os
from math import floor

import pytest
import numpy as np
from astropy.time import Time, TimeDelta

from ..rtp import (
    RTPStatus,
    RTPProcessEvent,
    RTPTaskProcessEvent,
    RTPTaskMultipleProcessEvent,
    RTPProcessRecord,
    RTPTaskResourceRecord,
    RTPLaunchRecord,
    RTPTaskJobID,
    RTPTaskMultipleJobID,
    RTPTaskMultipleResourceRecord,
    RTPTaskMultipleTrack,
)
from .. import utils


@pytest.fixture(scope="module")
def status():
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        status_names = [
            "time",
            "status",
            "event_min_elapsed",
            "num_processes",
            "restart_hours_elapsed",
        ]
        status_values = [time, "happy", 3.6, 8, 10.2]
        status_columns = dict(zip(status_names, status_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def observation():
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        obsid = utils.calculate_obsid(time)
        observation_names = ["starttime", "stoptime", "obsid"]
        observation_values = [time, time + TimeDelta(10 * 60, format="sec"), obsid]
        observation_columns = dict(zip(observation_names, observation_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def event(observation):
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        event_names = ["time", "obsid", "event"]
        event_values = [time, observation.obsid, "queued"]
        event_columns = dict(zip(event_names, event_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def task_event(observation):
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        event_names = ["time", "obsid", "task_name", "event"]
        event_values = [time, observation.obsid, "OMNICAL", "started"]
        event_columns = dict(zip(event_names, event_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def multiple_task_event(observation):
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        event_names = ["time", "obsid_start", "task_name", "event"]
        event_values = [time, observation.obsid, "OMNICAL", "started"]
        event_columns = dict(zip(event_names, event_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def record(observation):
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        record_names = [
            "time",
            "obsid",
            "pipeline_list",
            "rtp_git_version",
            "rtp_git_hash",
            "hera_qm_git_version",
            "hera_qm_git_hash",
            "hera_cal_git_version",
            "hera_cal_git_hash",
            "pyuvdata_git_version",
            "pyuvdata_git_hash",
        ]
        record_values = [
            time,
            observation.obsid,
            "sample_pipe",
            "v0.0.1",
            "lskdjf24l",
            "v0.1.0",
            "abcd34d",
            "v1.0.0",
            "jkfldi39",
            "v2.0.0",
            "fjklj828",
        ]
        record_columns = dict(zip(record_names, record_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def jobid(observation):
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        task_jobid_names = ["obsid", "task_name", "start_time", "job_id"]
        task_jobid_values = [observation.obsid, "OMNICAL", time, 1200]

        task_jobid_columns = dict(zip(task_jobid_names, task_jobid_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def task(observation):
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        task_resource_names = [
            "obsid",
            "task_name",
            "start_time",
            "stop_time",
            "max_memory",
            "avg_cpu_load",
        ]
        task_resource_values = [
            observation.obsid,
            "OMNICAL",
            time,
            time + TimeDelta(10 * 60, format="sec"),
            16.2,
            1.01,
        ]
        task_resource_columns = dict(zip(task_resource_names, task_resource_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def multiple_jobid(observation):
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        task_jobid_names = ["obsid_start", "task_name", "start_time", "job_id"]
        task_jobid_values = [observation.obsid, "OMNICAL", time, 1200]

        task_jobid_columns = dict(zip(task_jobid_names, task_jobid_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def task_multiple(observation):
    class DataHolder(object):
        # pick a date far in the past just in case IERS is down
        t0 = Time(2457000, format="jd")
        time = t0 - TimeDelta(30 * 60, format="sec")
        task_resource_names = [
            "obsid_start",
            "task_name",
            "start_time",
            "stop_time",
            "max_memory",
            "avg_cpu_load",
        ]
        task_resource_values = [
            observation.obsid,
            "OMNICAL",
            time,
            time + TimeDelta(10 * 60, format="sec"),
            16.2,
            1.01,
        ]
        task_resource_columns = dict(zip(task_resource_names, task_resource_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


@pytest.fixture(scope="module")
def multiple_track(observation):
    class DataHolder(object):
        track_names = ["obsid_start", "task_name", "obsid"]
        observation_names = ["starttime", "stoptime", "obsid"]

        # make more obsids
        starttimes = [observation.observation_columns["starttime"]] + [
            observation.observation_columns["starttime"]
            + TimeDelta(min_time * 60, format="sec")
            for min_time in [10, 20]
        ]
        stoptimes = [observation.observation_columns["stoptime"]] + [
            observation.observation_columns["stoptime"]
            + TimeDelta(min_time * 60, format="sec")
            for min_time in [10, 20]
        ]

        obsid_list = [observation.observation_columns["obsid"]] + [
            utils.calculate_obsid(time) for time in starttimes[1:]
        ]

        track_values = []
        track_columns = []
        observation_values = []
        observation_columns = []
        for ind, obsid in enumerate(obsid_list):
            this_track_values = [observation.obsid, "OMNICAL", obsid]
            track_values.append(this_track_values)
            track_columns.append(dict(zip(track_names, this_track_values)))
            this_obs_values = [starttimes[ind], stoptimes[ind], obsid]
            observation_values.append(this_obs_values)
            observation_columns.append(dict(zip(observation_names, this_obs_values)))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del data

    return


def test_add_rtp_status(mcsession, status):
    test_session = mcsession
    test_session.add_rtp_status(*status.status_values)

    exp_columns = status.status_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = RTPStatus(**exp_columns)

    result = test_session.get_rtp_status(
        starttime=status.status_columns["time"] - TimeDelta(2, format="sec")
    )
    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    new_status_time = status.status_columns["time"] + TimeDelta(5 * 60, format="sec")
    new_status = "unhappy"
    test_session.add_rtp_status(
        new_status_time,
        new_status,
        status.status_columns["event_min_elapsed"] + 5,
        status.status_columns["num_processes"],
        status.status_columns["restart_hours_elapsed"] + 5.0 / 60.0,
    )

    result_mult = test_session.get_rtp_status(
        starttime=status.status_columns["time"] - TimeDelta(2, format="sec"),
        stoptime=new_status_time,
    )
    assert len(result_mult) == 2

    result2 = test_session.get_rtp_status(
        starttime=new_status_time - TimeDelta(2, format="sec")
    )
    assert len(result2) == 1
    result2 = result2[0]
    assert not result2.isclose(expected)

    result_most_recent = test_session.get_rtp_status()
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result2.isclose(result_most_recent)


def test_errors_rtp_status(mcsession, status):
    test_session = mcsession
    with pytest.raises(ValueError, match="time must be an astropy Time objec"):
        test_session.add_rtp_status("foo", *status.status_values[1:])

    test_session.add_rtp_status(*status.status_values)
    with pytest.raises(
        ValueError, match="starttime must be specified if most_recent is False"
    ):
        test_session.get_rtp_status(most_recent=False)
    with pytest.raises(ValueError, match="starttime must be an astropy time object"):
        test_session.get_rtp_status(starttime="unhappy")
    with pytest.raises(ValueError, match="stoptime must be an astropy time object"):
        test_session.get_rtp_status(
            starttime=status.status_columns["time"], stoptime="unhappy"
        )


def test_add_rtp_process_event(mcsession, observation, event):
    test_session = mcsession

    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    test_session.add_rtp_process_event(*event.event_values)

    exp_columns = event.event_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = RTPProcessEvent(**exp_columns)

    result = test_session.get_rtp_process_event(
        starttime=event.event_columns["time"] - TimeDelta(2, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    result_obsid = test_session.get_rtp_process_event(
        starttime=event.event_columns["time"] - TimeDelta(2, format="sec"),
        obsid=event.event_columns["obsid"],
    )
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result.isclose(expected)

    new_obsid_time = event.event_columns["time"] + TimeDelta(3 * 60, format="sec")
    new_obsid = utils.calculate_obsid(new_obsid_time)
    test_session.add_obs(
        Time(new_obsid_time),
        Time(new_obsid_time + TimeDelta(10 * 60, format="sec")),
        new_obsid,
    )
    obs_result = test_session.get_obs(obsid=new_obsid)
    assert obs_result[0].obsid == new_obsid

    test_session.add_rtp_process_event(
        new_obsid_time, new_obsid, event.event_columns["event"]
    )
    result_obsid = test_session.get_rtp_process_event(
        starttime=event.event_columns["time"] - TimeDelta(2, format="sec"),
        obsid=event.event_columns["obsid"],
    )
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result_obsid.isclose(expected)

    new_event_time = event.event_columns["time"] + TimeDelta(5 * 60, format="sec")
    new_event = "started"
    test_session.add_rtp_process_event(
        new_event_time, event.event_columns["obsid"], new_event
    )

    result_mult = test_session.get_rtp_process_event(
        starttime=event.event_columns["time"] - TimeDelta(2, format="sec"),
        stoptime=new_event_time,
    )
    assert len(result_mult) == 3

    result_most_recent = test_session.get_rtp_process_event()
    assert len(result_most_recent) == 1
    assert result_most_recent[0] == result_mult[2]

    result_mult_obsid = test_session.get_rtp_process_event(
        starttime=event.event_columns["time"] - TimeDelta(2, format="sec"),
        stoptime=new_event_time,
        obsid=event.event_columns["obsid"],
    )
    assert len(result_mult_obsid) == 2

    result_obsid_most_recent = test_session.get_rtp_process_event(
        obsid=event.event_columns["obsid"]
    )
    assert len(result_most_recent) == 1
    assert result_obsid_most_recent[0] == result_mult_obsid[1]

    result_new_obsid = test_session.get_rtp_process_event(
        starttime=event.event_columns["time"] - TimeDelta(2, format="sec"),
        obsid=new_obsid,
    )
    assert len(result_new_obsid) == 1
    result_new_obsid = result_new_obsid[0]
    assert not result_new_obsid.isclose(expected)


def test_errors_rtp_process_event(mcsession, observation, event):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        test_session.add_rtp_process_event("foo", *event.event_values[1:])

    test_session.add_rtp_process_event(*event.event_values)
    with pytest.raises(ValueError, match="starttime must be an astropy time object"):
        test_session.get_rtp_process_event(starttime="foo")
    with pytest.raises(ValueError, match="stoptime must be an astropy time object"):
        test_session.get_rtp_process_event(
            starttime=event.event_columns["time"], stoptime="bar"
        )


@pytest.mark.parametrize("multiple", [False, True])
def test_add_rtp_task_process_event(
    tmpdir, mcsession, observation, multiple, task_event, multiple_task_event
):
    test_session = mcsession

    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    if multiple:
        data_obj = multiple_task_event
        table_obj = RTPTaskMultipleProcessEvent
        add_method = getattr(test_session, "add_rtp_task_multiple_process_event")
        get_method = getattr(test_session, "get_rtp_task_multiple_process_event")
        obsid_name = "obsid_start"
    else:
        data_obj = task_event
        table_obj = RTPTaskProcessEvent
        add_method = getattr(test_session, "add_rtp_task_process_event")
        get_method = getattr(test_session, "get_rtp_task_process_event")
        obsid_name = "obsid"

    add_method(*data_obj.event_values)

    exp_columns = data_obj.event_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = table_obj(**exp_columns)

    result = get_method(
        starttime=data_obj.event_columns["time"] - TimeDelta(2, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    arg_dict = {
        "starttime": data_obj.event_columns["time"] - TimeDelta(2, format="sec"),
        obsid_name: data_obj.event_columns[obsid_name],
    }
    result_obsid = get_method(**arg_dict)
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result.isclose(expected)

    new_obsid_time = data_obj.event_columns["time"] + TimeDelta(3 * 60, format="sec")
    new_obsid = utils.calculate_obsid(new_obsid_time)
    test_session.add_obs(
        Time(new_obsid_time),
        Time(new_obsid_time + TimeDelta(10 * 60, format="sec")),
        new_obsid,
    )
    obs_result = test_session.get_obs(obsid=new_obsid)
    assert obs_result[0].obsid == new_obsid

    add_method(
        new_obsid_time,
        new_obsid,
        data_obj.event_columns["task_name"],
        data_obj.event_columns["event"],
    )
    arg_dict = {
        "starttime": data_obj.event_columns["time"] - TimeDelta(2, format="sec"),
        obsid_name: data_obj.event_columns[obsid_name],
        "task_name": data_obj.event_columns["task_name"],
    }
    result_obsid = get_method(**arg_dict)
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result_obsid.isclose(expected)

    new_event_time = data_obj.event_columns["time"] + TimeDelta(5 * 60, format="sec")
    new_event = "finished"
    add_method(
        new_event_time,
        data_obj.event_columns[obsid_name],
        data_obj.event_columns["task_name"],
        new_event,
    )

    result_mult = get_method(
        starttime=data_obj.event_columns["time"] - TimeDelta(2, format="sec"),
        stoptime=new_event_time,
    )
    assert len(result_mult) == 3

    result_most_recent = get_method()
    assert len(result_most_recent) == 1
    assert result_most_recent[0] == result_mult[2]

    arg_dict = {
        "starttime": data_obj.event_columns["time"] - TimeDelta(2, format="sec"),
        "stoptime": new_event_time,
        obsid_name: data_obj.event_columns[obsid_name],
    }
    result_mult_obsid = get_method(**arg_dict)
    assert len(result_mult_obsid) == 2

    arg_dict = {
        obsid_name: data_obj.event_columns[obsid_name],
        "task_name": data_obj.event_columns["task_name"],
    }
    result_obsid_most_recent = get_method(**arg_dict)
    assert len(result_most_recent) == 1
    assert result_obsid_most_recent[0] == result_mult_obsid[0]

    arg_dict = {
        "starttime": data_obj.event_columns["time"] - TimeDelta(2, format="sec"),
        obsid_name: new_obsid,
    }
    result_new_obsid = get_method(**arg_dict)
    assert len(result_new_obsid) == 1
    result_new_obsid = result_new_obsid[0]
    assert not result_new_obsid.isclose(expected)

    filename = os.path.join(tmpdir, "test_rtp_task_process_event_file.csv")
    arg_dict = {
        obsid_name: data_obj.event_columns[obsid_name],
        "task_name": data_obj.event_columns["task_name"],
        "write_to_file": True,
        "filename": filename,
    }
    get_method(**arg_dict)
    os.remove(filename)

    return


@pytest.mark.parametrize("multiple", [False, True])
def test_errors_rtp_task_process_event(
    mcsession, observation, multiple, task_event, multiple_task_event
):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    if multiple:
        data_obj = multiple_task_event
        add_method = getattr(test_session, "add_rtp_task_multiple_process_event")
        get_method = getattr(test_session, "get_rtp_task_multiple_process_event")
    else:
        data_obj = task_event
        add_method = getattr(test_session, "add_rtp_task_process_event")
        get_method = getattr(test_session, "get_rtp_task_process_event")

    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        add_method("foo", *data_obj.event_values[1:])

    add_method(*data_obj.event_values)
    with pytest.raises(ValueError, match="starttime must be an astropy time object"):
        get_method(starttime="foo")
    with pytest.raises(ValueError, match="stoptime must be an astropy time object"):
        get_method(starttime=task_event.event_columns["time"], stoptime="bar")
    with pytest.raises(
        ValueError, match="If most_recent is set to False, at least one of"
    ):
        get_method(most_recent=False)

    return


def test_classes_not_equal(mcsession, status, observation, event):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    test_session.add_rtp_process_event(*event.event_values)
    test_session.add_rtp_status(*status.status_values)

    status_result = test_session.get_rtp_status(
        starttime=status.status_columns["time"] - TimeDelta(2, format="sec")
    )
    assert len(status_result) == 1
    status_result = status_result[0]
    event_result = test_session.get_rtp_process_event(
        starttime=event.event_columns["time"] - TimeDelta(2, format="sec")
    )
    assert not status_result.isclose(event_result)


def test_add_rtp_process_record(mcsession, observation, record):
    test_session = mcsession

    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    test_session.add_rtp_process_record(*record.record_values)

    exp_columns = record.record_columns.copy()
    exp_columns["time"] = int(floor(exp_columns["time"].gps))
    expected = RTPProcessRecord(**exp_columns)

    result = test_session.get_rtp_process_record(
        starttime=record.record_columns["time"] - TimeDelta(2, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_obsid = test_session.get_rtp_process_record(
        starttime=record.record_columns["time"] - TimeDelta(2, format="sec"),
        obsid=record.record_columns["obsid"],
    )
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result_obsid.isclose(expected)

    new_obsid_time = record.record_columns["time"] + TimeDelta(3 * 60, format="sec")
    new_obsid = utils.calculate_obsid(new_obsid_time)
    test_session.add_obs(
        Time(new_obsid_time),
        Time(new_obsid_time + TimeDelta(10 * 60, format="sec")),
        new_obsid,
    )
    obs_result = test_session.get_obs(obsid=new_obsid)
    assert obs_result[0].obsid == new_obsid

    test_session.add_rtp_process_record(
        new_obsid_time, new_obsid, *record.record_values[2:11]
    )
    result_obsid = test_session.get_rtp_process_record(
        starttime=record.record_columns["time"] - TimeDelta(2, format="sec"),
        obsid=record.record_columns["obsid"],
    )
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result_obsid.isclose(expected)

    new_record_time = record.record_columns["time"] + TimeDelta(5 * 60, format="sec")
    new_pipeline = "new_pipe"
    test_session.add_rtp_process_record(
        new_record_time,
        record.record_columns["obsid"],
        new_pipeline,
        *record.record_values[3:11],
    )

    result_mult = test_session.get_rtp_process_record(
        starttime=record.record_columns["time"] - TimeDelta(2, format="sec"),
        stoptime=new_record_time,
    )
    assert len(result_mult) == 3

    result_most_recent = test_session.get_rtp_process_record()
    assert len(result_most_recent) == 1
    assert result_most_recent[0] == result_mult[2]

    result_mult_obsid = test_session.get_rtp_process_record(
        starttime=record.record_columns["time"] - TimeDelta(2, format="sec"),
        stoptime=new_record_time,
        obsid=record.record_columns["obsid"],
    )
    assert len(result_mult_obsid) == 2

    result_obsid_most_recent = test_session.get_rtp_process_record(
        obsid=record.record_columns["obsid"]
    )
    assert len(result_obsid_most_recent) == 1
    assert result_obsid_most_recent[0] == result_mult_obsid[1]

    result_new_obsid = test_session.get_rtp_process_record(
        starttime=record.record_columns["time"] - TimeDelta(2, format="sec"),
        obsid=new_obsid,
    )
    assert len(result_new_obsid) == 1
    result_new_obsid = result_new_obsid[0]

    assert not result_new_obsid.isclose(expected)


def test_errors_rtp_process_record(mcsession, observation, record):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    fake_vals = [1.0, "a", 2.0, "b", 3.0, "c", 4.0, "d", 5.0, "e"]
    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        test_session.add_rtp_process_record("foo", *fake_vals)

    test_session.add_rtp_process_record(*record.record_values)
    with pytest.raises(ValueError, match="starttime must be an astropy time object"):
        test_session.get_rtp_process_record(starttime="foo")
    with pytest.raises(ValueError, match="stoptime must be an astropy time object"):
        test_session.get_rtp_process_record(
            starttime=record.record_columns["time"], stoptime="bar"
        )


@pytest.mark.parametrize("multiple", [False, True])
def test_rtp_task_jobid(
    tmpdir, mcsession, observation, multiple, jobid, multiple_jobid
):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    if multiple:
        data_obj = multiple_jobid
        table_obj = RTPTaskMultipleJobID
        add_method = getattr(test_session, "add_rtp_task_multiple_jobid")
        get_method = getattr(test_session, "get_rtp_task_multiple_jobid")
        obsid_name = "obsid_start"
    else:
        data_obj = jobid
        table_obj = RTPTaskJobID
        add_method = getattr(test_session, "add_rtp_task_jobid")
        get_method = getattr(test_session, "get_rtp_task_jobid")
        obsid_name = "obsid"

    add_method(*data_obj.task_jobid_values)

    exp_columns = data_obj.task_jobid_columns.copy()
    exp_columns["start_time"] = int(floor(exp_columns["start_time"].gps))
    expected = table_obj(**exp_columns)

    get_keywords = {
        "starttime": data_obj.task_jobid_columns["start_time"]
        - TimeDelta(2, format="sec"),
        obsid_name: data_obj.task_jobid_columns[obsid_name],
    }
    result = get_method(**get_keywords)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    new_jobid_time = data_obj.task_jobid_columns["start_time"] + TimeDelta(
        60, format="sec"
    )
    new_task = "task2"
    add_method(
        data_obj.task_jobid_columns[obsid_name],
        new_task,
        new_jobid_time,
        *data_obj.task_jobid_values[3:],
    )

    result = get_method(**get_keywords)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    get_keywords["stoptime"] = data_obj.task_jobid_columns["start_time"] + TimeDelta(
        2 * 60, format="sec"
    )
    result = get_method(**get_keywords)
    assert len(result) == 2

    result_most_recent = get_method()
    assert len(result_most_recent) == 1
    assert result[1] == result_most_recent[0]

    get_keywords = {obsid_name: data_obj.task_jobid_columns[obsid_name]}
    result = get_method(**get_keywords)
    assert len(result) == 2

    get_keywords = {
        obsid_name: data_obj.task_jobid_columns[obsid_name],
        "most_recent": True,
    }
    result_obsid_most_recent = get_method(**get_keywords)
    assert len(result_obsid_most_recent) == 1
    assert result[1] == result_obsid_most_recent[0]

    result_task_no_times = get_method(
        task_name=data_obj.task_jobid_columns["task_name"], most_recent=False
    )
    assert len(result_task_no_times) == 1
    assert result_task_no_times[0].isclose(expected)

    result = get_method(
        starttime=data_obj.task_jobid_columns["start_time"]
        - TimeDelta(2, format="sec"),
        task_name=data_obj.task_jobid_columns["task_name"],
        stoptime=data_obj.task_jobid_columns["start_time"]
        + TimeDelta(2 * 60, format="sec"),
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_task_most_recent = get_method(
        task_name=data_obj.task_jobid_columns["task_name"], most_recent=True
    )
    assert len(result_task_most_recent) == 1
    assert result_task_most_recent[0].isclose(expected)

    new_task_time = data_obj.task_jobid_columns["start_time"] + TimeDelta(
        3 * 60, format="sec"
    )

    new_obsid_time = data_obj.task_jobid_columns["start_time"] + TimeDelta(
        3 * 60, format="sec"
    )
    new_obsid = utils.calculate_obsid(new_obsid_time)
    test_session.add_obs(
        Time(new_obsid_time),
        Time(new_obsid_time + TimeDelta(10 * 60, format="sec")),
        new_obsid,
    )
    obs_result = test_session.get_obs(obsid=new_obsid)
    assert obs_result[0].obsid == new_obsid

    add_method(
        new_obsid,
        data_obj.task_jobid_columns["task_name"],
        new_task_time,
        *data_obj.task_jobid_values[3:],
    )

    result = get_method(
        starttime=data_obj.task_jobid_columns["start_time"]
        - TimeDelta(2, format="sec"),
        task_name=data_obj.task_jobid_columns["task_name"],
        stoptime=data_obj.task_jobid_columns["start_time"]
        + TimeDelta(5 * 60, format="sec"),
    )
    assert len(result) == 2

    result_task_no_times = get_method(
        task_name=data_obj.task_jobid_columns["task_name"], most_recent=False
    )
    assert len(result_task_no_times) == 2
    assert result_task_no_times == result

    result_task_most_recent = get_method(
        task_name=data_obj.task_jobid_columns["task_name"], most_recent=True
    )
    assert len(result_task_most_recent) == 1
    assert result_task_most_recent[0].isclose(result[1])

    get_keywords = {
        "starttime": data_obj.task_jobid_columns["start_time"]
        - TimeDelta(2, format="sec"),
        obsid_name: data_obj.task_jobid_columns[obsid_name],
        "task_name": data_obj.task_jobid_columns["task_name"],
        "stoptime": data_obj.task_jobid_columns["start_time"]
        + TimeDelta(5 * 60, format="sec"),
    }
    result = get_method(**get_keywords)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    filename = os.path.join(tmpdir, "test_rtp_task_record_file.csv")
    get_keywords = {
        obsid_name: data_obj.task_jobid_columns[obsid_name],
        "task_name": data_obj.task_jobid_columns["task_name"],
        "write_to_file": True,
        "filename": filename,
    }
    get_method(**get_keywords)
    os.remove(filename)


@pytest.mark.parametrize("multiple", [False, True])
def test_errors_rtp_task_jobid(mcsession, observation, multiple, jobid, multiple_jobid):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    if multiple:
        data_obj = multiple_jobid
        add_method = getattr(test_session, "add_rtp_task_multiple_jobid")
        get_method = getattr(test_session, "get_rtp_task_multiple_jobid")
        obsid_name = "obsid_start"
    else:
        data_obj = jobid
        add_method = getattr(test_session, "add_rtp_task_jobid")
        get_method = getattr(test_session, "get_rtp_task_jobid")
        obsid_name = "obsid"

    with pytest.raises(ValueError, match="start_time must be an astropy Time object"):
        add_method(
            data_obj.task_jobid_columns[obsid_name],
            data_obj.task_jobid_columns["task_name"],
            "foo",
            data_obj.task_jobid_columns["job_id"],
        )

    with pytest.raises(
        ValueError,
        match=(
            "If most_recent is set to False, at least one of "
            + obsid_name
            + ", task_name or starttime must be specified."
        ),
    ):
        get_method(most_recent=False)


@pytest.mark.parametrize("multiple", [False, True])
def test_add_rtp_task_resource_record(
    tmpdir, mcsession, observation, multiple, task, task_multiple
):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    if multiple:
        data_obj = task_multiple
        table_obj = RTPTaskMultipleResourceRecord
        add_method = getattr(test_session, "add_rtp_task_multiple_resource_record")
        get_method = getattr(test_session, "get_rtp_task_multiple_resource_record")
        obsid_name = "obsid_start"
    else:
        data_obj = task
        table_obj = RTPTaskResourceRecord
        add_method = getattr(test_session, "add_rtp_task_resource_record")
        get_method = getattr(test_session, "get_rtp_task_resource_record")
        obsid_name = "obsid"

    add_method(*data_obj.task_resource_values)

    exp_columns = data_obj.task_resource_columns.copy()
    exp_columns["start_time"] = int(floor(exp_columns["start_time"].gps))
    exp_columns["stop_time"] = int(floor(exp_columns["stop_time"].gps))
    expected = table_obj(**exp_columns)

    get_keywords = {
        "starttime": data_obj.task_resource_columns["start_time"]
        - TimeDelta(2, format="sec"),
        obsid_name: data_obj.task_resource_columns[obsid_name],
    }
    result = get_method(**get_keywords)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    new_task_time = data_obj.task_resource_columns["start_time"] + TimeDelta(
        60, format="sec"
    )
    new_task = "task2"
    add_method(
        data_obj.task_resource_columns[obsid_name],
        new_task,
        new_task_time,
        *data_obj.task_resource_values[3:],
    )

    result = get_method(**get_keywords)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    get_keywords["stoptime"] = data_obj.task_resource_columns["start_time"] + TimeDelta(
        2 * 60, format="sec"
    )
    result = get_method(**get_keywords)
    assert len(result) == 2

    result_most_recent = get_method()
    assert len(result_most_recent) == 1
    assert result[1] == result_most_recent[0]

    get_keywords = {obsid_name: data_obj.task_resource_columns[obsid_name]}
    result = get_method(**get_keywords)
    assert len(result) == 2

    get_keywords["most_recent"] = True
    result_obsid_most_recent = get_method(**get_keywords)
    assert len(result_obsid_most_recent) == 1
    assert result[1] == result_obsid_most_recent[0]

    result_task_no_times = get_method(
        task_name=data_obj.task_resource_columns["task_name"], most_recent=False
    )
    assert len(result_task_no_times) == 1
    assert result_task_no_times[0].isclose(expected)

    result = get_method(
        starttime=data_obj.task_resource_columns["start_time"]
        - TimeDelta(2, format="sec"),
        task_name=data_obj.task_resource_columns["task_name"],
        stoptime=data_obj.task_resource_columns["start_time"]
        + TimeDelta(2 * 60, format="sec"),
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_task_most_recent = get_method(
        task_name=data_obj.task_resource_columns["task_name"], most_recent=True
    )
    assert len(result_task_most_recent) == 1
    assert result_task_most_recent[0].isclose(expected)

    new_task_time = data_obj.task_resource_columns["start_time"] + TimeDelta(
        3 * 60, format="sec"
    )

    new_obsid_time = data_obj.task_resource_columns["start_time"] + TimeDelta(
        3 * 60, format="sec"
    )
    new_obsid = utils.calculate_obsid(new_obsid_time)
    test_session.add_obs(
        Time(new_obsid_time),
        Time(new_obsid_time + TimeDelta(10 * 60, format="sec")),
        new_obsid,
    )
    obs_result = test_session.get_obs(obsid=new_obsid)
    assert obs_result[0].obsid == new_obsid

    add_method(
        new_obsid,
        data_obj.task_resource_columns["task_name"],
        new_task_time,
        *data_obj.task_resource_values[3:],
    )

    result = get_method(
        starttime=data_obj.task_resource_columns["start_time"]
        - TimeDelta(2, format="sec"),
        task_name=data_obj.task_resource_columns["task_name"],
        stoptime=data_obj.task_resource_columns["start_time"]
        + TimeDelta(5 * 60, format="sec"),
    )
    assert len(result) == 2

    result_task_no_times = get_method(
        task_name=data_obj.task_resource_columns["task_name"], most_recent=False
    )
    assert len(result_task_no_times) == 2
    assert result_task_no_times == result

    result_task_most_recent = get_method(
        task_name=data_obj.task_resource_columns["task_name"], most_recent=True
    )
    assert len(result_task_most_recent) == 1
    assert result_task_most_recent[0].isclose(result[1])

    get_keywords = {
        "starttime": data_obj.task_resource_columns["start_time"]
        - TimeDelta(2, format="sec"),
        obsid_name: data_obj.task_resource_columns[obsid_name],
        "task_name": data_obj.task_resource_columns["task_name"],
        "stoptime": data_obj.task_resource_columns["start_time"]
        + TimeDelta(5 * 60, format="sec"),
    }
    result = get_method(**get_keywords)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    filename = os.path.join(tmpdir, "test_rtp_task_record_file.csv")
    get_keywords = {
        obsid_name: data_obj.task_resource_columns[obsid_name],
        "task_name": data_obj.task_resource_columns["task_name"],
        "write_to_file": True,
        "filename": filename,
    }
    get_method(**get_keywords)
    os.remove(filename)

    # test computed column
    elapsed = result.elapsed
    assert np.isclose(elapsed, 600.0)


@pytest.mark.parametrize("multiple", [False, True])
def test_add_rtp_task_resource_record_nulls(
    mcsession, observation, record, multiple, task, task_multiple
):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    if multiple:
        data_obj = task_multiple
        table_obj = RTPTaskMultipleResourceRecord
        add_method = getattr(test_session, "add_rtp_task_multiple_resource_record")
        get_method = getattr(test_session, "get_rtp_task_multiple_resource_record")
        obsid_name = "obsid_start"
    else:
        data_obj = task
        table_obj = RTPTaskResourceRecord
        add_method = getattr(test_session, "add_rtp_task_resource_record")
        get_method = getattr(test_session, "get_rtp_task_resource_record")
        obsid_name = "obsid"

    # don't pass in max_memory or avg_cpu_load
    add_method(*data_obj.task_resource_values[:-2])

    exp_columns = data_obj.task_resource_columns.copy()
    # get rid of max_memory and avg_cpu_load columns
    exp_columns.pop("max_memory")
    exp_columns.pop("avg_cpu_load")
    exp_columns["start_time"] = int(floor(exp_columns["start_time"].gps))
    exp_columns["stop_time"] = int(floor(exp_columns["stop_time"].gps))
    expected = table_obj(**exp_columns)

    get_keywords = {
        "starttime": (
            data_obj.task_resource_columns["start_time"] - TimeDelta(2, format="sec")
        ),
        obsid_name: data_obj.task_resource_columns[obsid_name],
    }
    result = get_method(**get_keywords)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


@pytest.mark.parametrize("multiple", [False, True])
def test_errors_rtp_task_resource_record(
    mcsession, observation, multiple, task, task_multiple
):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    if multiple:
        data_obj = task_multiple
        add_method = getattr(test_session, "add_rtp_task_multiple_resource_record")
        get_method = getattr(test_session, "get_rtp_task_multiple_resource_record")
        obsid_name = "obsid_start"
    else:
        data_obj = task
        add_method = getattr(test_session, "add_rtp_task_resource_record")
        get_method = getattr(test_session, "get_rtp_task_resource_record")
        obsid_name = "obsid"

    fake_vals = [1, "a", 2, "b", 3, "c"]
    with pytest.raises(ValueError, match="start_time must be an astropy Time object"):
        add_method(*fake_vals)
    # test case where start_time is an astropy.time object, but stop_time isn't
    fake_vals2 = [1, "a", Time.now(), "b", 3, "c"]
    with pytest.raises(ValueError, match="stop_time must be an astropy Time object"):
        add_method(*fake_vals2)

    add_method(*data_obj.task_resource_values)

    with pytest.raises(
        ValueError,
        match=(
            "If most_recent is set to False, at least one of "
            + obsid_name
            + ", task_name "
            "or starttime must be specified."
        ),
    ):
        get_method(most_recent=False)


def test_add_rtp_launch_record(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # define properties
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    # add entry
    test_session.add_rtp_launch_record(obsid, jd, obs_tag, filename, prefix)

    # fetch entry
    query = mcsession.query(RTPLaunchRecord).filter(RTPLaunchRecord.obsid == obsid)
    result = query.all()
    assert len(result) == 1
    assert result[0].obsid == obsid
    assert result[0].jd == jd
    assert result[0].obs_tag == obs_tag
    assert result[0].filename == filename
    assert result[0].prefix == prefix
    assert result[0].submitted_time is None
    assert result[0].rtp_attempts == 0

    return


def test_add_rtp_launch_record_non_null_submitted_time(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # define properties
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    submitted_time = time + TimeDelta(60, format="sec")
    # add entry
    test_session.add_rtp_launch_record(
        obsid, jd, obs_tag, filename, prefix, submitted_time=submitted_time
    )

    # fetch entry
    query = mcsession.query(RTPLaunchRecord).filter(RTPLaunchRecord.obsid == obsid)
    result = query.all()
    assert len(result) == 1
    assert result[0].obsid == obsid
    assert result[0].jd == jd
    assert result[0].obs_tag == obs_tag
    assert result[0].filename == filename
    assert result[0].prefix == prefix
    assert result[0].submitted_time == int(floor(submitted_time.gps))
    assert result[0].rtp_attempts == 0

    return


def test_update_rtp_launch_record(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # define properties
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    submitted_time = time + TimeDelta(60, format="sec")
    # add entry
    test_session.add_rtp_launch_record(obsid, jd, obs_tag, filename, prefix)
    # update entry
    test_session.update_rtp_launch_record(obsid, submitted_time)

    # fetch entry
    query = mcsession.query(RTPLaunchRecord).filter(RTPLaunchRecord.obsid == obsid)
    result = query.all()
    assert len(result) == 1
    assert result[0].obsid == obsid
    assert result[0].jd == jd
    assert result[0].obs_tag == obs_tag
    assert result[0].filename == filename
    assert result[0].prefix == prefix
    assert result[0].submitted_time == int(floor(submitted_time.gps))
    assert result[0].rtp_attempts == 1

    return


def test_add_rtp_launch_record_errors(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # use bogus values for RTPLaunchRecord parameters
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    with pytest.raises(ValueError) as cm:
        mcsession.add_rtp_launch_record("foo", jd, obs_tag, filename, prefix)
    assert str(cm.value).startswith("obsid must be an integer.")

    with pytest.raises(ValueError) as cm:
        mcsession.add_rtp_launch_record(obsid, "foo", obs_tag, filename, prefix)
    assert str(cm.value).startswith("jd must be an integer.")

    with pytest.raises(ValueError) as cm:
        mcsession.add_rtp_launch_record(obsid, jd, 7, filename, prefix)
    assert str(cm.value).startswith("obs_tag must be a string.")

    with pytest.raises(ValueError) as cm:
        mcsession.add_rtp_launch_record(obsid, jd, obs_tag, 7, prefix)
    assert str(cm.value).startswith("filename must be a string.")

    with pytest.raises(ValueError) as cm:
        mcsession.add_rtp_launch_record(obsid, jd, obs_tag, filename, 7)
    assert str(cm.value).startswith("prefix must be a string.")

    with pytest.raises(ValueError) as cm:
        mcsession.add_rtp_launch_record(
            obsid, jd, obs_tag, filename, prefix, submitted_time="foo"
        )
    assert str(cm.value).startswith("submitted_time must be an astropy Time object.")

    with pytest.raises(ValueError) as cm:
        mcsession.add_rtp_launch_record(
            obsid,
            jd,
            obs_tag,
            filename,
            prefix,
            submitted_time=None,
            rtp_attempts="foo",
        )
    assert str(cm.value).startswith("rtp_attempts must be an integer.")

    return


def test_update_rtp_launch_record_errors(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # test trying to update a non-existent entry
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    submitted_time = time + TimeDelta(60, format="sec")
    with pytest.raises(RuntimeError) as cm:
        mcsession.update_rtp_launch_record(obsid, submitted_time)
    assert str(cm.value).startswith(
        f"RTP launch record does not exist for obsid {obsid}"
    )

    # test using something besides an astropy object for submitted_time
    with pytest.raises(ValueError) as cm:
        mcsession.update_rtp_launch_record(obsid, "foo")
    assert str(cm.value).startswith("submitted_time must be an astropy Time object")

    return


def test_get_rtp_launch_record(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # add an entry to the table
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    test_session.add_rtp_launch_record(obsid, jd, obs_tag, filename, prefix)

    # test getting it back again
    rtp_launch_records = mcsession.get_rtp_launch_record(obsid)
    assert len(rtp_launch_records) == 1
    assert rtp_launch_records[0].obsid == obsid

    return


def test_get_rtp_launch_record_by_time(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # add an etnry to the table with a submitted_time
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    submitted_time = time + TimeDelta(60, format="sec")
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    test_session.add_rtp_launch_record(
        obsid, jd, obs_tag, filename, prefix, submitted_time=submitted_time
    )

    # get selecting on submitted_time
    rtp_launch_records = mcsession.get_rtp_launch_record_by_time(most_recent=True)
    assert len(rtp_launch_records) == 1
    assert rtp_launch_records[0].submitted_time == int(np.floor(submitted_time.gps))

    return


def test_get_rtp_launch_record_by_jd(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # add an entry to the table
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    test_session.add_rtp_launch_record(obsid, jd, obs_tag, filename, prefix)

    # test selecting on jd
    rtp_launch_records = mcsession.get_rtp_launch_record_by_jd(jd)
    assert len(rtp_launch_records) == 1
    assert rtp_launch_records[0].jd == jd

    return


def test_get_rtp_launch_record_by_rtp_attempts(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # add an entry to the table
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    test_session.add_rtp_launch_record(obsid, jd, obs_tag, filename, prefix)

    # test selecting on rtp_attempts
    rtp_launch_records = mcsession.get_rtp_launch_record_by_rtp_attempts(0)
    assert len(rtp_launch_records) == 1
    assert rtp_launch_records[0].rtp_attempts == 0

    return


def test_get_rtp_launch_record_by_obs_tag(mcsession, observation):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # add an entry to the table
    time = observation.observation_values[0]
    obsid = observation.observation_values[2]
    jd = int(floor(time.jd))
    obs_tag = "engineering"
    filename = "zen.2457000.12345.sum.uvh5"
    prefix = "/mnt/sn1"
    test_session.add_rtp_launch_record(obsid, jd, obs_tag, filename, prefix)

    # test selecting on obs_tag
    rtp_launch_records = mcsession.get_rtp_launch_record_by_obs_tag(obs_tag)
    assert len(rtp_launch_records) == 1
    assert rtp_launch_records[0].obs_tag == obs_tag

    return


def test_add_rtp_task_multiple_track(
    tmpdir, mcsession, observation, task_multiple, multiple_track
):
    test_session = mcsession

    # add obsids:
    for entry in multiple_track.observation_values:
        test_session.add_obs(*entry)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 3

    # add task multiple resource record
    test_session.add_rtp_task_multiple_resource_record(
        *task_multiple.task_resource_values
    )
    task_result = test_session.get_rtp_task_multiple_resource_record()
    assert len(task_result) == 1

    exp_list = []
    for ind, entry in enumerate(multiple_track.track_values):
        test_session.add_rtp_task_multiple_track(*entry)
        exp_list.append(RTPTaskMultipleTrack(**multiple_track.track_columns[ind]))
    assert len(exp_list) == 3

    result_obsid_start = test_session.get_rtp_task_multiple_track(
        obsid_start=multiple_track.track_columns[0]["obsid_start"]
    )
    assert len(result_obsid_start) == 3
    for ind, result in enumerate(result_obsid_start):
        assert result.isclose(exp_list[ind])

    result_task = test_session.get_rtp_task_multiple_track(
        task_name=multiple_track.track_columns[0]["task_name"]
    )
    for ind, result in enumerate(result_task):
        assert result.isclose(result_obsid_start[ind])

    result_obsid = test_session.get_rtp_task_multiple_track(
        obsid=multiple_track.track_columns[0]["obsid"]
    )
    assert len(result_obsid) == 1
    assert result_obsid[0].isclose(exp_list[0])

    filename = os.path.join(tmpdir, "test_rtp_track_multiple_file.csv")
    test_session.get_rtp_task_multiple_track(
        obsid_start=multiple_track.track_columns[0]["obsid_start"],
        write_to_file=True,
        filename=filename,
    )
    os.remove(filename)
