# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.correlator`."""
import copy
import datetime
import hashlib
import os
import re
import warnings
from math import floor

import numpy as np
import pytest

with warnings.catch_warnings():
    # This filter can be removed when pyuvdata (and maybe other imported packages?)
    # are updated to use importlib.metadata rather than pkg_resources
    warnings.filterwarnings("ignore", "Implementing implicit namespace packages")
    import pyuvdata.tests as uvtest
import yaml
from astropy.time import Time, TimeDelta

import hera_mc.correlator as corr
from hera_mc import cm_partconnect, mc
from hera_mc.data import DATA_PATH

from ..tests import (
    TEST_DEFAULT_REDIS_HOST,
    checkWarnings,
    onsite,
    requires_default_redis,
    requires_redis,
)

TEST_TIME1 = Time("2016-01-10 01:15:23", scale="utc")
TEST_TIME2 = TEST_TIME1 + TimeDelta(120.0, format="sec")


@pytest.fixture(scope="module")
def feng_config():
    config_file = os.path.join(DATA_PATH, "test_data", "hera_feng_config_example.yaml")
    with open(config_file, "r") as stream:
        config = yaml.safe_load(stream)

    return config_file, config


@pytest.fixture(scope="module")
def corr_config():
    config_file = os.path.join(DATA_PATH, "test_data", "corr_config_example.yaml")
    with open(config_file, "r") as stream:
        config = yaml.safe_load(stream)

    return config_file, config


@pytest.fixture(scope="module")
def corr_config_dict(corr_config):
    return {
        "time": Time(1230372020, format="gps"),
        "hash": "testhash",
        "config": corr_config[1],
    }


@pytest.fixture(scope="module")
def init_args():
    return (
        "Namespace(config_file=None, eth=True, initialize=True, "
        + "mansync=False, noise=False, program=False, "
        + f"redishost='{TEST_DEFAULT_REDIS_HOST}', sync=True, tvg=False)"
    )


@pytest.fixture(scope="module")
def snapversion(corr_config, init_args):
    return {
        "udpSender:hera_node_keep_alive.py": {
            "timestamp": datetime.datetime(2019, 4, 2, 19, 7, 17, 438357),
            "version": "0.0.1-1eaa49ea",
        },
        "hera_corr_f:hera_snap_redis_monitor.py": {
            "timestamp": datetime.datetime(2019, 4, 2, 19, 7, 14, 317679),
            "version": "0.0.1-3c7fdaf6",
        },
        "udpSender:hera_node_cmd_check.py": {
            "timestamp": datetime.datetime(2019, 4, 2, 19, 7, 17, 631614),
            "version": "0.0.1-1eaa49ea",
        },
        "udpSender:hera_node_receiver.py": {
            "timestamp": datetime.datetime(2019, 4, 2, 19, 7, 16, 555086),
            "version": "0.0.1-1eaa49ea",
        },
        "hera_corr_cm": {
            "timestamp": datetime.datetime(2019, 4, 2, 19, 7, 17, 644984),
            "version": "0.0.1-11a573c9",
        },
        "snap": {
            "config": corr_config[1],
            "config_md5": "testhash",
            "config_timestamp": datetime.datetime(2019, 2, 18, 5, 41, 29, 376363),
            "init_args": init_args,
            "timestamp": datetime.datetime(2019, 3, 27, 8, 28, 25, 806626),
            "version": "0.0.1-3c7fdaf6",
        },
    }


@pytest.fixture(scope="module")
def snapstatus():
    return {
        "heraNode700Snap0": {
            "last_programmed": datetime.datetime(2016, 1, 10, 23, 16, 3),
            "pmb_alert": True,
            "pps_count": 595687,
            "serial": "SNPA000700",
            "temp": 57.984954833984375,
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
            "uptime": 595686,
            "is_programmed": True,
            "adc_is_configured": True,
            "is_initialized": True,
            "dest_is_configured": True,
            "version": "7.1",
            "sample_rate": 500.0,
            "input": "adc,adc,adc,adc,adc,adc",
        },
        "heraNode701Snap3": {
            "last_programmed": datetime.datetime(2016, 1, 10, 23, 16, 3),
            "pmb_alert": False,
            "pps_count": 595699,
            "serial": "SNPD000703",
            "temp": 59.323028564453125,
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            "uptime": 595699,
            "is_programmed": False,
            "adc_is_configured": False,
            "is_initialized": False,
            "dest_is_configured": False,
            "version": "7.1",
            "sample_rate": 500.0,
            "input": "noise-1,noise-2,noise-3,noise-4,noise-5,noise-6",
        },
    }


@pytest.fixture(scope="module")
def snapstatus_none():
    return {
        "heraNode700Snap0": {
            "last_programmed": None,
            "pmb_alert": None,
            "pps_count": None,
            "serial": None,
            "temp": None,
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
            "uptime": None,
            "is_programmed": None,
            "adc_is_configured": None,
            "is_initialized": None,
            "dest_is_configured": None,
            "version": None,
            "sample_rate": None,
            "input": None,
        },
        "heraNode701Snap3": {
            "last_programmed": datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
            "pmb_alert": False,
            "pps_count": 595699,
            "serial": "SNPD000703",
            "temp": 59.323028564453125,
            "timestamp": None,
            "uptime": 595699,
            "is_programmed": None,
            "adc_is_configured": None,
            "is_initialized": None,
            "dest_is_configured": None,
            "version": None,
            "sample_rate": None,
            "input": None,
        },
    }


@pytest.fixture(scope="module")
def snap_feng_init_status():
    return {
        "log_time_start": "2022-08-01T17:20:37.025000",
        "maxout": "heraNode9Snap3",
        "unconfig": ("heraNode19Snap3,heraNode13Snap3,heraNode18Snap1,heraNode18Snap2"),
        "timestamp": "2022-08-02T15:53:17",
        "working": ("heraNode12Snap2,heraNode12Snap3,heraNode12Snap0,heraNode12Snap1"),
        "log_time_stop": "2022-08-01T17:20:37.941000",
    }


@pytest.fixture(scope="module")
def antstatus():
    return {
        "4:e": {
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            "f_host": "heraNode700Snap0",
            "host_ant_id": 3,
            "adc_mean": -0.5308380126953125,
            "adc_rms": 3.0134560488579285,
            "adc_power": 9.080917358398438,
            "pam_atten": 0,
            "pam_power": -13.349140985640002,
            "pam_voltage": 10.248,
            "pam_current": 0.6541,
            "pam_id": "[112, 217, 32, 59, 1, 0, 0, 14]",
            "fem_voltage": 6.496,
            "fem_current": 0.5627000000000001,
            "fem_id": "[0, 168, 19, 212, 51, 51, 255, 255]",
            "fem_switch": "antenna",
            "fem_lna_power": True,
            "fem_imu_theta": 1.3621702512711602,
            "fem_imu_phi": 30.762719534238915,
            "fem_temp": 26.327341308593752,
            "fft_of": False,
            "eq_coeffs": (np.zeros((1024)) + 56.921875).tolist(),
            "histogram": (np.zeros((256)) + 10).tolist(),
        },
        "31:n": {
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            "f_host": "heraNode4Snap3",
            "host_ant_id": 7,
            "adc_mean": -0.4805450439453125,
            "adc_rms": 16.495319974304454,
            "adc_power": 272.0955810546875,
            "pam_atten": 0,
            "pam_power": -32.03119784856,
            "pam_voltage": 10.268,
            "pam_current": 0.6695000000000001,
            "pam_id": "[112, 84, 143, 59, 1, 0, 0, 242]",
            "fem_voltage": float("nan"),
            "fem_current": float("nan"),
            "fem_id": "[0, 168, 19, 212, 51, 51, 255, 255]",
            "fem_switch": "noise",
            "fem_lna_power": False,
            "fem_imu_theta": 1.3621702512711602,
            "fem_imu_phi": 30.762719534238915,
            "fem_temp": 27.828854980468755,
            "fft_of": True,
            "eq_coeffs": (np.zeros((1024)) + 73.46875).tolist(),
            "histogram": (np.zeros((256)) + 12).tolist(),
        },
    }


@pytest.fixture(scope="module")
def antstatus_none():
    return {
        "4:e": {
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            "f_host": None,
            "host_ant_id": None,
            "adc_mean": None,
            "adc_rms": None,
            "adc_power": None,
            "pam_atten": None,
            "pam_power": None,
            "pam_voltage": None,
            "pam_current": None,
            "pam_id": None,
            "fem_voltage": None,
            "fem_current": None,
            "fem_id": None,
            "fem_switch": None,
            "fem_lna_power": None,
            "fem_imu_theta": None,
            "fem_imu_phi": None,
            "fem_temp": None,
            "fft_of": None,
            "eq_coeffs": None,
            "histogram": None,
        },
        "31:n": {
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            "f_host": None,
            "host_ant_id": None,
            "adc_mean": None,
            "adc_rms": None,
            "adc_power": None,
            "pam_atten": None,
            "pam_power": None,
            "pam_voltage": None,
            "pam_current": None,
            "pam_id": None,
            "fem_voltage": float("nan"),
            "fem_current": float("nan"),
            "fem_id": None,
            "fem_switch": "Unknown mode",
            "fem_lna_power": None,
            "fem_imu_theta": None,
            "fem_imu_phi": None,
            "fem_temp": None,
            "fft_of": None,
            "eq_coeffs": None,
            "histogram": None,
        },
    }


def test_py3_hashing(feng_config):
    # make sure I get the same answer as with python 2.7 & no explicit encoding
    # (like the correlator)
    py27_hash = "3b03414da0abe738aae071cccb911377"

    with open(feng_config[0], "r") as fh:
        config_string = fh.read().encode("utf-8")
        config_hash = hashlib.md5(config_string).hexdigest()

    assert py27_hash == config_hash


