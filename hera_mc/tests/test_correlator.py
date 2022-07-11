# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.correlator`."""
import os
import copy
import datetime
import hashlib
from math import floor
import re

import pytest
import yaml
import numpy as np
from astropy.time import Time, TimeDelta

from hera_mc import mc, cm_partconnect
import hera_mc.correlator as corr
from hera_mc.data import DATA_PATH
from ..tests import (
    onsite,
    checkWarnings,
    requires_redis,
    requires_default_redis,
    TEST_DEFAULT_REDIS_HOST,
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
            "pmb_alert": False,
            "pps_count": 595687,
            "serial": "SNPA000700",
            "temp": 57.984954833984375,
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
            "uptime": 595686,
        },
        "heraNode701Snap3": {
            "last_programmed": datetime.datetime(2016, 1, 10, 23, 16, 3),
            "pmb_alert": False,
            "pps_count": 595699,
            "serial": "SNPD000703",
            "temp": 59.323028564453125,
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            "uptime": 595699,
        },
    }


@pytest.fixture(scope="module")
def snapstatus_none():
    return {
        "heraNode700Snap0": {
            "last_programmed": "None",
            "pmb_alert": "None",
            "pps_count": "None",
            "serial": "None",
            "temp": "None",
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
            "uptime": "None",
        },
        "heraNode701Snap3": {
            "last_programmed": datetime.datetime(2016, 1, 5, 20, 44, 52, 741137),
            "pmb_alert": False,
            "pps_count": 595699,
            "serial": "SNPD000703",
            "temp": 59.323028564453125,
            "timestamp": "None",
            "uptime": 595699,
        },
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
            "f_host": "None",
            "host_ant_id": "None",
            "adc_mean": "None",
            "adc_rms": "None",
            "adc_power": "None",
            "pam_atten": "None",
            "pam_power": "None",
            "pam_voltage": "None",
            "pam_current": "None",
            "pam_id": "None",
            "fem_voltage": "None",
            "fem_current": "None",
            "fem_id": "None",
            "fem_switch": "None",
            "fem_lna_power": "None",
            "fem_imu_theta": "None",
            "fem_imu_phi": "None",
            "fem_temp": "None",
            "fft_of": "None",
            "eq_coeffs": "None",
            "histogram": "None",
        },
        "31:n": {
            "timestamp": datetime.datetime(2016, 1, 5, 20, 44, 52, 739322),
            "f_host": "None",
            "host_ant_id": "None",
            "adc_mean": "None",
            "adc_rms": "None",
            "adc_power": "None",
            "pam_atten": "None",
            "pam_power": "None",
            "pam_voltage": "None",
            "pam_current": "None",
            "pam_id": "None",
            "fem_voltage": float("nan"),
            "fem_current": float("nan"),
            "fem_id": "None",
            "fem_switch": "Unknown mode",
            "fem_lna_power": "None",
            "fem_imu_theta": "None",
            "fem_imu_phi": "None",
            "fem_temp": "None",
            "fft_of": "None",
            "eq_coeffs": "None",
            "histogram": "None",
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

    mcsession.add_correlator_component_event_time("f_engine_sync", t1)

    comp_event_expected = corr.CorrelatorComponentEventTime(
        component_event="f_engine_sync", time=t1.gps
    )
    comp_event_result = mcsession.get_correlator_component_event_time(
        starttime=t1 - TimeDelta(3.0, format="sec")
    )
    assert len(comp_event_result) == 1
    comp_event_result = comp_event_result[0]
    assert comp_event_result.isclose(comp_event_expected)

    mcsession.add_correlator_component_event_time("catcher_start", t2)
    comp_event_expected2 = corr.CorrelatorComponentEventTime(
        component_event="catcher_start", time=t2.gps
    )

    comp_event_result = mcsession.get_correlator_component_event_time(
        component_event="f_engine_sync"
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
            {b"state": b"True", b"time": str(int(TEST_TIME1.unix)).encode("utf-8")},
            "catcher_start",
            TEST_TIME1,
        ),
        (
            {b"state": b"False", b"time": str(int(TEST_TIME1.unix)).encode("utf-8")},
            "catcher_stop",
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
    expdict["f_engine_sync"] = corr._get_f_engine_sync_time_from_redis()
    if event is not None:
        expdict[event] = time

    outdict = corr._get_correlator_component_event_times_from_redis(
        taking_data_dict=input_dict
    )

    assert outdict == expdict


@requires_redis
def test_add_correlator_component_event_time_from_redis(mcsession):
    comp_event_list = mcsession.add_correlator_component_event_time_from_redis(
        redishost=TEST_DEFAULT_REDIS_HOST, testing=True
    )
    assert len(comp_event_list) >= 1
    assert len(comp_event_list) <= 2

    event_types = []
    for comp_event_obj in comp_event_list:
        event_types.append(comp_event_obj.component_event)

    assert "f_engine_sync" in event_types
    if len(comp_event_list) == 2:
        assert "catcher_start" in event_types or "catcher_stop" in event_types

    mcsession.add_correlator_component_event_time_from_redis(
        redishost=TEST_DEFAULT_REDIS_HOST
    )

    # get most recent
    comp_event_result = mcsession.get_correlator_component_event_time(
        component_event="f_engine_sync"
    )
    assert len(comp_event_result) == 1

    f_engine_index = event_types.index("f_engine_sync")
    assert comp_event_result[0].isclose(comp_event_list[f_engine_index])

    if len(comp_event_list) == 2:
        if "catcher_start" in event_types:
            catcher_index = event_types.index("catcher_start")
            catcher_event = "catcher_start"
        else:
            catcher_index = event_types.index("catcher_stop")
            catcher_event = "catcher_stop"

        comp_event_result = mcsession.get_correlator_component_event_time(
            component_event=catcher_event
        )
        assert len(comp_event_result) == 1
        assert comp_event_result[0].isclose(comp_event_list[catcher_index])


def test_add_correlator_component_event_time_errors(mcsession):
    with pytest.raises(ValueError, match="time must be an astropy Time object"):
        mcsession.add_correlator_component_event_time("f_engine_sync", "foo")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "invalid component event value was passed. Passed value was "
            f"foo, must be one of: {corr.corr_component_events}"
        ),
    ):
        mcsession.add_correlator_component_event_time("foo", TEST_TIME1)


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
    )
    result = test_session.get_snap_status(starttime=t1 - TimeDelta(3.0, format="sec"))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_snap_status(
        t1,
        "heraNode701Snap3",
        "SNPD000703",
        True,
        595699,
        59.323028564453125,
        595699,
        t_prog,
    )

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), nodeID=700
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status(nodeID=700)
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

    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), stoptime=t1
    )
    assert len(result) == 2

    result_most_recent = test_session.get_snap_status()
    assert len(result) == 2

    result = test_session.get_snap_status(starttime=t1 + TimeDelta(200.0, format="sec"))
    assert result == []


