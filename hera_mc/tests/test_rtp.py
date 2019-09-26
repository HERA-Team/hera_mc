# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.rtp`."""
from __future__ import absolute_import, division, print_function

import os
from math import floor

import pytest
import numpy as np
from astropy.time import Time, TimeDelta

from ..rtp import (RTPStatus, RTPProcessEvent, RTPProcessRecord,
                   RTPTaskResourceRecord)
from .. import utils
from hera_mc.data import DATA_PATH


@pytest.fixture(scope='module')
def status():
    class DataHolder(object):
        time = Time.now() - TimeDelta(30 * 60, format='sec')
        status_names = ['time', 'status', 'event_min_elapsed',
                        'num_processes', 'restart_hours_elapsed']
        status_values = [time, 'happy', 3.6, 8, 10.2]
        status_columns = dict(zip(status_names, status_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del(data)

    return


@pytest.fixture(scope='module')
def observation():
    class DataHolder(object):
        time = Time.now() - TimeDelta(30 * 60, format='sec')
        obsid = utils.calculate_obsid(time)
        observation_names = ['starttime', 'stoptime', 'obsid']
        observation_values = [time, time + TimeDelta(10 * 60, format='sec'),
                              obsid]
        observation_columns = dict(zip(observation_names, observation_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del(data)

    return


@pytest.fixture(scope='module')
def event(observation):
    class DataHolder(object):
        time = Time.now() - TimeDelta(30 * 60, format='sec')
        event_names = ['time', 'obsid', 'event']
        event_values = [time, observation.obsid, 'queued']
        event_columns = dict(zip(event_names, event_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del(data)

    return


@pytest.fixture(scope='module')
def record(observation):
    class DataHolder(object):
        time = Time.now() - TimeDelta(30 * 60, format='sec')
        record_names = ['time', 'obsid', 'pipeline_list', 'rtp_git_version',
                        'rtp_git_hash', 'hera_qm_git_version',
                        'hera_qm_git_hash',
                        'hera_cal_git_version', 'hera_cal_git_hash',
                        'pyuvdata_git_version', 'pyuvdata_git_hash']
        record_values = [time, observation.obsid, 'sample_pipe', 'v0.0.1',
                         'lskdjf24l', 'v0.1.0',
                         'abcd34d', 'v1.0.0', 'jkfldi39', 'v2.0.0', 'fjklj828']
        record_columns = dict(zip(record_names, record_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del(data)

    return


@pytest.fixture(scope='module')
def task(observation):
    class DataHolder(object):
        time = Time.now() - TimeDelta(30 * 60, format='sec')
        task_resource_names = ['obsid', 'task_name', 'start_time', 'stop_time',
                               'max_memory', 'avg_cpu_load']
        task_resource_values = [observation.obsid, 'OMNICAL', time,
                                time + TimeDelta(10 * 60, format='sec'),
                                16.2, 1.01]
        task_resource_columns = dict(zip(task_resource_names,
                                         task_resource_values))

    data = DataHolder()

    # yields the data we need but will continue to the del call after tests
    yield data

    # some post-test object cleanup
    del(data)

    return


def test_add_rtp_status(mcsession, status):
    test_session = mcsession
    test_session.add_rtp_status(*status.status_values)

    exp_columns = status.status_columns.copy()
    exp_columns['time'] = int(floor(exp_columns['time'].gps))
    expected = RTPStatus(**exp_columns)

    result = test_session.get_rtp_status(
        starttime=status.status_columns['time'] - TimeDelta(2, format='sec'))
    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    new_status_time = (status.status_columns['time']
                       + TimeDelta(5 * 60, format='sec'))
    new_status = 'unhappy'
    test_session.add_rtp_status(new_status_time, new_status,
                                status.status_columns['event_min_elapsed'] + 5,
                                status.status_columns['num_processes'],
                                status.status_columns['restart_hours_elapsed']
                                + 5. / 60.)

    result_mult = test_session.get_rtp_status(
        starttime=status.status_columns['time'] - TimeDelta(2, format='sec'),
        stoptime=new_status_time)
    assert len(result_mult) == 2

    result2 = test_session.get_rtp_status(
        starttime=new_status_time - TimeDelta(2, format='sec'))
    assert len(result2) == 1
    result2 = result2[0]
    assert not result2.isclose(expected)

    result_most_recent = test_session.get_rtp_status()
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result2.isclose(result_most_recent)


def test_errors_rtp_status(mcsession, status):
    test_session = mcsession
    pytest.raises(ValueError, test_session.add_rtp_status, 'foo',
                  *status.status_values[1:])

    test_session.add_rtp_status(*status.status_values)
    pytest.raises(ValueError, test_session.get_rtp_status, most_recent=False)
    pytest.raises(ValueError, test_session.get_rtp_status, starttime='unhappy')
    pytest.raises(ValueError, test_session.get_rtp_status,
                  starttime=status.status_columns['time'], stoptime='unhappy')


def test_add_rtp_process_event(mcsession, observation, event):
    test_session = mcsession

    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    test_session.add_rtp_process_event(*event.event_values)

    exp_columns = event.event_columns.copy()
    exp_columns['time'] = int(floor(exp_columns['time'].gps))
    expected = RTPProcessEvent(**exp_columns)

    result = test_session.get_rtp_process_event(
        starttime=event.event_columns['time'] - TimeDelta(2, format='sec'))
    assert len(result) == 1
    result = result[0]
    result_obsid = test_session.get_rtp_process_event(
        starttime=event.event_columns['time'] - TimeDelta(2, format='sec'),
        obsid=event.event_columns['obsid'])
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result.isclose(expected)

    new_obsid_time = (event.event_columns['time']
                      + TimeDelta(3 * 60, format='sec'))
    new_obsid = utils.calculate_obsid(new_obsid_time)
    test_session.add_obs(
        Time(new_obsid_time),
        Time(new_obsid_time + TimeDelta(10 * 60, format='sec')), new_obsid)
    obs_result = test_session.get_obs(obsid=new_obsid)
    assert obs_result[0].obsid == new_obsid

    test_session.add_rtp_process_event(new_obsid_time, new_obsid,
                                       event.event_columns['event'])
    result_obsid = test_session.get_rtp_process_event(
        starttime=event.event_columns['time'] - TimeDelta(2, format='sec'),
        obsid=event.event_columns['obsid'])
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result_obsid.isclose(expected)

    new_event_time = (event.event_columns['time']
                      + TimeDelta(5 * 60, format='sec'))
    new_event = 'started'
    test_session.add_rtp_process_event(
        new_event_time, event.event_columns['obsid'], new_event)

    result_mult = test_session.get_rtp_process_event(
        starttime=event.event_columns['time'] - TimeDelta(2, format='sec'),
        stoptime=new_event_time)
    assert len(result_mult) == 3

    result_most_recent = test_session.get_rtp_process_event()
    assert len(result_most_recent) == 1
    assert result_most_recent[0] == result_mult[2]

    result_mult_obsid = test_session.get_rtp_process_event(
        starttime=event.event_columns['time'] - TimeDelta(2, format='sec'),
        stoptime=new_event_time, obsid=event.event_columns['obsid'])
    assert len(result_mult_obsid) == 2

    result_obsid_most_recent = test_session.get_rtp_process_event(
        obsid=event.event_columns['obsid'])
    assert len(result_most_recent) == 1
    assert result_obsid_most_recent[0] == result_mult_obsid[1]

    result_new_obsid = test_session.get_rtp_process_event(
        starttime=event.event_columns['time'] - TimeDelta(2, format='sec'),
        obsid=new_obsid)
    assert len(result_new_obsid) == 1
    result_new_obsid = result_new_obsid[0]
    assert not result_new_obsid.isclose(expected)


def test_errors_rtp_process_event(mcsession, observation, event):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    pytest.raises(ValueError, test_session.add_rtp_process_event, 'foo',
                  *event.event_values[1:])

    test_session.add_rtp_process_event(*event.event_values)
    pytest.raises(ValueError, test_session.get_rtp_process_event,
                  starttime='foo')
    pytest.raises(ValueError, test_session.get_rtp_process_event,
                  starttime=event.event_columns['time'], stoptime='bar')


def test_classes_not_equal(mcsession, status, observation, event):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    test_session.add_rtp_process_event(*event.event_values)
    test_session.add_rtp_status(*status.status_values)

    status_result = test_session.get_rtp_status(
        starttime=status.status_columns['time'] - TimeDelta(2, format='sec'))
    assert len(status_result) == 1
    status_result = status_result[0]
    event_result = test_session.get_rtp_process_event(
        starttime=event.event_columns['time'] - TimeDelta(2, format='sec'))
    assert not status_result.isclose(event_result)


def test_add_rtp_process_record(mcsession, observation, record):
    test_session = mcsession

    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    test_session.add_rtp_process_record(*record.record_values)

    exp_columns = record.record_columns.copy()
    exp_columns['time'] = int(floor(exp_columns['time'].gps))
    expected = RTPProcessRecord(**exp_columns)

    result = test_session.get_rtp_process_record(
        starttime=record.record_columns['time'] - TimeDelta(2, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_obsid = test_session.get_rtp_process_record(
        starttime=record.record_columns['time'] - TimeDelta(2, format='sec'),
        obsid=record.record_columns['obsid'])
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result_obsid.isclose(expected)

    new_obsid_time = (record.record_columns['time']
                      + TimeDelta(3 * 60, format='sec'))
    new_obsid = utils.calculate_obsid(new_obsid_time)
    test_session.add_obs(
        Time(new_obsid_time),
        Time(new_obsid_time + TimeDelta(10 * 60, format='sec')), new_obsid)
    obs_result = test_session.get_obs(obsid=new_obsid)
    assert obs_result[0].obsid == new_obsid

    test_session.add_rtp_process_record(
        new_obsid_time, new_obsid, *record.record_values[2:11])
    result_obsid = test_session.get_rtp_process_record(
        starttime=record.record_columns['time'] - TimeDelta(2, format='sec'),
        obsid=record.record_columns['obsid'])
    assert len(result_obsid) == 1
    result_obsid = result_obsid[0]
    assert result_obsid.isclose(expected)

    new_record_time = (record.record_columns['time']
                       + TimeDelta(5 * 60, format='sec'))
    new_pipeline = 'new_pipe'
    test_session.add_rtp_process_record(
        new_record_time, record.record_columns['obsid'], new_pipeline,
        *record.record_values[3:11])

    result_mult = test_session.get_rtp_process_record(
        starttime=record.record_columns['time'] - TimeDelta(2, format='sec'),
        stoptime=new_record_time)
    assert len(result_mult) == 3

    result_most_recent = test_session.get_rtp_process_record()
    assert len(result_most_recent) == 1
    assert result_most_recent[0] == result_mult[2]

    result_mult_obsid = test_session.get_rtp_process_record(
        starttime=record.record_columns['time'] - TimeDelta(2, format='sec'),
        stoptime=new_record_time, obsid=record.record_columns['obsid'])
    assert len(result_mult_obsid) == 2

    result_obsid_most_recent = test_session.get_rtp_process_record(
        obsid=record.record_columns['obsid'])
    assert len(result_obsid_most_recent) == 1
    assert result_obsid_most_recent[0] == result_mult_obsid[1]

    result_new_obsid = test_session.get_rtp_process_record(
        starttime=record.record_columns['time'] - TimeDelta(2, format='sec'),
        obsid=new_obsid)
    assert len(result_new_obsid) == 1
    result_new_obsid = result_new_obsid[0]

    assert not result_new_obsid.isclose(expected)


def test_errors_rtp_process_record(mcsession, observation, record):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    fake_vals = [1., 'a', 2., 'b', 3., 'c', 4., 'd', 5., 'e']
    pytest.raises(ValueError, test_session.add_rtp_process_record, 'foo',
                  *fake_vals)

    test_session.add_rtp_process_record(*record.record_values)
    pytest.raises(ValueError, test_session.get_rtp_process_record,
                  starttime='foo')
    pytest.raises(ValueError, test_session.get_rtp_process_record,
                  starttime=record.record_columns['time'], stoptime='bar')


def test_add_rtp_task_resource_record(mcsession, observation, task):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    test_session.add_rtp_task_resource_record(*task.task_resource_values)

    exp_columns = task.task_resource_columns.copy()
    exp_columns['start_time'] = int(floor(exp_columns['start_time'].gps))
    exp_columns['stop_time'] = int(floor(exp_columns['stop_time'].gps))
    expected = RTPTaskResourceRecord(**exp_columns)

    result = test_session.get_rtp_task_resource_record(
        starttime=task.task_resource_columns['start_time']
        - TimeDelta(2, format='sec'),
        obsid=task.task_resource_columns['obsid'])
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    new_task_time = (task.task_resource_columns['start_time']
                     + TimeDelta(60, format='sec'))
    new_task = 'task2'
    test_session.add_rtp_task_resource_record(
        task.task_resource_columns['obsid'], new_task, new_task_time,
        *task.task_resource_values[3:])

    result = test_session.get_rtp_task_resource_record(
        starttime=task.task_resource_columns['start_time']
        - TimeDelta(2, format='sec'),
        obsid=task.task_resource_columns['obsid'])
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_rtp_task_resource_record(
        starttime=task.task_resource_columns['start_time']
        - TimeDelta(2, format='sec'),
        obsid=task.task_resource_columns['obsid'],
        stoptime=task.task_resource_columns['start_time']
        + TimeDelta(2 * 60, format='sec'))
    assert len(result) == 2

    result_most_recent = test_session.get_rtp_task_resource_record()
    assert len(result_most_recent) == 1
    assert result[1] == result_most_recent[0]

    result = test_session.get_rtp_task_resource_record(
        obsid=task.task_resource_columns['obsid'])
    assert len(result) == 2

    result_obsid_most_recent = test_session.get_rtp_task_resource_record(
        obsid=task.task_resource_columns['obsid'])
    assert len(result_obsid_most_recent) == 2
    assert result == result_obsid_most_recent

    result = test_session.get_rtp_task_resource_record(
        starttime=task.task_resource_columns['start_time']
        - TimeDelta(2, format='sec'),
        task_name=task.task_resource_columns['task_name'],
        stoptime=task.task_resource_columns['start_time']
        + TimeDelta(2 * 60, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_task_most_recent = test_session.get_rtp_task_resource_record(
        task_name=task.task_resource_columns['task_name'])
    assert len(result_task_most_recent) == 1
    assert result_task_most_recent[0].isclose(expected)

    new_task_time = (task.task_resource_columns['start_time']
                     + TimeDelta(3 * 60, format='sec'))

    new_obsid_time = (task.task_resource_columns['start_time']
                      + TimeDelta(3 * 60, format='sec'))
    new_obsid = utils.calculate_obsid(new_obsid_time)
    test_session.add_obs(
        Time(new_obsid_time),
        Time(new_obsid_time + TimeDelta(10 * 60, format='sec')), new_obsid)
    obs_result = test_session.get_obs(obsid=new_obsid)
    assert obs_result[0].obsid == new_obsid

    test_session.add_rtp_task_resource_record(
        new_obsid, task.task_resource_columns['task_name'], new_task_time,
        *task.task_resource_values[3:])

    result = test_session.get_rtp_task_resource_record(
        starttime=task.task_resource_columns['start_time']
        - TimeDelta(2, format='sec'),
        task_name=task.task_resource_columns['task_name'],
        stoptime=task.task_resource_columns['start_time']
        + TimeDelta(5 * 60, format='sec'))
    assert len(result) == 2

    result_task_most_recent = test_session.get_rtp_task_resource_record(
        task_name=task.task_resource_columns['task_name'])
    assert len(result_task_most_recent) == 1
    assert result_task_most_recent[0].isclose(result[1])

    result = test_session.get_rtp_task_resource_record(
        starttime=task.task_resource_columns['start_time']
        - TimeDelta(2, format='sec'),
        obsid=task.task_resource_columns['obsid'],
        task_name=task.task_resource_columns['task_name'],
        stoptime=task.task_resource_columns['start_time']
        + TimeDelta(5 * 60, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    filename = os.path.join(DATA_PATH, 'test_rtp_task_record_file.csv')
    test_session.get_rtp_task_resource_record(
        obsid=task.task_resource_columns['obsid'],
        task_name=task.task_resource_columns['task_name'],
        write_to_file=True, filename=filename)
    os.remove(filename)

    # test computed column
    elapsed = result.elapsed
    assert np.isclose(elapsed, 600.)


def test_add_rtp_task_resource_record_nulls(mcsession, observation, record,
                                            task):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    # don't pass in max_memory or avg_cpu_load
    test_session.add_rtp_task_resource_record(*task.task_resource_values[:-2])

    exp_columns = task.task_resource_columns.copy()
    # get rid of max_memory and avg_cpu_load columns
    exp_columns.pop('max_memory')
    exp_columns.pop('avg_cpu_load')
    exp_columns['start_time'] = int(floor(exp_columns['start_time'].gps))
    exp_columns['stop_time'] = int(floor(exp_columns['stop_time'].gps))
    expected = RTPTaskResourceRecord(**exp_columns)

    result = test_session.get_rtp_task_resource_record(
        starttime=(task.task_resource_columns['start_time']
                   - TimeDelta(2, format='sec')),
        obsid=record.record_columns['obsid'])
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


def test_errors_rtp_task_resource_record(mcsession, observation, task):
    test_session = mcsession
    test_session.add_obs(*observation.observation_values)
    obs_result = test_session.get_obs()
    assert len(obs_result) == 1

    fake_vals = [1, 'a', 2, 'b', 3, 'c']
    pytest.raises(ValueError, test_session.add_rtp_task_resource_record,
                  *fake_vals)
    # test case where start_time is an astropy.time object, but stop_time isn't
    fake_vals2 = [1, 'a', Time.now(), 'b', 3, 'c']
    pytest.raises(ValueError, test_session.add_rtp_task_resource_record,
                  *fake_vals2)

    test_session.add_rtp_task_resource_record(*task.task_resource_values)

    pytest.raises(ValueError, test_session.get_rtp_task_resource_record,
                  task_name=task.task_resource_columns['task_name'],
                  most_recent=False)

    pytest.raises(ValueError, test_session.get_rtp_task_resource_record,
                  most_recent=False)