def test_add_array_signal_source(mcsession):
    t1 = TEST_TIME1.copy()
    t2 = TEST_TIME2.copy()

    mcsession.add_array_signal_source(t1, "antenna")

    source_expected = corr.ArraySignalSource(time=int(floor(t1.gps)), source="antenna")
    source_result = mcsession.get_array_signal_source(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(source_result) == 1
    source_result = source_result[0]
    assert source_result.isclose(source_expected)

    mcsession.add_array_signal_source(t2, "digital_same_seed")
    source_expected2 = corr.ArraySignalSource(
        time=int(floor(t2.gps)), source="digital_same_seed"
    )

    source_result = mcsession.get_array_signal_source(source="antenna")
    assert len(source_result) == 1
    source_result = source_result[0]
    assert source_result.isclose(source_expected)

    # get most recent
    source_result = mcsession.get_array_signal_source()
    assert len(source_result) == 1
    source_result = source_result[0]
    assert source_result.isclose(source_expected2)

    source_result = mcsession.get_array_signal_source(
        starttime=t1 - TimeDelta(3.0, format="sec"),
        stoptime=t2 + TimeDelta(3.0, format="sec"),
    )
    assert len(source_result) == 2
    assert source_result[0].isclose(source_expected)

    assert source_result[1].isclose(source_expected2)

    source_result_mr_start = mcsession.get_array_signal_source(
        most_recent=True, starttime=t1 + TimeDelta(3.0, format="sec")
    )
    source_result_start = mcsession.get_array_signal_source(
        starttime=t1 + TimeDelta(3.0, format="sec")
    )

    assert len(source_result_mr_start) == 1
    assert len(source_result_start) == 1
    assert not source_result_mr_start[0].isclose(source_result_start[0])

    assert source_result_mr_start[0].isclose(source_expected)
    assert source_result_start[0].isclose(source_expected2)

    # this tests different column types not matching:
    source_expected2 = corr.ArraySignalSource(time=t2.gps, source="digital_same_seed")
    assert not source_result[1].isclose(source_expected2)


@pytest.mark.parametrize(
    "snap_source,snap_seed,snap_time,fem_switch,fem_time,source,time",
    [
        ("adc", "same", TEST_TIME1, "antenna", TEST_TIME2, "antenna", TEST_TIME2),
        ("adc", "same", TEST_TIME2, "noise", TEST_TIME1, "noise", TEST_TIME2),
        ("adc", "same", TEST_TIME1, "load", TEST_TIME2, "load", TEST_TIME2),
        (
            "noise",
            "same",
            TEST_TIME1,
            "antenna",
            TEST_TIME2,
            "digital_same_seed",
            TEST_TIME1,
        ),
        (
            "noise",
            "diff",
            TEST_TIME2,
            "load",
            TEST_TIME1,
            "digital_different_seed",
            TEST_TIME2,
        ),
    ],
)
def test_define_array_signal_source(
    snap_source, snap_seed, snap_time, fem_switch, fem_time, source, time
):
    this_time, this_source = corr._define_array_signal_source(
        snap_source, snap_seed, snap_time, fem_switch, fem_time
    )

    assert this_source == source
    assert this_time == time


@pytest.mark.parametrize(
    "snap_source,snap_seed,snap_time,fem_switch,fem_time,err_msg",
    [
        (
            "foo",
            "same",
            TEST_TIME1,
            "antenna",
            TEST_TIME2,
            "SNAP input information is foo, should be 'adc' or 'noise'",
        ),
        (
            "adc",
            "same",
            TEST_TIME2,
            "foo",
            TEST_TIME1,
            "On FEM input, FEM switch state is foo, should be one of "
            f"{corr.signal_source_list[0:3]}.",
        ),
        (
            "noise",
            "foo",
            TEST_TIME1,
            "antenna",
            TEST_TIME2,
            "On digital noise, seed type is foo, should be 'same' or 'diff'.",
        ),
    ],
)
def test_define_array_signal_source_errors(
    snap_source, snap_seed, snap_time, fem_switch, fem_time, err_msg
):
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        corr._define_array_signal_source(
            snap_source, snap_seed, snap_time, fem_switch, fem_time
        )


@requires_redis
def test_add_array_signal_source_from_redis(mcsession):
    current_array_source = mcsession.add_array_signal_source_from_redis(
        redishost=TEST_DEFAULT_REDIS_HOST, testing=True
    )
    mcsession.add_array_signal_source_from_redis(redishost=TEST_DEFAULT_REDIS_HOST)

    # get most recent
    source_result = mcsession.get_array_signal_source()
    assert len(source_result) == 1

    assert source_result[0].isclose(current_array_source)


def test_add_array_signal_errors(mcsession):
    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        mcsession.add_array_signal_source("foo", "antenna")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "invalid signal source value was passed. Passed value was foo, must be one "
            f"of: {corr.signal_source_list}"
        ),
    ):
        mcsession.add_array_signal_source(TEST_TIME1, "foo")


def test_add_correlator_component_event_time(mcsession):
    t1 = TEST_TIME1.copy()
    t2 = TEST_TIME2.copy()

    mcsession.add_correlator_component_event_time("f_engine", "sync", t1)

    comp_event_expected = corr.CorrelatorComponentEventTime(
        component="f_engine", event="sync", time=t1.gps
    )
    comp_event_result = mcsession.get_correlator_component_event_time(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(comp_event_result) == 1
    comp_event_result = comp_event_result[0]
    assert comp_event_result.isclose(comp_event_expected)

    mcsession.add_correlator_component_event_time("catcher", "start", t2)
    comp_event_expected2 = corr.CorrelatorComponentEventTime(
        component="catcher", event="start", time=t2.gps
    )

    comp_event_result = mcsession.get_correlator_component_event_time(
        component="f_engine"
    )
    assert len(comp_event_result) == 1
    comp_event_result = comp_event_result[0]
    assert comp_event_result.isclose(comp_event_result)

    # get most recent
    comp_event_result = mcsession.get_correlator_component_event_time()
    assert len(comp_event_result) == 1
    comp_event_result = comp_event_result[0]
    assert comp_event_result.isclose(comp_event_expected2)

    comp_event_result = mcsession.get_correlator_component_event_time(
        starttime=t1 - TimeDelta(3.0, format="sec"),
        stoptime=t2 + TimeDelta(3.0, format="sec"),
    )
    assert len(comp_event_result) == 2
    assert comp_event_result[0].isclose(comp_event_expected)

    assert comp_event_result[1].isclose(comp_event_expected2)


@requires_redis
@pytest.mark.parametrize(
    "input_dict,event,time",
    [
        (
            {"state": "True", "time": str(int(TEST_TIME1.unix))},
            "start",
            TEST_TIME1,
        ),
        (
            {"state": "False", "time": str(int(TEST_TIME1.unix))},
            "stop",
            TEST_TIME1,
        ),
        ({}, None, None),
    ],
)
def test_get_catcher_start_stop_time_from_redis(input_dict, event, time):
    """Test logic branching by passing in spoofed redis output"""
    out_event, out_time = corr._get_catcher_start_stop_time_from_redis(
        taking_data_dict=input_dict
    )

    assert out_event == event
    assert out_time == time

    expdict = {}
    expdict["f_engine"] = {
        "event": "sync",
        "time": corr._get_f_engine_sync_time_from_redis(),
    }
    if event is not None:
        expdict["catcher"] = {"event": event, "time": time}

    outdict = corr._get_correlator_component_event_times_from_redis(
        taking_data_dict=input_dict
    )

    assert outdict == expdict


@requires_redis
@pytest.mark.parametrize("catcher_same", (True, False))
def test_get_catcher_start_stop_time_from_redis_with_timeouts(mcsession, catcher_same):
    # add a start time of 5 seconds ago
    starttime_unix = int(Time.now().unix - 5)
    mcsession.add_correlator_component_event_time_from_redis(
        taking_data_dict={
            "state": "True",
            "time": str(starttime_unix),
        }
    )
    comp_event_expected = corr.CorrelatorComponentEventTime(
        component="catcher", event="start", time=Time(starttime_unix, format="unix").gps
    )
    comp_event_result = mcsession.get_correlator_component_event_time(
        component="catcher"
    )[0]
    assert comp_event_result.isclose(comp_event_expected)

    # simulate a timeout to add a stop_timeout event
    mcsession.add_correlator_component_event_time_from_redis(taking_data_dict={})
    mcsession.commit()

    comp_event_result2 = mcsession.get_correlator_component_event_time(
        component="catcher"
    )[0]
    assert comp_event_result2.event == "stop_timeout"
    assert comp_event_result2.time > Time(starttime_unix, format="unix").gps
    # make this be a copy so it's not changed with the later update
    comp_event_result2 = copy.deepcopy(comp_event_result2)

    if catcher_same:
        # Pass in the same catcher start time as before, causing the timeout entry to be
        # deleted.
        mcsession.add_correlator_component_event_time_from_redis(
            taking_data_dict={
                "state": "True",
                "time": str(starttime_unix),
            }
        )
        comp_event_result = mcsession.get_correlator_component_event_time(
            component="catcher"
        )[0]
        assert comp_event_result.event == "start"
        assert comp_event_result.isclose(comp_event_expected)
    else:
        # Pass in a later catcher start time than before, causing the timeout entry to be
        # updated and a new catcher start time to be entered.
        mcsession.add_correlator_component_event_time_from_redis(
            taking_data_dict={
                "state": "True",
                "time": str(starttime_unix + 3),
            }
        )
        comp_event_expected = corr.CorrelatorComponentEventTime(
            component="catcher",
            event="start",
            time=Time(starttime_unix + 3, format="unix").gps,
        )
        comp_event_result = mcsession.get_correlator_component_event_time(
            component="catcher"
        )[0]
        assert comp_event_result.isclose(comp_event_expected)

        comp_event_result3 = mcsession.get_correlator_component_event_time(
            component="catcher", event="stop_timeout"
        )[0]

        assert not comp_event_result3.isclose(comp_event_result2)
        assert comp_event_result3.component == comp_event_result2.component
        assert comp_event_result3.event == comp_event_result2.event
        assert comp_event_result3.time < comp_event_result2.time


@requires_redis
def test_add_correlator_component_event_time_from_redis(mcsession):
    comp_event_list = mcsession.add_correlator_component_event_time_from_redis(
        redishost=TEST_DEFAULT_REDIS_HOST, testing=True
    )
    assert len(comp_event_list) >= 1
    assert len(comp_event_list) <= 2

    components = []
    events = []
    for comp_event_obj in comp_event_list:
        components.append(comp_event_obj.component)
        events.append(comp_event_obj.event)

    assert "f_engine" in components
    if len(comp_event_list) == 2:
        assert "catcher" in components

    mcsession.add_correlator_component_event_time_from_redis(
        redishost=TEST_DEFAULT_REDIS_HOST
    )

    # get most recent
    comp_event_result = mcsession.get_correlator_component_event_time(
        component="f_engine"
    )
    assert len(comp_event_result) == 1

    f_engine_index = components.index("f_engine")
    assert comp_event_result[0].isclose(comp_event_list[f_engine_index])

    if len(comp_event_list) == 2:
        catcher_index = components.index("catcher")

        comp_event_result = mcsession.get_correlator_component_event_time(
            component="catcher"
        )
        assert len(comp_event_result) == 1
        assert comp_event_result[0].isclose(comp_event_list[catcher_index])


def test_add_correlator_component_event_time_errors(mcsession):
    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        mcsession.add_correlator_component_event_time("f_engine", "sync", "foo")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "invalid component value was passed. Passed component was "
            f"foo, must be one of: {corr.corr_component_events.keys()}"
        ),
    ):
        mcsession.add_correlator_component_event_time("foo", "start", TEST_TIME1)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "invalid event value for catcher was passed. Passed value was "
            f"sync, must be one of: {corr.corr_component_events['catcher']}"
        ),
    ):
        mcsession.add_correlator_component_event_time("catcher", "sync", TEST_TIME1)