def test_add_snap_status_from_corrcm(mcsession, snapstatus):
    test_session = mcsession
    test_session.add_snap_status_from_corrcm(snap_status_dict=snapstatus)

    t1 = Time(datetime.datetime(2016, 1, 5, 20, 44, 52, 741137), format="datetime")
    t_prog = Time(datetime.datetime(2016, 1, 10, 23, 16, 3), format="datetime")
    result = test_session.get_snap_status(
        starttime=t1 - TimeDelta(3.0, format="sec"), nodeID=700
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
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status(nodeID=700)
    assert len(result_most_recent) == 1
    result_most_recent = result_most_recent[0]
    assert result_most_recent.isclose(expected)

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
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result_most_recent = test_session.get_snap_status()
    assert len(result_most_recent) == 2


def test_add_snap_status_from_corrcm_with_nones(mcsession, snapstatus_none):
    test_session = mcsession
    snap_status_obj_list = test_session.add_snap_status_from_corrcm(
        snap_status_dict=snapstatus_none, testing=True
    )

    for obj in snap_status_obj_list:
        test_session.add(obj)

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
    )
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)


def test_snap_status_errors(mcsession):
    test_session = mcsession
    t1 = TEST_TIME1.copy()

    pytest.raises(
        ValueError,
        test_session.add_snap_status,
        "foo",
        "heraNode700Snap0",
        "SNPA000700",
        False,
        595687,
        57.984954833984375,
        595686,
        t1,
    )

    pytest.raises(
        ValueError,
        test_session.add_snap_status,
        t1,
        "heraNode700Snap0",
        "SNPA000700",
        False,
        595687,
        57.984954833984375,
        595686,
        "foo",
    )


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
    assert n_good_statuses == len(result_test2)

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
    assert n_good_statuses == len(result_test2)

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
@pytest.mark.filterwarnings("ignore:fem_switch value is UNKNOWN")
@pytest.mark.filterwarnings("ignore:fem_switch value is Unknown")
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