def test_add_correlator_catcher_file(mcsession):
    t1 = TEST_TIME1.copy()
    t2 = TEST_TIME2.copy()

    filename1 = (
        str(int(np.fix(t1.jd)))
        + "/zen."
        + np.format_float_positional(t1.jd, precision=5)
        + ".sum.dat"
    )

    filename2 = (
        str(int(np.fix(t2.jd)))
        + "/zen."
        + np.format_float_positional(t2.jd, precision=5)
        + ".sum.dat"
    )

    mcsession.add_correlator_catcher_file(t1, filename1)

    catcher_file_expected = corr.CorrelatorCatcherFile(
        time=int(floor(t1.gps)), filename=filename1
    )
    catcher_file_result = mcsession.get_correlator_catcher_file(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(catcher_file_result) == 1
    catcher_file_result = catcher_file_result[0]
    assert catcher_file_result.isclose(catcher_file_expected)

    mcsession.add_correlator_catcher_file(t2, filename2)
    catcher_file_expected2 = corr.CorrelatorCatcherFile(
        time=int(floor(t2.gps)), filename=filename2
    )

    # get most recent
    catcher_file_result = mcsession.get_correlator_catcher_file()
    assert len(catcher_file_result) == 1
    catcher_file_result = catcher_file_result[0]
    assert catcher_file_result.isclose(catcher_file_expected2)

    catcher_file_result = mcsession.get_correlator_catcher_file(
        starttime=t1 - TimeDelta(3.0, format="sec"),
        stoptime=t2 + TimeDelta(3.0, format="sec"),
    )
    assert len(catcher_file_result) == 2
    assert catcher_file_result[0].isclose(catcher_file_expected)

    assert catcher_file_result[1].isclose(catcher_file_expected2)


def test_add_correlator_catcher_file_errors(mcsession):
    t1 = TEST_TIME1.copy()

    filename1 = (
        str(int(np.fix(t1.jd)))
        + "/zen."
        + np.format_float_positional(t1.jd, precision=5)
        + ".sum.dat"
    )

    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        mcsession.add_correlator_catcher_file("foo", filename1)


def test_get_catcher_file_from_redis():
    t1 = TEST_TIME1.copy()

    unix_second = int(np.floor(t1.unix))
    input_dict = {"time": unix_second, "filename": "NONE"}
    time, filename = corr._get_catcher_file_from_redis(test_dict=input_dict)

    assert time == Time(unix_second, format="unix")
    assert filename is None


@requires_redis
def test_add_correlator_catcher_file_from_redis(mcsession):
    current_file = mcsession.add_correlator_catcher_file_from_redis(
        redishost=TEST_DEFAULT_REDIS_HOST, testing=True
    )
    mcsession.add_correlator_catcher_file_from_redis(redishost=TEST_DEFAULT_REDIS_HOST)

    # get most recent
    catcher_file_result = mcsession.get_correlator_catcher_file()
    assert len(catcher_file_result) == 1

    assert catcher_file_result[0].isclose(current_file)


def test_add_corr_file_queues(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()
    t2 = TEST_TIME2.copy()

    int_jd1 = int(np.fix(t1.jd))
    filename1 = f"{int_jd1}/zen.{t1.jd}.sum.uvh5"
    t1a = t1 - TimeDelta(10.0 * 12, format="sec")
    filename1a = f"{int_jd1}/zen.{t1a.jd}.sum.uvh5"

    test_session.add_correlator_file_queues(t1, "raw", 13, filename1a, filename1)
    t0 = t1 - TimeDelta(60.0, format="sec")
    int_jd0 = int(np.fix(t0.jd))
    filename0 = f"{int_jd0}/zen.{t0.jd}.sum.uvh5"
    t0a = t0 - TimeDelta(10.0, format="sec")
    filename0a = f"{int_jd0}/zen.{t0a.jd}.sum.uvh5"

    test_session.add_correlator_file_queues(t1, "converted", 2, filename0a, filename0)

    queue_expected1 = corr.CorrelatorFileQueues(
        time=int(floor(t1.gps)),
        queue="raw",
        length=13,
        oldest_entry=filename1a,
        newest_entry=filename1,
    )

    queue_result = test_session.get_correlator_file_queues(
        starttime=t1 - TimeDelta(3.0, format="sec"), queue="raw"
    )
    assert len(queue_result) == 1
    queue_result = queue_result[0]
    assert queue_result.isclose(queue_expected1)

    queue_expected0 = corr.CorrelatorFileQueues(
        time=int(floor(t1.gps)),
        queue="converted",
        length=2,
        oldest_entry=filename0a,
        newest_entry=filename0,
    )
    queue_result = test_session.get_correlator_file_queues(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(queue_result) == 2
    for obj in queue_result:
        if obj.queue == "raw":
            assert obj.isclose(queue_expected1)
        else:
            assert obj.isclose(queue_expected0)

    result_most_recent = test_session.get_correlator_file_queues(queue="raw")
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(queue_expected1)

    int_jd2 = int(np.fix(t2.jd))
    filename2 = f"{int_jd2}/zen.{t2.jd}.sum.uvh5"
    t2a = t2 - TimeDelta(10.0 * 4, format="sec")
    filename2a = f"{int_jd2}/zen.{t2a.jd}.sum.uvh5"
    test_session.add_correlator_file_queues(t2, "raw", 5, filename2a, filename2)
    test_session.add_correlator_file_queues(t2, "lib_upload_purgatory", 0, None, None)

    queue_expected2 = corr.CorrelatorFileQueues(
        time=int(floor(t2.gps)),
        queue="raw",
        length=5,
        oldest_entry=filename2a,
        newest_entry=filename2,
    )

    result = test_session.get_correlator_file_queues(queue="raw")
    assert len(result) == 1
    result = result[0]
    assert result.isclose(queue_expected2)

    queue_expected3 = corr.CorrelatorFileQueues(
        time=int(floor(t2.gps)),
        queue="lib_upload_purgatory",
        length=0,
        newest_entry=None,
        oldest_entry=None,
    )
    result = test_session.get_correlator_file_queues(queue="lib_upload_purgatory")
    assert len(result) == 1
    result = result[0]

    assert result.isclose(queue_expected3)

    result = test_session.get_correlator_file_queues(
        starttime=t1 + TimeDelta(200.0, format="sec")
    )
    assert result == []


def test_add_corr_file_queues_errors(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()

    int_jd1 = int(np.fix(t1.jd))
    filename1 = f"{int_jd1}/zen.{t1.jd}.sum.uvh5"
    t1a = t1 - TimeDelta(10.0 * 12, format="sec")
    filename1a = f"{int_jd1}/zen.{t1a.jd}.sum.uvh5"

    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        test_session.add_correlator_file_queues("foo", "raw", 13, filename1, filename1a)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Unknown queue name: foo. Should be one of: "
            f"{list(corr.file_queue_names.keys())}"
        ),
    ):
        test_session.add_correlator_file_queues(t1, "foo", 13, filename1, filename1a)


@requires_redis
def test_add_corr_file_queues_redis(mcsession):
    queue_list = mcsession.add_correlator_file_queues_from_redis(
        redishost=TEST_DEFAULT_REDIS_HOST, testing=True
    )
    assert len(queue_list) == 7

    mcsession.add_correlator_file_queues_from_redis(redishost=TEST_DEFAULT_REDIS_HOST)
    # get most recent
    queue_result = mcsession.get_correlator_file_queues()

    assert len(queue_result) == len(queue_list)

    queue_lengths = [obj.length for obj in queue_result]

    assert max(queue_lengths) > 0


def test_update_correlator_file_eod(mcsession):
    test_session = mcsession
    t0 = TEST_TIME1.copy()
    t1 = t0 + TimeDelta(30 * 60.0, format="sec")
    t2 = t1 + TimeDelta(30 * 60.0, format="sec")
    tfail = t2 + TimeDelta(2 * 3600.0, format="sec")

    jd = int(t0.jd)

    test_session.update_correlator_file_eod(t0, jd, 0)
    expected_eod = corr.CorrelatorFileEOD.create(jd, t0, None, None, None)
    result = test_session.get_correlator_file_eod(jd)
    assert len(result) == 1
    assert expected_eod.isclose(result[0])

    # check that nothing happens if this status is already in the db
    test_session.update_correlator_file_eod(t1, jd, 0)
    result = test_session.get_correlator_file_eod(jd)
    assert len(result) == 1
    assert expected_eod.isclose(result[0])

    test_session.update_correlator_file_eod(t1, jd, 1)
    expected_eod = corr.CorrelatorFileEOD.create(jd, t0, t1, None, None)
    result = test_session.get_correlator_file_eod(jd)
    assert len(result) == 1
    assert expected_eod.isclose(result[0])

    test_session.update_correlator_file_eod(t2, jd, 2)
    expected_eod = corr.CorrelatorFileEOD.create(jd, t0, t1, t2, None)
    result = test_session.get_correlator_file_eod(jd)
    assert len(result) == 1
    assert expected_eod.isclose(result[0])

    test_session.update_correlator_file_eod(tfail, jd, -1)
    expected_eod = corr.CorrelatorFileEOD.create(jd, t0, t1, t2, tfail)
    result = test_session.get_correlator_file_eod(jd)
    assert len(result) == 1
    assert expected_eod.isclose(result[0])


def test_update_correlator_file_eod_errors(mcsession):
    test_session = mcsession
    t0 = TEST_TIME1.copy()
    t1 = t0 + TimeDelta(30 * 60.0, format="sec")
    t2 = t1 + TimeDelta(30 * 60.0, format="sec")
    tfail = t2 + TimeDelta(2 * 3600.0, format="sec")

    jd = int(t0.jd)

    with pytest.raises(ValueError, match="time must an astropy Time object"):
        test_session.update_correlator_file_eod(t0.gps, jd, 0)

    with pytest.raises(
        ValueError, match="time_start must be None or an astropy Time object"
    ):
        corr.CorrelatorFileEOD.create(jd, t0.jd, t1, t2, tfail)


@requires_redis
def test_update_correlator_file_eod_redis(mcsession):
    jd_eod_dict = corr._get_correlator_file_eod_status_from_redis(
        redishost=TEST_DEFAULT_REDIS_HOST
    )
    time = Time.now()
    mcsession.update_correlator_file_eod_from_redis(redishost=TEST_DEFAULT_REDIS_HOST)

    assert len(jd_eod_dict) > 0

    for jd, status in jd_eod_dict.items():
        eod_result = mcsession.get_correlator_file_eod(jd)
        assert len(eod_result) == 1

        file_eod_status_columns = {
            0: "time_start",
            1: "time_converted",
            2: "time_uploaded",
            -1: "time_launch_failed",
        }
        assert status in file_eod_status_columns.keys()
        eod_kwarg = {}
        for eod_status, name in file_eod_status_columns.items():
            if eod_status == status:
                eod_kwarg[name] = int(time.gps)
            else:
                eod_kwarg[name] = None
        expected_obj = corr.CorrelatorFileEOD(jd=jd, **eod_kwarg)
        assert eod_result[0].isclose(expected_obj)


def test_add_corr_config(mcsession, corr_config):
    test_session = mcsession
    t1 = TEST_TIME1.copy()
    t2 = TEST_TIME2.copy()

    config_hash = "testhash"

    test_session.add_correlator_config_file(config_hash, corr_config[0])
    test_session.commit()
    test_session.add_correlator_config_status(t1, config_hash)
    test_session.commit()

    file_expected = corr.CorrelatorConfigFile(
        config_hash=config_hash, filename=corr_config[0]
    )
    status_expected = corr.CorrelatorConfigStatus(
        time=int(floor(t1.gps)), config_hash=config_hash
    )

    file_result = test_session.get_correlator_config_file(config_hash=config_hash)
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    # check you get the same thing using time filtering
    file_result, time_list = test_session.get_correlator_config_file()
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    status_result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(status_result) == 1
    status_result = status_result[0]
    assert status_result.isclose(status_expected)

    config_hash2 = "testhash2"
    test_session.add_correlator_config_file(config_hash2, corr_config[0])
    test_session.commit()
    test_session.add_correlator_config_status(t2, config_hash2)
    test_session.commit()

    result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), config_hash=config_hash
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(status_expected)

    result_most_recent = test_session.get_correlator_config_status(
        config_hash=config_hash
    )
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(status_expected)

    status_expected = corr.CorrelatorConfigStatus(
        time=int(floor(t2.gps)), config_hash=config_hash2
    )

    result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), config_hash=config_hash2
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(status_expected)

    result_most_recent = test_session.get_correlator_config_status(
        config_hash=config_hash2
    )
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(status_expected)

    result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t2
    )
    assert len(result) == 2

    result_most_recent = test_session.get_correlator_config_status()
    assert len(result_most_recent) == 1

    result = test_session.get_correlator_config_status(
        starttime=t1 + TimeDelta(200.0, format="sec")
    )
    assert result == []


@pytest.mark.parametrize("rosetta_exists", (True, False))
def test_add_correlator_config_from_corrcm(mcsession, corr_config_dict, rosetta_exists):
    pytest.importorskip("hera_corr_cm")
    test_session = mcsession
    corr_config_dict_use = copy.deepcopy(corr_config_dict)

    if not rosetta_exists:
        # use an earlier time before the part_rosetta entries start
        corr_config_dict_use["time"] = Time(1512770942, format="unix")

    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=corr_config_dict_use, testing=True
    )

    for obj in corr_config_list:
        test_session.add(obj)
        test_session.commit()

    t1 = corr_config_dict_use["time"]
    status_result = test_session.get_correlator_config_status(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(status_result) == 1
    file_result = test_session.get_correlator_config_file(
        config_hash=status_result[0].config_hash
    )

    config_filename = "correlator_config_" + str(int(floor(t1.gps))) + ".yaml"

    file_expected = corr.CorrelatorConfigFile(
        config_hash="testhash", filename=config_filename
    )
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    # check you get the same thing using time filtering
    file_result, time_list = test_session.get_correlator_config_file(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(file_result) == 1
    file_result = file_result[0]
    assert file_result.isclose(file_expected)

    status_expected = corr.CorrelatorConfigStatus(
        time=int(floor(t1.gps)), config_hash="testhash"
    )

    assert len(status_result) == 1
    status_result = status_result[0]
    assert status_result.isclose(status_expected)

    config_params_result = test_session.get_correlator_config_params(
        config_hash=status_result.config_hash
    )

    config_param_dict = {
        "fft_shift": 15086,
        "fpgfile": "redis:snap_fengine_2020-07-16_1253.fpg",
        "dest_port": 8511,
        "log_walsh_step_size": 3,
        "walsh_order": 32,
        "walsh_delay": 600,
        "fengines": ",".join(
            [
                "heraNode700Snap0",
                "heraNode700Snap1",
                "heraNode700Snap2",
                "heraNode700Snap3",
            ]
        ),
        "xengines": ",".join([str(xeng) for xeng in [0, 1]]),
        "x0:chan_range": ",".join([str(chan) for chan in [1536, 1920]]),
        "x1:chan_range": ",".join([str(chan) for chan in [1920, 2304]]),
        "x0:even:ip": "10.80.40.197",
        "x0:even:mac": "2207786215621",
        "x0:odd:ip": "10.80.40.206",
        "x0:odd:mac": "2207786215630",
        "x1:even:ip": "10.80.40.229",
        "x1:even:mac": "2207786215653",
        "x1:odd:ip": "10.80.40.238",
        "x1:odd:mac": "2207786215662",
    }

    assert len(config_params_result) == len(config_param_dict)

    # check that using the time options works too
    config_params_result2, time_list = test_session.get_correlator_config_params(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(config_params_result2) == len(config_param_dict)
    assert len(time_list) == len(config_param_dict)
    for time_obj in time_list[1:]:
        assert time_obj == time_list[0]

    for param, val in config_param_dict.items():
        config_params_result = test_session.get_correlator_config_params(
            config_hash=status_result.config_hash,
            parameter=param,
        )
        config_params_expected = corr.CorrelatorConfigParams(
            config_hash="testhash",
            parameter=param,
            value=str(val),
        )
        assert len(config_params_result) == 1
        config_params_result = config_params_result[0]
        assert config_params_result.isclose(config_params_expected)

        # check that using the time options works too
        config_params_result, time_list = test_session.get_correlator_config_params(
            starttime=t1 - TimeDelta(3.0, format="sec"),
            parameter=param,
        )
        assert len(config_params_result) == 1
        config_params_result = config_params_result[0]
        assert config_params_result.isclose(config_params_expected)

    config_active_snaps_result = test_session.get_correlator_config_active_snaps(
        config_hash=status_result.config_hash,
    )
    active_snaps_list = [
        "heraNode700Snap0",
        "heraNode700Snap1",
        "heraNode700Snap2",
        "heraNode700Snap3",
    ]
    assert len(config_active_snaps_result) == len(active_snaps_list)

    # check that we can also get the nodes & snap loc nums
    (
        config_active_snaps_result,
        node_list,
        snap_loc_list,
    ) = test_session.get_correlator_config_active_snaps(
        config_hash=status_result.config_hash,
        return_node_loc_num=True,
    )
    assert len(config_active_snaps_result) == len(active_snaps_list)
    # since the request doesn't specify a time, the rosetta mapping for "now" is used.
    for index, active_snap in enumerate(config_active_snaps_result):
        assert node_list[index] == int(active_snap.hostname.split("S")[0][8:])
        assert snap_loc_list[index] == int(active_snap.hostname[-1])

    # check that using the time options works too
    # with return_node_loc_num
    if not rosetta_exists:
        # this tests that Nones are returned if there's not mapping info
        (
            config_active_snaps_result2,
            time_list,
            node_list,
            snap_loc_list,
        ) = test_session.get_correlator_config_active_snaps(
            starttime=t1 - TimeDelta(30.0, format="sec"), return_node_loc_num=True
        )
        assert len(config_active_snaps_result2) == len(active_snaps_list)
        for index, active_snap in enumerate(config_active_snaps_result):
            assert node_list[index] is None
            assert snap_loc_list[index] is None

    # and without return_node_loc_num
    (
        config_active_snaps_result2,
        time_list,
    ) = test_session.get_correlator_config_active_snaps(
        starttime=t1 - TimeDelta(30.0, format="sec"), return_node_loc_num=False
    )
    assert len(config_active_snaps_result2) == len(active_snaps_list)
    assert len(time_list) == len(active_snaps_list)
    for index, active_snap in enumerate(config_active_snaps_result):
        if rosetta_exists:
            assert node_list[index] == int(active_snap.hostname.split("S")[0][8:])
            assert snap_loc_list[index] == int(active_snap.hostname[-1])

    for index, result in enumerate(config_active_snaps_result):
        this_hostname = result.hostname
        assert this_hostname in active_snaps_list
        expected_result = corr.CorrelatorConfigActiveSNAP(
            config_hash="testhash",
            hostname=this_hostname,
        )
        assert result.isclose(expected_result)
        assert config_active_snaps_result2[index].isclose(expected_result)

    config_input_index_result = test_session.get_correlator_config_input_index(
        config_hash=status_result.config_hash
    )
    input_index_dict = {
        "0": {"hostname": "heraNode700Snap0", "ant_loc": 0},
        "1": {"hostname": "heraNode700Snap0", "ant_loc": 1},
        "2": {"hostname": "heraNode700Snap0", "ant_loc": 2},
        "3": {"hostname": "heraNode700Snap1", "ant_loc": 0},
        "4": {"hostname": "heraNode700Snap1", "ant_loc": 1},
        "5": {"hostname": "heraNode700Snap1", "ant_loc": 2},
        "6": {"hostname": "heraNode700Snap2", "ant_loc": 0},
        "7": {"hostname": "heraNode700Snap2", "ant_loc": 1},
        "8": {"hostname": "heraNode700Snap2", "ant_loc": 2},
        "9": {"hostname": "heraNode700Snap3", "ant_loc": 0},
        "10": {"hostname": "heraNode700Snap3", "ant_loc": 1},
        "11": {"hostname": "heraNode700Snap3", "ant_loc": 2},
    }
    assert len(config_input_index_result) == len(input_index_dict)

    # check that we can also get the nodes & snap loc nums
    (
        config_input_index_result,
        node_list,
        snap_loc_list,
    ) = test_session.get_correlator_config_input_index(
        config_hash=status_result.config_hash, return_node_loc_num=True
    )
    assert len(config_input_index_result) == len(input_index_dict)
    # since the request doesn't specify a time, the rosetta mapping for "now" is used.
    for index, input_index in enumerate(config_input_index_result):
        assert node_list[index] == int(input_index.hostname.split("S")[0][8:])
        assert snap_loc_list[index] == int(input_index.hostname[-1])

    # check that using the time options works too
    (
        config_input_index_result2,
        time_list,
    ) = test_session.get_correlator_config_input_index(
        starttime=t1 - TimeDelta(3.0, format="sec"), return_node_loc_num=False
    )
    assert len(config_input_index_result2) == len(input_index_dict)
    assert len(time_list) == len(input_index_dict)
    for index, input_index in enumerate(config_input_index_result2):
        if rosetta_exists:
            assert node_list[index] == int(input_index.hostname.split("S")[0][8:])
            assert snap_loc_list[index] == int(input_index.hostname[-1])

    for corr_index, info in input_index_dict.items():
        config_input_index_result = test_session.get_correlator_config_input_index(
            config_hash=status_result.config_hash,
            correlator_index=int(corr_index),
        )
        config_input_index_expected = corr.CorrelatorConfigInputIndex(
            config_hash="testhash",
            correlator_index=int(corr_index),
            hostname=info["hostname"],
            antenna_index_position=info["ant_loc"],
        )
        assert len(config_input_index_result) == 1
        config_input_index_result = config_input_index_result[0]
        assert config_input_index_result.isclose(config_input_index_expected)

        # check that using the time options works too
        (
            config_input_index_result,
            time_list,
        ) = test_session.get_correlator_config_input_index(
            starttime=t1 - TimeDelta(3.0, format="sec"),
            correlator_index=int(corr_index),
        )
        assert len(config_input_index_result) == 1
        config_input_index_result = config_input_index_result[0]
        assert config_input_index_result.isclose(config_input_index_expected)

    config_phase_switch_result = test_session.get_correlator_config_phase_switch_index(
        config_hash=status_result.config_hash
    )
    phase_switch_dict = {
        "1": {"hostname": "heraNode700Snap0", "antpol_index": 0},
        "2": {"hostname": "heraNode700Snap0", "antpol_index": 1},
        "3": {"hostname": "heraNode700Snap0", "antpol_index": 2},
        "4": {"hostname": "heraNode700Snap0", "antpol_index": 3},
        "5": {"hostname": "heraNode700Snap0", "antpol_index": 4},
        "6": {"hostname": "heraNode700Snap0", "antpol_index": 5},
        "7": {"hostname": "heraNode700Snap1", "antpol_index": 0},
        "8": {"hostname": "heraNode700Snap1", "antpol_index": 1},
        "9": {"hostname": "heraNode700Snap1", "antpol_index": 2},
        "10": {"hostname": "heraNode700Snap1", "antpol_index": 3},
        "11": {"hostname": "heraNode700Snap1", "antpol_index": 4},
        "12": {"hostname": "heraNode700Snap1", "antpol_index": 5},
        "13": {"hostname": "heraNode700Snap2", "antpol_index": 0},
        "14": {"hostname": "heraNode700Snap2", "antpol_index": 1},
        "15": {"hostname": "heraNode700Snap2", "antpol_index": 2},
        "16": {"hostname": "heraNode700Snap2", "antpol_index": 3},
        "17": {"hostname": "heraNode700Snap2", "antpol_index": 4},
        "18": {"hostname": "heraNode700Snap2", "antpol_index": 5},
        "19": {"hostname": "heraNode700Snap3", "antpol_index": 0},
        "20": {"hostname": "heraNode700Snap3", "antpol_index": 1},
        "21": {"hostname": "heraNode700Snap3", "antpol_index": 2},
        "22": {"hostname": "heraNode700Snap3", "antpol_index": 3},
        "23": {"hostname": "heraNode700Snap3", "antpol_index": 4},
        "24": {"hostname": "heraNode700Snap3", "antpol_index": 5},
    }
    assert len(config_phase_switch_result) == len(phase_switch_dict)

    # check that we can also get the nodes & snap loc nums
    (
        config_phase_switch_result,
        node_list,
        snap_loc_list,
    ) = test_session.get_correlator_config_phase_switch_index(
        config_hash=status_result.config_hash, return_node_loc_num=True
    )
    assert len(config_phase_switch_result) == len(phase_switch_dict)
    # since the request doesn't specify a time, the rosetta mapping for "now" is used.
    for index, ps_index in enumerate(config_phase_switch_result):
        assert node_list[index] == int(ps_index.hostname.split("S")[0][8:])
        assert snap_loc_list[index] == int(ps_index.hostname[-1])

    # check that using the time options works too
    (
        config_phase_switch_result2,
        time_list,
    ) = test_session.get_correlator_config_phase_switch_index(
        starttime=t1 - TimeDelta(3.0, format="sec"), return_node_loc_num=False
    )
    assert len(config_phase_switch_result2) == len(phase_switch_dict)
    assert len(time_list) == len(phase_switch_dict)
    for index, ps_index in enumerate(config_phase_switch_result2):
        if rosetta_exists:
            assert node_list[index] == int(ps_index.hostname.split("S")[0][8:])
            assert snap_loc_list[index] == int(ps_index.hostname[-1])

    for index, result in enumerate(config_phase_switch_result):
        phase_switch_index = result.phase_switch_index
        this_dict = phase_switch_dict[str(phase_switch_index)]
        config_phase_switch_expected = corr.CorrelatorConfigPhaseSwitchIndex(
            config_hash="testhash",
            hostname=this_dict["hostname"],
            phase_switch_index=phase_switch_index,
            antpol_index_position=this_dict["antpol_index"],
        )
        assert result.isclose(config_phase_switch_expected)
        assert config_phase_switch_result2[index].isclose(config_phase_switch_expected)


def test_add_correlator_config_from_corrcm_match_prior(mcsession, corr_config_dict):
    test_session = mcsession
    # test behavior when matching config exists at an earlier time
    t1 = Time(1230372020, format="gps")
    t0 = t1 - TimeDelta(30, format="sec")
    config_hash = "testhash"
    config_filename = "correlator_config_" + str(int(floor(t1.gps))) + ".yaml"
    test_session.add_correlator_config_file(config_hash, config_filename)
    test_session.commit()
    test_session.add_correlator_config_status(t0, config_hash)
    test_session.commit()

    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=corr_config_dict, testing=True
    )

    status_expected = corr.CorrelatorConfigStatus(
        time=int(floor(t1.gps)), config_hash="testhash"
    )

    assert corr_config_list[0].isclose(status_expected)


def test_add_correlator_config_from_corrcm_duplicate(mcsession, corr_config_dict):
    test_session = mcsession
    # test behavior when duplicate config exists
    t1 = Time(1230372020, format="gps")
    config_hash = "testhash"
    config_filename = "correlator_config_" + str(int(floor(t1.gps))) + ".yaml"
    test_session.add_correlator_config_file(config_hash, config_filename)
    test_session.commit()
    test_session.add_correlator_config_status(t1, config_hash)
    test_session.commit()

    corr_config_list = test_session.add_correlator_config_from_corrcm(
        config_state_dict=corr_config_dict, testing=True
    )

    assert len(corr_config_list) == 0


def test_config_errors(mcsession):
    test_session = mcsession
    pytest.raises(
        ValueError, test_session.add_correlator_config_status, "foo", "testhash"
    )


@requires_redis
def test_add_correlator_config_from_corrcm_redis(mcsession):
    pytest.importorskip("hera_corr_cm")
    test_session = mcsession

    config_dict = corr._get_config(redishost=TEST_DEFAULT_REDIS_HOST)

    result = test_session.add_correlator_config_from_corrcm(
        testing=True, redishost=TEST_DEFAULT_REDIS_HOST
    )

    assert len(result) > 0
    if len(result) == 1:
        # should just be a status object because this file already exists
        assert result[0].__class__ == corr.CorrelatorConfigStatus
        assert result[0].time == int(Time(config_dict["time"], format="unix").gps)
    else:
        # first should be a file object, then a bunch of objects for the various parsed
        # config tables, then finally a status object.
        class_list = [obj.__class__ for obj in result]
        assert class_list[0] == corr.CorrelatorConfigFile
        assert class_list[-1] == corr.CorrelatorConfigStatus
        assert result[-1].time == int(Time(config_dict["time"], format="unix").gps)
        assert corr.CorrelatorConfigParams in class_list
        assert corr.CorrelatorConfigActiveSNAP in class_list
        assert corr.CorrelatorConfigInputIndex in class_list
        assert corr.CorrelatorConfigPhaseSwitchIndex in class_list


def test_add_correlator_software_versions(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()

    test_session.add_correlator_software_versions(t1, "hera_corr_f", "0.0.1-3c7fdaf6")

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t1.gps)), package="hera_corr_f", version="0.0.1-3c7fdaf6"
    )
    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_correlator_software_versions(t1, "hera_corr_cm", "0.0.1-11a573c9")

    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format="sec"), package="hera_corr_f"
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_software_versions(
        package="hera_corr_f"
    )
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t1.gps)), package="hera_corr_cm", version="0.0.1-11a573c9"
    )

    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format="sec"), package="hera_corr_cm"
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_software_versions(
        package="hera_corr_cm"
    )
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t1
    )
    assert len(result) == 2

    result_most_recent = test_session.get_correlator_software_versions()
    assert len(result) == 2

    result = test_session.get_correlator_software_versions(
        starttime=t1 + TimeDelta(200.0, format="sec")
    )
    assert result == []


def test_software_version_errors(mcsession):
    test_session = mcsession
    pytest.raises(
        ValueError,
        test_session.add_correlator_software_versions,
        "foo",
        "hera_corr_cm",
        "0.0.1-11a573c9",
    )


def test_add_snap_config_version(mcsession, feng_config, init_args):
    test_session = mcsession
    t1 = TEST_TIME1.copy()
    t2 = TEST_TIME2.copy()

    test_session.add_correlator_config_file("testhash", feng_config[0])
    test_session.commit()
    test_session.add_correlator_config_status(t1, "testhash")
    test_session.commit()

    test_session.add_snap_config_version(t1, "0.0.1-3c7fdaf6", init_args, "testhash")

    expected = corr.SNAPConfigVersion(
        init_time=int(floor(t1.gps)),
        version="0.0.1-3c7fdaf6",
        init_args=init_args,
        config_hash="testhash",
    )

    result = test_session.get_snap_config_version(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_correlator_config_file("testhash2", feng_config[0])
    test_session.commit()
    test_session.add_correlator_config_status(t2, "testhash2")
    test_session.commit()

    test_session.add_snap_config_version(t2, "0.0.1-11a573c9", init_args, "testhash2")

    expected = corr.SNAPConfigVersion(
        init_time=int(floor(t2.gps)),
        version="0.0.1-11a573c9",
        init_args=init_args,
        config_hash="testhash2",
    )

    result = test_session.get_snap_config_version(
        starttime=t2 - TimeDelta(3.0, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_config_version()
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_snap_config_version(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t2
    )
    assert len(result) == 2

    result = test_session.get_snap_config_version(
        starttime=t1 + TimeDelta(200.0, format="sec")
    )
    assert result == []


def test_snap_config_version_errors(mcsession, init_args):
    test_session = mcsession
    pytest.raises(
        ValueError,
        test_session.add_snap_config_version,
        "foo",
        "0.0.1-3c7fdaf6",
        init_args,
        "testhash",
    )


def test_add_corr_snap_versions_from_corrcm(mcsession, snapversion, init_args):
    test_session = mcsession
    # use testing to prevent call to hera_librarian to save new config file
    corr_snap_version_obj_list = test_session.add_corr_snap_versions_from_corrcm(
        corr_snap_version_dict=snapversion, testing=True
    )

    for obj in corr_snap_version_obj_list:
        test_session.add(obj)
        test_session.commit()

    t1 = Time(datetime.datetime(2019, 4, 2, 19, 7, 14), format="datetime")
    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t1.gps)),
        package="hera_corr_f:hera_snap_redis_monitor.py",
        version="0.0.1-3c7fdaf6",
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_software_versions(
        package="hera_corr_f:hera_snap_redis_monitor.py"
    )
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result_most_recent = test_session.get_correlator_software_versions()
    assert len(result_most_recent) == 3
    most_recent_packages = sorted(res.package for res in result_most_recent)
    expected_recent_packages = sorted(
        [
            "udpSender:hera_node_keep_alive.py",
            "udpSender:hera_node_cmd_check.py",
            "hera_corr_cm",
        ]
    )
    assert most_recent_packages == expected_recent_packages

    result = test_session.get_correlator_software_versions(
        starttime=t1 - TimeDelta(3.0, format="sec"),
        stoptime=t1 + TimeDelta(10.0, format="sec"),
    )
    assert len(result) == 5

    t2 = Time(datetime.datetime(2019, 3, 27, 8, 28, 25), format="datetime")
    result = test_session.get_snap_config_version(
        starttime=t2 - TimeDelta(3.0, format="sec")
    )

    expected = corr.SNAPConfigVersion(
        init_time=int(floor(t2.gps)),
        version="0.0.1-3c7fdaf6",
        init_args=init_args,
        config_hash="testhash",
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_config_version()
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    t3 = Time(datetime.datetime(2019, 2, 18, 5, 41, 29), format="datetime")
    result = test_session.get_correlator_config_status(
        starttime=t3 - TimeDelta(3.0, format="sec")
    )

    expected = corr.CorrelatorConfigStatus(
        time=int(floor(t3.gps)), config_hash="testhash"
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_correlator_config_status()
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    # test that a new hera_corr_cm timestamp with the same version doesn't make
    # a new row
    new_dict = copy.deepcopy(snapversion)
    new_dict["hera_corr_cm"]["timestamp"] = datetime.datetime(
        2019, 4, 2, 19, 8, 17, 644984
    )

    corr_snap_version_obj_list = test_session.add_corr_snap_versions_from_corrcm(
        corr_snap_version_dict=new_dict
    )

    t4 = Time(datetime.datetime(2019, 4, 2, 19, 7, 17), format="datetime")
    t5 = Time(datetime.datetime(2019, 4, 2, 19, 8, 17), format="datetime")

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t4.gps)), package="hera_corr_cm", version="0.0.1-11a573c9"
    )

    result = test_session.get_correlator_software_versions(
        starttime=t4 - TimeDelta(3.0, format="sec"),
        stoptime=t5 + TimeDelta(10.0, format="sec"),
        package="hera_corr_cm",
    )

    assert len(result) == 1
    assert result[0].isclose(expected)

    # test that a new hera_corr_cm timestamp with a new version makes a new row
    new_dict = copy.deepcopy(snapversion)
    new_dict["hera_corr_cm"]["timestamp"] = datetime.datetime(
        2019, 4, 2, 19, 8, 17, 644984
    )
    new_dict["hera_corr_cm"]["version"] = "0.0.1-b43b2b72"

    corr_snap_version_obj_list = test_session.add_corr_snap_versions_from_corrcm(
        corr_snap_version_dict=new_dict
    )

    expected = corr.CorrelatorSoftwareVersions(
        time=int(floor(t5.gps)), package="hera_corr_cm", version="0.0.1-b43b2b72"
    )

    result = test_session.get_correlator_software_versions(
        starttime=t4 - TimeDelta(3.0, format="sec"),
        stoptime=t5 + TimeDelta(10.0, format="sec"),
        package="hera_corr_cm",
    )

    assert len(result) == 2
    assert result[1].isclose(expected)


@requires_redis
def test_redis_add_corr_snap_versions_from_corrcm(mcsession):
    pytest.importorskip("hera_corr_cm")
    test_session = mcsession

    version_dict = corr._get_corr_versions(redishost=TEST_DEFAULT_REDIS_HOST)
    result = test_session.add_corr_snap_versions_from_corrcm(
        testing=True, redishost=TEST_DEFAULT_REDIS_HOST
    )

    assert len(result) >= 1
    for obj in result:
        if isinstance(obj, corr.CorrelatorSoftwareVersions):
            assert obj.version == version_dict[obj.package]["version"]
        elif isinstance(obj, corr.SNAPConfigVersion):
            assert obj.version == version_dict["snap"]["version"]


@onsite
def test_onsite_add_corr_snap_versions_from_corrcm(mcsession):
    # this has to be done onsite, not in CI because it needs to talk to the librarian
    # as well (to register the config file in the librarian)
    test_session = mcsession
    test_session.add_corr_obj(redishost=TEST_DEFAULT_REDIS_HOST)

    corr_versions_dict = corr._get_corr_versions(
        corr_cm=test_session.corr_obj, redishost=TEST_DEFAULT_REDIS_HOST
    )
    assert len(corr_versions_dict) >= 1

    test_results = test_session.add_corr_snap_versions_from_corrcm(
        redishost=TEST_DEFAULT_REDIS_HOST, testing=True
    )
    assert len(corr_versions_dict) >= 1

    assert len(test_results) >= len(corr_versions_dict)

    test_session.add_corr_snap_versions_from_corrcm(redishost=TEST_DEFAULT_REDIS_HOST)

    result = test_session.get_correlator_software_versions(
        package="hera_corr_cm", most_recent=True
    )
    assert len(result) == 1

    result = test_session.get_correlator_software_versions()
    assert len(result) >= 1

    result = test_session.get_snap_config_version()
    assert len(result) == 1


def test_add_snap_status(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()

    t_prog = Time("2016-01-05 20:00:00", scale="utc")
    test_session.add_snap_status(
        t1,
        "heraNode700Snap0",
        "SNPA000700",
        False,
        595687,
        57.984954833984375,
        595686,
        t_prog,
        True,
        True,
        True,
        True,
        "7.1",
        500.0,
    )

    expected = corr.SNAPStatus(
        time=int(floor(t1.gps)),
        hostname="heraNode700Snap0",
        serial_number="SNPA000700",
        node=700,
        snap_loc_num=0,
        psu_alert=False,
        pps_count=595687,
        fpga_temp=57.984954833984375,
        uptime_cycles=595686,
        last_programmed_time=int(floor(t_prog.gps)),
        is_programmed=True,
        adc_is_configured=True,
        is_initialized=True,
        dest_is_configured=True,
        version="7.1",
        sample_rate=500.0,
    )
    result = test_session.get_snap_status(starttime=t1 - TimeDelta(3.0, format="sec"))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    for channel_number in range(6):
        test_session.add_snap_input(t1, "heraNode700Snap0", channel_number, "adc")

    result = test_session.get_snap_input(starttime=t1 - TimeDelta(3.0, format="sec"))
    assert len(result) == 6

    snap_input_antpol = {
        0: {"antenna": 701, "pol": "n"},
        1: {"antenna": 701, "pol": "e"},
        2: {"antenna": 702, "pol": "n"},
        3: {"antenna": 702, "pol": "e"},
        4: {"antenna": None, "pol": None},
        5: {"antenna": None, "pol": None},
    }
    for snap_input_obj in result:
        channel_number = snap_input_obj.snap_channel_number
        expected_input = corr.SNAPInput(
            time=int(floor(t1.gps)),
            hostname="heraNode700Snap0",
            snap_channel_number=channel_number,
            antenna_number=snap_input_antpol[channel_number]["antenna"],
            antenna_feed_pol=snap_input_antpol[channel_number]["pol"],
            snap_input="adc",
        )
        assert snap_input_obj.isclose(expected_input)

    test_session.add_snap_status(
        t1,
        "heraNode701Snap3",
        "SNPD000703",
        True,
        595699,
        59.323028564453125,
        595699,
        t_prog,
        False,
        False,
        False,
        False,
        "7.1",
        500.0,
    )

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), nodeID=700
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status(hostname="heraNode700Snap0")
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    expected = corr.SNAPStatus(
        time=int(floor(t1.gps)),
        hostname="heraNode701Snap3",
        serial_number="SNPD000703",
        node=701,
        snap_loc_num=3,
        psu_alert=True,
        pps_count=595699,
        fpga_temp=59.323028564453125,
        uptime_cycles=595699,
        last_programmed_time=int(floor(t_prog.gps)),
        is_programmed=False,
        adc_is_configured=False,
        is_initialized=False,
        dest_is_configured=False,
        version="7.1",
        sample_rate=500.0,
    )

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), nodeID=701
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status(nodeID=701)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    for channel_number in range(6):
        test_session.add_snap_input(
            t1, "heraNode701Snap3", channel_number, f"noise-{channel_number}"
        )

    result = test_session.get_snap_input(
        starttime=t1 - TimeDelta(3.0, format="sec"), hostname="heraNode701Snap3"
    )
    assert len(result) == 6

    for snap_input_obj in result:
        channel_number = snap_input_obj.snap_channel_number
        expected_input = corr.SNAPInput(
            time=int(floor(t1.gps)),
            hostname="heraNode701Snap3",
            snap_channel_number=channel_number,
            antenna_number=None,
            antenna_feed_pol=None,
            snap_input=f"noise-{channel_number}",
        )
        assert snap_input_obj.isclose(expected_input)

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t1
    )
    assert len(result) == 2

    result_most_recent = test_session.get_snap_status()
    assert len(result) == 2

    result = test_session.get_snap_input()
    assert len(result) == 12

    result = test_session.get_snap_status(starttime=t1 + TimeDelta(200.0, format="sec"))
    assert result == []


def test_add_snap_status_from_corrcm(mcsession, snapstatus):
    test_session = mcsession
    test_session.add_snap_status_from_corrcm(snap_status_dict=snapstatus)

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format="datetime")
    t_prog = Time(datetime.datetime(2016, 1, 10, 23, 16, 3), format="datetime")
    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), hostname="heraNode700Snap0"
    )

    expected = corr.SNAPStatus(
        time=int(floor(t1.gps)),
        hostname="heraNode700Snap0",
        serial_number="SNPA000700",
        node=700,
        snap_loc_num=0,
        psu_alert=True,
        pps_count=595687,
        fpga_temp=57.984954833984375,
        uptime_cycles=595686,
        last_programmed_time=int(floor(t_prog.gps)),
        is_programmed=True,
        adc_is_configured=True,
        is_initialized=True,
        dest_is_configured=True,
        version="7.1",
        sample_rate=500.0,
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status(nodeID=700)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result_input = test_session.get_snap_input(
        starttime=t1 - TimeDelta(3.0, format="sec"), hostname="heraNode700Snap0"
    )

    snap_input_antpol = {
        0: {"antenna": 701, "pol": "n"},
        1: {"antenna": 701, "pol": "e"},
        2: {"antenna": 702, "pol": "n"},
        3: {"antenna": 702, "pol": "e"},
        4: {"antenna": None, "pol": None},
        5: {"antenna": None, "pol": None},
    }
    for snap_input_obj in result_input:
        channel_number = snap_input_obj.snap_channel_number
        expected_input = corr.SNAPInput(
            time=int(floor(t1.gps)),
            hostname="heraNode700Snap0",
            snap_channel_number=channel_number,
            antenna_number=snap_input_antpol[channel_number]["antenna"],
            antenna_feed_pol=snap_input_antpol[channel_number]["pol"],
            snap_input="adc",
        )
        assert snap_input_obj.isclose(expected_input)

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), nodeID=701
    )

    expected = corr.SNAPStatus(
        time=int(floor(t1.gps)),
        hostname="heraNode701Snap3",
        serial_number="SNPD000703",
        node=701,
        snap_loc_num=3,
        psu_alert=False,
        pps_count=595699,
        fpga_temp=59.323028564453125,
        uptime_cycles=595699,
        last_programmed_time=int(floor(t_prog.gps)),
        is_programmed=False,
        adc_is_configured=False,
        is_initialized=False,
        dest_is_configured=False,
        version="7.1",
        sample_rate=500.0,
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_input = test_session.get_snap_input(
        starttime=t1 - TimeDelta(3.0, format="sec"), hostname="heraNode701Snap3"
    )
    assert len(result_input) == 6

    for snap_input_obj in result_input:
        channel_number = snap_input_obj.snap_channel_number
        expected_input = corr.SNAPInput(
            time=int(floor(t1.gps)),
            hostname="heraNode701Snap3",
            snap_channel_number=channel_number,
            antenna_number=None,
            antenna_feed_pol=None,
            snap_input=f"noise-{channel_number + 1}",
        )
        assert snap_input_obj.isclose(expected_input)

    result_most_recent = test_session.get_snap_status()
    assert len(result_most_recent) == 2

    result_input = test_session.get_snap_input()
    assert len(result_input) == 12


def test_add_snap_status_from_corrcm_with_nones(mcsession, snapstatus_none):
    test_session = mcsession
    snap_status_obj_list = test_session.add_snap_status_from_corrcm(
        snap_status_dict=snapstatus_none, testing=True
    )
    for obj in snap_status_obj_list:
        test_session.add(obj)
        test_session.commit()

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format="datetime")
    result = test_session.get_snap_status(starttime=t1 - TimeDelta(3.0, format="sec"))

    expected = corr.SNAPStatus(
        time=int(floor(t1.gps)),
        hostname="heraNode700Snap0",
        serial_number=None,
        node=None,
        snap_loc_num=None,
        psu_alert=None,
        pps_count=None,
        fpga_temp=None,
        uptime_cycles=None,
        last_programmed_time=None,
        is_programmed=None,
        adc_is_configured=None,
        is_initialized=None,
        dest_is_configured=None,
        version=None,
        sample_rate=None,
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


def test_snap_status_errors(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()

    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        test_session.add_snap_status(
            "foo",
            "heraNode700Snap0",
            "SNPA000700",
            False,
            595687,
            57.984954833984375,
            595686,
            t1,
            True,
            True,
            True,
            True,
            "7.1",
            500.0,
        )

    with pytest.raises(
        ValueError, match="last_programmed_time must be an astropy Time object"
    ):
        test_session.add_snap_status(
            t1,
            "heraNode700Snap0",
            "SNPA000700",
            False,
            595687,
            57.984954833984375,
            595686,
            "foo",
            True,
            True,
            True,
            True,
            "7.1",
            500.0,
        )


def test_snap_input_errors(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()

    t_prog = Time("2016-01-05 20:00:00", scale="utc")
    test_session.add_snap_status(
        t1,
        "heraNode700Snap0",
        "SNPA000700",
        False,
        595687,
        57.984954833984375,
        595686,
        t_prog,
        True,
        True,
        True,
        True,
        "7.1",
        500.0,
    )

    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        test_session.add_snap_input("foo", "heraNode700Snap0", 0, "adc")

    with pytest.raises(ValueError, match="antenna_feed_pol must be 'e' or 'n'."):
        corr.SNAPInput.create(t1, "heraNode700Snap0", 0, 11, "foo", "adc")


def test_add_snap_feng_init_status(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()
    t2 = TEST_TIME2.copy()

    test_session.add_snap_feng_init_status(t1, "heraNode700Snap0", "working")

    expected = corr.SNAPFengInitStatus(
        time=int(floor(t1.gps)), hostname="heraNode700Snap0", status="working"
    )
    result = test_session.get_snap_feng_init_status(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_snap_feng_init_status(t2, "heraNode701Snap3", "unconfig")

    expected2 = corr.SNAPFengInitStatus(
        time=int(floor(t2.gps)), hostname="heraNode701Snap3", status="unconfig"
    )

    result = test_session.get_snap_feng_init_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), hostname="heraNode701Snap3"
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected2)

    result = test_session.get_snap_feng_init_status()
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected2)


def test_add_snap_feng_init_status_errors(mcsession):
    test_session = mcsession

    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        test_session.add_snap_feng_init_status("foo", "heraNode700Snap0", "working")


@pytest.mark.parametrize(
    "key,value",
    [
        (None, None),
        ("maxout", ""),
        ("special", "heraNode9Snap3"),
        ("foo", "bar"),
        ("log_time_stop", "Not found"),
        ("log_time_stop", None),
    ],
)
def test_get_snap_feng_init_status_from_redis(snap_feng_init_status, key, value):
    input_dict = snap_feng_init_status.copy()

    expected_snap_state = {
        "heraNode9Snap3": "maxout",
        "heraNode19Snap3": "unconfig",
        "heraNode13Snap3": "unconfig",
        "heraNode18Snap1": "unconfig",
        "heraNode18Snap2": "unconfig",
        "heraNode12Snap2": "working",
        "heraNode12Snap3": "working",
        "heraNode12Snap0": "working",
        "heraNode12Snap1": "working",
    }
    expected_time = Time(input_dict["log_time_stop"])

    if key is not None:
        input_dict[key] = value
        if key == "maxout" and value == "":
            expected_snap_state.pop("heraNode9Snap3")
        elif key == "special":
            expected_snap_state[value] = key
        elif key == "log_time_stop":
            expected_snap_state = {}
            expected_time = None

    if key == "foo":
        exp_warning = UserWarning
        warn_msg = (
            f"Unexpected key in redis `snap_log` key: {key}, some info may be lost"
        )
    else:
        exp_warning = None
        warn_msg = ""

    with uvtest.check_warnings(exp_warning, match=warn_msg):
        log_time, snap_state = corr._get_snap_feng_init_status_from_redis(
            snap_config_dict=input_dict
        )
    assert log_time == expected_time
    assert expected_snap_state == snap_state


@requires_redis
def test_add_snap_feng_init_status_from_redis(mcsession):
    test_session = mcsession

    # get the dict from redis
    log_time, snap_feng_status = corr._get_snap_feng_init_status_from_redis()
    assert len(snap_feng_status) > 1

    # get the objects, check same number as dict
    snap_objs = test_session.add_snap_feng_init_status_from_redis(testing=True)
    assert len(snap_objs) == len(snap_feng_status)
    assert snap_objs[0].time == int(floor(log_time.gps))
    input_hostnames = [obj.hostname for obj in snap_objs]

    # actually put them in the db, get them back and check they're as expected
    test_session.add_snap_feng_init_status_from_redis()
    db_snap_objs = test_session.get_snap_feng_init_status(most_recent=True)

    assert len(db_snap_objs) == len(snap_objs)
    db_hostnames = [obj.hostname for obj in db_snap_objs]
    assert sorted(input_hostnames) == sorted(db_hostnames)

    for obj in db_snap_objs:
        input_ind = input_hostnames.index(obj.hostname)
        assert obj.isclose(snap_objs[input_ind])


def test_get_node_snap_from_serial_nodossier(mcsession):
    with pytest.warns(
        UserWarning,
        match="No active connections returned for snap serial foo. "
        "Setting node and snap location numbers to None",
    ):
        node, snap_loc_num = mcsession._get_node_snap_from_serial("foo")
    assert node is None
    assert snap_loc_num is None


def test_get_node_snap_from_serial_multiple_revs(mcsession):
    """Test multiple snap location numbers."""
    part = cm_partconnect.Parts()
    part.hpn = "SNPD000703"
    part.hpn_rev = "B"
    part.hptype = "snap"
    part.manufacture_number = "D000703"
    part.start_gpstime = 1230375618
    mcsession.add(part)
    mcsession.commit()
    connection = cm_partconnect.Connections()
    connection.upstream_part = "SNPD000703"
    connection.up_part_rev = "B"
    connection.downstream_part = "N701"
    connection.down_part_rev = "A"
    connection.upstream_output_port = "rack"
    connection.downstream_input_port = "loc2"
    connection.start_gpstime = 1230375618
    mcsession.add(connection)
    mcsession.commit()
    with pytest.warns(
        UserWarning,
        match="There is more that one active revision for snap serial SNPD000703. "
        "Setting node and snap location numbers to None",
    ):
        node, snap_loc_num = mcsession._get_node_snap_from_serial("SNPD000703")
    assert node is None
    assert snap_loc_num is None


def test_get_node_snap_from_serial_multiple_times_diffloc(mcsession):
    """Test multiple times with change in location."""
    # stop earlier connection
    conn_to_stop = [["SNPD000703", "A", "N701", "A", "rack", "loc3", 1230375618]]
    cm_partconnect.stop_connections(
        mcsession, conn_to_stop, Time(1230375700, format="gps")
    )

    connection = cm_partconnect.Connections()
    connection.upstream_part = "SNPD000703"
    connection.up_part_rev = "A"
    connection.downstream_part = "N701"
    connection.down_part_rev = "A"
    connection.upstream_output_port = "rack"
    connection.downstream_input_port = "loc2"
    connection.start_gpstime = 1230375718
    mcsession.add(connection)
    mcsession.commit()
    node, snap_loc_num = checkWarnings(
        mcsession._get_node_snap_from_serial, ["SNPD000703"], nwarnings=0
    )
    assert node == 701
    assert snap_loc_num == 2


def test_get_snap_hostname_from_serial(mcsession, snapstatus):
    test_session = mcsession
    test_session.add_snap_status_from_corrcm(snap_status_dict=snapstatus)

    hostname = test_session.get_snap_hostname_from_serial("SNPA000700")
    assert hostname == "heraNode700Snap0"

    # asking for a hostname from before the part_rosetta was active should give None
    hostname = test_session.get_snap_hostname_from_serial(
        "SNPA000700", at_date=Time(1512770942, format="unix")
    )
    assert hostname is None

    hostname = test_session.get_snap_hostname_from_serial("blah")
    assert hostname is None


@requires_redis
@pytest.mark.filterwarnings("ignore:No active connections returned for snap")
def test_redis_add_snap_status_from_corrcm(mcsession):
    pytest.importorskip("hera_corr_cm")
    test_session = mcsession
    test_session.add_corr_obj(redishost=TEST_DEFAULT_REDIS_HOST)

    # get the snap status dict from the correlator redis
    snap_status_dict = corr._get_snap_status(
        corr_cm=test_session.corr_obj, redishost=TEST_DEFAULT_REDIS_HOST
    )
    assert len(snap_status_dict) >= 1

    # sometimes we get some statuses that have a timestamp that is a None, those are
    # skipped when updloaded into the DB, which will make the lengths different.
    # Count them here so we can test for the same lengths.
    count_bad_timestamp = 0
    for _, status in snap_status_dict.items():
        if status["timestamp"] is None or status["timestamp"] == "None":
            count_bad_timestamp += 1
    n_good_statuses = len(snap_status_dict) - count_bad_timestamp

    # get result using just the test db, check it matches snap_status_dict
    result_test2 = test_session.add_snap_status_from_corrcm(
        testing=True, redishost=TEST_DEFAULT_REDIS_HOST
    )
    snap_status_list = []
    snap_input_list = []
    for obj in result_test2:
        if isinstance(obj, corr.SNAPStatus):
            snap_status_list.append(obj)
        else:
            snap_input_list.append(obj)
    assert n_good_statuses == len(snap_status_list)
    assert len(snap_input_list) == 6 * len(snap_status_list)

    # use the real (not test) database to get the node & snap location number
    # check the length is the same
    real_db = mc.connect_to_mc_db(None)
    real_session = real_db.sessionmaker()

    result_test3 = test_session.add_snap_status_from_corrcm(
        cm_session=real_session, testing=True, redishost=TEST_DEFAULT_REDIS_HOST
    )
    assert len(result_test3) == len(result_test2)

    # actually add them to the db and get most recent, check there's at least one
    test_session.add_snap_status_from_corrcm(
        cm_session=real_session, redishost=TEST_DEFAULT_REDIS_HOST
    )
    result = test_session.get_snap_status(most_recent=True)

    assert len(result) >= 1


@requires_redis
@requires_default_redis
@pytest.mark.filterwarnings("ignore:No active connections returned for snap")
def test_site_add_snap_status_from_corrcm_default_redishost(mcsession):
    test_session = mcsession

    # get the snap status dict from the correlator redis
    snap_status_dict = corr._get_snap_status()
    assert len(snap_status_dict) >= 1

    # sometimes we get some statuses that have a timestamp that is a None, those are
    # skipped when updloaded into the DB, which will make the lengths different.
    # Count them here so we can test for the same lengths.
    count_bad_timestamp = 0
    for _, status in snap_status_dict.items():
        if status["timestamp"] is None or status["timestamp"] == "None":
            count_bad_timestamp += 1
    n_good_statuses = len(snap_status_dict) - count_bad_timestamp

    # get result using just the test db, check it matches snap_status_dict
    result_test2 = test_session.add_snap_status_from_corrcm(testing=True)
    snap_status_list = []
    snap_input_list = []
    for obj in result_test2:
        if isinstance(obj, corr.SNAPStatus):
            snap_status_list.append(obj)
        else:
            snap_input_list.append(obj)
    assert n_good_statuses == len(snap_status_list)
    assert len(snap_input_list) == 6 * len(snap_status_list)

    # use the real (not test) database to get the node & snap location number
    # check the length is the same
    real_db = mc.connect_to_mc_db(None)
    real_session = real_db.sessionmaker()

    result_test3 = test_session.add_snap_status_from_corrcm(
        cm_session=real_session, testing=True
    )
    assert len(result_test3) == len(result_test2)

    # actually add them to the db and get most recent, check there's at least one
    test_session.add_snap_status_from_corrcm(cm_session=real_session)
    result = test_session.get_snap_status(most_recent=True)

    assert len(result) >= 1


def test_add_antenna_status(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()
    t2 = TEST_TIME2.copy()

    eq_coeffs = (np.zeros((5)) + 56.921875).tolist()
    histogram = [0, 3, 6, 10, 12, 8, 4, 0]
    pam_id_list = [112, 217, 32, 59, 1, 0, 0, 14]
    pam_id = ":".join([str(i) for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ":".join([str(i) for i in fem_id_list])
    test_session.add_antenna_status(
        t1,
        4,
        "e",
        "heraNode700Snap0",
        3,
        -0.5308380126953125,
        3.0134560488579285,
        9.080917358398438,
        0,
        -13.349140985640002,
        10.248,
        0.6541,
        pam_id,
        6.496,
        0.5627000000000001,
        fem_id,
        "antenna",
        True,
        1.3621702512711602,
        30.762719534238915,
        26.327341308593752,
        False,
        eq_coeffs,
        histogram,
    )

    eq_coeffs_string = "[56.921875,56.921875,56.921875,56.921875,56.921875]"
    histogram_string = "[0,3,6,10,12,8,4,0]"
    expected = corr.AntennaStatus(
        time=int(floor(t1.gps)),
        antenna_number=4,
        antenna_feed_pol="e",
        snap_hostname="heraNode700Snap0",
        snap_channel_number=3,
        adc_mean=-0.5308380126953125,
        adc_rms=3.0134560488579285,
        adc_power=9.080917358398438,
        pam_atten=0,
        pam_power=-13.349140985640002,
        pam_voltage=10.248,
        pam_current=0.6541,
        pam_id=pam_id,
        fem_voltage=6.496,
        fem_current=0.5627000000000001,
        fem_id=fem_id,
        fem_switch="antenna",
        fem_lna_power=True,
        fem_imu_theta=1.3621702512711602,
        fem_imu_phi=30.762719534238915,
        fem_temp=26.327341308593752,
        fft_overflow=False,
        eq_coeffs=eq_coeffs_string,
        histogram=histogram_string,
    )

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    eq_coeffs = (np.zeros((5)) + 73.46875).tolist()
    histogram = [0, 3, 6, 10, 12, 8, 4, 0]
    pam_id_list = [112, 84, 143, 59, 1, 0, 0, 242]
    pam_id = ":".join([str(i) for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ":".join([str(i) for i in fem_id_list])
    test_session.add_antenna_status(
        t2,
        31,
        "n",
        "heraNode4Snap3",
        7,
        -0.4805450439453125,
        16.495319974304454,
        272.0955810546875,
        0,
        -32.03119784856,
        10.268,
        0.6695000000000001,
        pam_id,
        None,
        None,
        fem_id,
        "noise",
        False,
        1.3621702512711602,
        30.762719534238915,
        27.828854980468755,
        True,
        eq_coeffs,
        histogram,
    )

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), antenna_number=4
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_antenna_status(antenna_number=4)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    eq_coeffs_string = "[73.46875,73.46875,73.46875,73.46875,73.46875]"
    histogram_string = "[0,3,6,10,12,8,4,0]"
    expected = corr.AntennaStatus(
        time=int(floor(t2.gps)),
        antenna_number=31,
        antenna_feed_pol="n",
        snap_hostname="heraNode4Snap3",
        snap_channel_number=7,
        adc_mean=-0.4805450439453125,
        adc_rms=16.495319974304454,
        adc_power=272.0955810546875,
        pam_atten=0,
        pam_power=-32.03119784856,
        pam_voltage=10.268,
        pam_current=0.6695000000000001,
        pam_id=pam_id,
        fem_voltage=None,
        fem_current=None,
        fem_id=fem_id,
        fem_switch="noise",
        fem_lna_power=False,
        fem_imu_theta=1.3621702512711602,
        fem_imu_phi=30.762719534238915,
        fem_temp=27.828854980468755,
        fft_overflow=True,
        eq_coeffs=eq_coeffs_string,
        histogram=histogram_string,
    )

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), antenna_number=31
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_antenna_status(antenna_number=31)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t1
    )
    assert len(result) == 1

    result_most_recent = test_session.get_antenna_status()
    assert len(result) == 1

    result = test_session.get_antenna_status(
        starttime=t1 + TimeDelta(200.0, format="sec")
    )
    assert result == []


def test_edge_pam_fem_id():
    test_id = "UNKNOWN"
    assert corr._pam_fem_id_to_string(test_id) == test_id
    test_id = '"UNKNOWN"'
    assert corr._pam_fem_id_to_string(test_id) == test_id


def test_add_antenna_status_from_corrcm(mcsession, antstatus):
    test_session = mcsession
    ant_status_obj_list = test_session.add_antenna_status_from_corrcm(
        ant_status_dict=antstatus, testing=True
    )

    for obj in ant_status_obj_list:
        test_session.add(obj)

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format="datetime")
    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), antenna_number=4
    )

    eq_coeffs_str = [str(val) for val in (np.zeros((1024)) + 56.921875).tolist()]
    eq_coeffs_string = "[" + ",".join(eq_coeffs_str) + "]"

    histogram_str = [str(val) for val in (np.zeros((256)) + 10).tolist()]
    histogram_string = "[" + ",".join(histogram_str) + "]"
    pam_id_list = [112, 217, 32, 59, 1, 0, 0, 14]
    pam_id = ":".join([str(i) for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ":".join([str(i) for i in fem_id_list])
    expected = corr.AntennaStatus(
        time=int(floor(t1.gps)),
        antenna_number=4,
        antenna_feed_pol="e",
        snap_hostname="heraNode700Snap0",
        snap_channel_number=3,
        adc_mean=-0.5308380126953125,
        adc_rms=3.0134560488579285,
        adc_power=9.080917358398438,
        pam_atten=0,
        pam_power=-13.349140985640002,
        pam_voltage=10.248,
        pam_current=0.6541,
        pam_id=pam_id,
        fem_voltage=6.496,
        fem_current=0.5627000000000001,
        fem_id=fem_id,
        fem_switch="antenna",
        fem_lna_power=True,
        fem_imu_theta=1.3621702512711602,
        fem_imu_phi=30.762719534238915,
        fem_temp=26.327341308593752,
        fft_overflow=False,
        eq_coeffs=eq_coeffs_string,
        histogram=histogram_string,
    )

    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_antenna_status(antenna_number=4)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), antenna_number=31
    )

    eq_coeffs_str = [str(val) for val in (np.zeros((1024)) + 73.46875).tolist()]
    eq_coeffs_string = "[" + ",".join(eq_coeffs_str) + "]"
    histogram_str = [str(val) for val in (np.zeros((256)) + 12).tolist()]
    histogram_string = "[" + ",".join(histogram_str) + "]"
    pam_id_list = [112, 84, 143, 59, 1, 0, 0, 242]
    pam_id = ":".join([str(i) for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ":".join([str(i) for i in fem_id_list])
    expected = corr.AntennaStatus(
        time=int(floor(t1.gps)),
        antenna_number=31,
        antenna_feed_pol="n",
        snap_hostname="heraNode4Snap3",
        snap_channel_number=7,
        adc_mean=-0.4805450439453125,
        adc_rms=16.495319974304454,
        adc_power=272.0955810546875,
        pam_atten=0,
        pam_power=-32.03119784856,
        pam_voltage=10.268,
        pam_current=0.6695000000000001,
        pam_id=pam_id,
        fem_voltage=None,
        fem_current=None,
        fem_id=fem_id,
        fem_switch="noise",
        fem_lna_power=False,
        fem_imu_theta=1.3621702512711602,
        fem_imu_phi=30.762719534238915,
        fem_temp=27.828854980468755,
        fft_overflow=True,
        eq_coeffs=eq_coeffs_string,
        histogram=histogram_string,
    )

    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_antenna_status()
    assert len(result_most_recent) == 2


def test_add_antenna_status_from_corrcm_with_nones(mcsession, antstatus_none):
    test_session = mcsession
    checkWarnings(
        test_session.add_antenna_status_from_corrcm,
        func_kwargs={"ant_status_dict": antstatus_none},
        message="fem_switch value is Unknown mode",
    )

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format="datetime")
    result = test_session.get_antenna_status(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(result) == 2

    expected = corr.AntennaStatus(
        time=int(floor(t1.gps)),
        antenna_number=4,
        antenna_feed_pol="e",
        snap_hostname=None,
        snap_channel_number=None,
        adc_mean=None,
        adc_rms=None,
        adc_power=None,
        pam_atten=None,
        pam_power=None,
        pam_voltage=None,
        pam_current=None,
        pam_id=None,
        fem_voltage=None,
        fem_current=None,
        fem_id=None,
        fem_switch=None,
        fem_lna_power=None,
        fem_imu_theta=None,
        fem_imu_phi=None,
        fem_temp=None,
        fft_overflow=None,
        eq_coeffs=None,
        histogram=None,
    )

    result = test_session.get_antenna_status(antenna_number=4)
    result = result[0]
    assert result.isclose(expected)

    expected = corr.AntennaStatus(
        time=int(floor(t1.gps)),
        antenna_number=31,
        antenna_feed_pol="n",
        snap_hostname=None,
        snap_channel_number=None,
        adc_mean=None,
        adc_rms=None,
        adc_power=None,
        pam_atten=None,
        pam_power=None,
        pam_voltage=None,
        pam_current=None,
        pam_id=None,
        fem_voltage=None,
        fem_current=None,
        fem_id=None,
        fem_switch=None,
        fem_lna_power=None,
        fem_imu_theta=None,
        fem_imu_phi=None,
        fem_temp=None,
        fft_overflow=None,
        eq_coeffs=None,
        histogram=None,
    )

    result = test_session.get_antenna_status(antenna_number=31)
    result = result[0]
    assert result.isclose(expected)


def test_antenna_status_errors(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()

    eq_coeffs = (np.zeros((5)) + 56.921875).tolist()
    histogram = [0, 3, 6, 10, 12, 8, 4, 0]
    pam_id_list = [112, 217, 32, 59, 1, 0, 0, 14]
    pam_id = ":".join([str(i) for i in pam_id_list])
    fem_id_list = [0, 168, 19, 212, 51, 51, 255, 255]
    fem_id = ":".join([str(i) for i in fem_id_list])
    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        test_session.add_antenna_status(
            "foo",
            4,
            "e",
            "heraNode700Snap0",
            3,
            -0.5308380126953125,
            3.0134560488579285,
            9.080917358398438,
            0,
            -13.349140985640002,
            10.248,
            0.6541,
            pam_id,
            6.496,
            0.5627000000000001,
            fem_id,
            "antenna",
            True,
            1.3621702512711602,
            30.762719534238915,
            26.327341308593752,
            False,
            eq_coeffs,
            histogram,
        )

    with pytest.raises(
        ValueError, match='fem_switch must be "antenna", "load", "noise"'
    ):
        test_session.add_antenna_status(
            t1,
            4,
            "e",
            "heraNode700Snap0",
            3,
            -0.5308380126953125,
            3.0134560488579285,
            9.080917358398438,
            0,
            -13.349140985640002,
            10.248,
            0.6541,
            pam_id,
            6.496,
            0.5627000000000001,
            fem_id,
            "foo",
            True,
            1.3621702512711602,
            30.762719534238915,
            26.327341308593752,
            False,
            eq_coeffs,
            histogram,
        )

    with pytest.raises(ValueError, match='antenna_feed_pol must be "e" or "n".'):
        test_session.add_antenna_status(
            t1,
            4,
            "x",
            "heraNode700Snap0",
            3,
            -0.5308380126953125,
            3.0134560488579285,
            9.080917358398438,
            0,
            -13.349140985640002,
            10.248,
            0.6541,
            pam_id,
            6.496,
            0.5627000000000001,
            fem_id,
            "load",
            True,
            1.3621702512711602,
            30.762719534238915,
            26.327341308593752,
            False,
            eq_coeffs,
            histogram,
        )


@requires_redis
@pytest.mark.filterwarnings("ignore:fem_switch value is null")
@pytest.mark.filterwarnings("ignore:fem_switch value is failed")
def test_redis_add_antenna_status_from_corrcm(mcsession):
    pytest.importorskip("hera_corr_cm")
    test_session = mcsession

    result_test1 = corr._get_ant_status(redishost=TEST_DEFAULT_REDIS_HOST)
    result_test2 = corr.create_antenna_status(redishost=TEST_DEFAULT_REDIS_HOST)

    assert len(result_test1) > 0
    assert len(result_test1) == len(result_test2)

    result_test3 = test_session.add_antenna_status_from_corrcm(
        redishost=TEST_DEFAULT_REDIS_HOST, testing=True
    )

    assert len(result_test3) == len(result_test2)

    test_session.add_antenna_status_from_corrcm(redishost=TEST_DEFAULT_REDIS_HOST)
    result = test_session.get_antenna_status(most_recent=True)

    assert len(result) >= 1


def test_pam_fem_id_to_string_list():
    idno = ["fem0", "fem1"]
    assert corr._pam_fem_id_to_string(idno) == "fem0:fem1"

    return
