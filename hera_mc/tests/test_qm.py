# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.qm`."""
import os

import pytest
from astropy.time import Time, TimeDelta

from .. import mc
from .. import utils
from ..tests import checkWarnings
from ..qm import AntMetrics, ArrayMetrics

pytest.importorskip("hera_qm")
from hera_qm.firstcal_metrics import get_firstcal_metrics_dict  # noqa
from hera_qm.utils import get_metrics_dict  # noqa


@pytest.fixture(scope="module")
def metrics_dict():
    return get_metrics_dict()


@pytest.mark.parametrize("pol_x,pol_y", [("x", "y"), ("n", "e")])
def test_AntMetrics(mcsession, tmpdir, pol_x, pol_y):
    test_session = mcsession
    # Initialize
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format="sec"), t2, obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format="sec"), t2, obsid + 10)
    # Same for metric description
    test_session.add_metric_desc("test", "Test metric")
    test_session.commit()

    # now the tests
    ant_metric_time = Time.now()
    test_session.add_ant_metric(obsid, 0, pol_x, "test", 4.5)
    test_session.commit()
    r = test_session.get_ant_metric(metric="test")
    assert len(r) == 1
    assert r[0].antpol == (0, pol_x)
    assert r[0].metric == "test"
    assert r[0].val == 4.5
    r_recent = test_session.get_ant_metric()
    assert r == r_recent

    # test that updating works
    test_session.add_ant_metric(obsid, 0, pol_x, "test", 4.3)
    test_session.commit()
    r = test_session.get_ant_metric(metric="test")
    assert len(r) == 1
    assert r[0].antpol == (0, pol_x)
    assert r[0].metric == "test"
    assert r[0].val == 4.3

    # Test more exciting queries
    test_session.add_ant_metric(obsid, 0, pol_y, "test", 2.5)
    test_session.add_ant_metric(obsid, 3, pol_x, "test", 2.5)
    test_session.add_ant_metric(obsid, 3, pol_y, "test", 2.5)
    r = test_session.get_ant_metric()
    assert len(r) == 4
    r = test_session.get_ant_metric(ant=0)
    assert len(r) == 2
    for ri in r:
        assert ri.ant == 0
    r = test_session.get_ant_metric(pol=pol_x)
    assert len(r) == 2
    for ri in r:
        assert ri.pol == pol_x
    t1 = ant_metric_time - TimeDelta(10.0, format="sec")
    t2 = ant_metric_time + TimeDelta(4.0, format="sec")
    r = test_session.get_ant_metric(starttime=t1, stoptime=t2)
    assert len(r) == 4

    r = test_session.get_ant_metric(obsid=obsid)
    assert len(r) == 4
    r = test_session.get_ant_metric(ant=3, pol=pol_y)
    assert len(r) == 1
    assert r[0].ant == 3
    assert r[0].pol == pol_y

    filename = os.path.join(tmpdir, "test_ant_metric.csv")
    test_session.get_ant_metric(metric="test", write_to_file=True, filename=filename)
    os.remove(filename)

    with pytest.raises(
        ValueError,
        match="If most_recent is set to False, at least one of ant, pol, metric, "
        "obsid, or starttime must be specified.",
    ):
        test_session.get_ant_metric(most_recent=False)


@pytest.mark.parametrize(
    "ant,pol,metric,val,err_msg",
    [
        ("0", "x", "test", 4.5, "antenna must be an integer."),
        (0, 5, "test", 4.5, "pol="),
        (0, "\xff", "test", 4.5, "pol="),
        (0, "Q", "test", 4.5, "pol="),
        (0, "x", 4, 4.5, "metric must be string."),
        (0, "x", "test", "value", "val must be castable as float"),
    ],
)
def test_add_AntMetrics_errors(mcsession, ant, pol, metric, val, err_msg):
    test_session = mcsession
    # Initialize
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format="sec"), t2, obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format="sec"), t2, obsid + 10)
    # Same for metric description
    test_session.add_metric_desc("test", "Test metric")
    test_session.commit()

    # Test exceptions
    with pytest.raises(ValueError, match=err_msg):
        test_session.add_ant_metric(obsid, ant, pol, metric, val)


def test_add_AntMetrics_bad_obsid(mcsession):
    test_session = mcsession
    # Initialize
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format="sec"), t2, obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format="sec"), t2, obsid + 10)
    # Same for metric description
    test_session.add_metric_desc("test", "Test metric")
    test_session.commit()
    with pytest.raises(ValueError, match="obsid must be an integer"):
        test_session.add_ant_metric("obs", 0, "x", "test", 4.5)


def test_create_AntMetrics_bad_mc_time(mcsession):
    # # Initialize a time
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    obsid = utils.calculate_obsid(t1)
    with pytest.raises(ValueError, match="db_time must be an astropy Time object"):
        AntMetrics.create(obsid, 0, "x", "test", obsid, 4.5)


def test_ArrayMetrics(mcsession, tmpdir):
    test_session = mcsession
    # Initialize
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    obsid0 = obsid - 10
    obsid2 = obsid + 10
    test_session.add_obs(t1 - TimeDelta(10.0, format="sec"), t2, obsid0)
    test_session.add_obs(t1 + TimeDelta(10.0, format="sec"), t2, obsid2)
    # Same for metric description
    test_session.add_metric_desc("test", "Test metric")
    test_session.commit()

    # now the tests
    array_metric_time = Time.now()
    test_session.add_array_metric(obsid, "test", 6.2)
    test_session.commit()
    r = test_session.get_array_metric()
    assert r[0].metric == "test"
    assert r[0].val == 6.2

    # test that updating works
    test_session.add_array_metric(obsid, "test", 6.5)
    test_session.commit()
    r = test_session.get_array_metric()
    assert r[0].metric == "test"
    assert r[0].val == 6.5

    # Test more exciting queries
    test_session.add_array_metric(obsid2, "test", 2.5)
    test_session.add_array_metric(obsid0, "test", 2.5)
    t1 = array_metric_time - TimeDelta(10.0, format="sec")
    t2 = array_metric_time + TimeDelta(4.0, format="sec")
    r = test_session.get_array_metric(starttime=t1, stoptime=t2)
    assert len(r) == 3

    r = test_session.get_array_metric(metric="test")
    assert len(r) == 3
    r = test_session.get_array_metric(obsid=obsid)
    assert len(r) == 1
    r = test_session.get_array_metric(obsid=obsid0)
    assert len(r) == 1

    filename = os.path.join(tmpdir, "test_array_metric.csv")
    test_session.get_array_metric(metric="test", write_to_file=True, filename=filename)
    os.remove(filename)

    with pytest.raises(
        ValueError,
        match="If most_recent is set to False, at least one of metric, obsid, or "
        "starttime must be specified.",
    ):
        test_session.get_array_metric(most_recent=False)

    # Test exceptions
    with pytest.raises(ValueError, match="obsid must be an integer."):
        test_session.add_array_metric("obs", "test", 4.5)
    with pytest.raises(ValueError, match="metric must be string."):
        test_session.add_array_metric(obsid, 4, 4.5)
    with pytest.raises(ValueError, match="val must be castable as float."):
        test_session.add_array_metric(obsid, "test", "value")
    with pytest.raises(ValueError, match="db_time must be an astropy Time object"):
        ArrayMetrics.create(obsid, "test", obsid, 4.5)


def test_MetricList(mcsession, tmpdir):
    test_session = mcsession
    # Initialize
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format="sec"), t2, obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format="sec"), t2, obsid + 10)

    # now the tests
    test_session.add_metric_desc("test", "test desc")
    r = test_session.get_metric_desc(metric="test")
    assert r[0].metric == "test"
    assert r[0].desc == "test desc"

    test_session.update_metric_desc("test", "new desc")
    r = test_session.get_metric_desc(metric="test")
    assert r[0].desc == "new desc"

    filename = os.path.join(tmpdir, "test_metric_desc.csv")
    test_session.get_metric_desc(metric="test", write_to_file=True, filename=filename)
    os.remove(filename)

    # Test exceptions
    with pytest.raises(
        ValueError,
        match="metric must be string.",
    ):
        test_session.add_metric_desc(4, "desc")
    with pytest.raises(
        ValueError,
        match="metric description must be a string.",
    ):
        test_session.add_metric_desc("test", 5)

    # Test check_metric_desc function to auto-fill descriptions
    test_session.check_metric_desc("test")
    r = test_session.get_metric_desc(metric="test")
    assert r[0].desc == "new desc"
    checkWarnings(
        test_session.check_metric_desc,
        ["test2"],
        message="Metric test2 not found in db",
    )
    r = test_session.get_metric_desc(metric="test2")
    assert "Auto-generated description." in r[0].desc


def test_update_qm_list(mcsession, metrics_dict):
    test_session = mcsession
    test_session.update_qm_list()
    r = test_session.get_metric_desc()
    results = []
    for result in r:
        assert result.metric in metrics_dict
        results.append(result.metric)
    for metric in metrics_dict.keys():
        assert metric in results
    metric = list(metrics_dict.keys())[0]
    test_session.update_metric_desc(metric, "foo")
    test_session.commit()
    # Doing it again will update rather than insert.
    test_session.update_qm_list()
    r = test_session.get_metric_desc(metric=metric)
    assert r[0].desc == metrics_dict[metric]


def test_ingest_metrics_file(mcsession):
    test_session = mcsession
    # Initialize
    t1 = Time("2016-01-10 01:15:23", scale="utc")
    t2 = t1 + TimeDelta(120.0, format="sec")
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.commit()
    filename = os.path.join(mc.test_data_path, "example_firstcal_metrics.hdf5")
    filebase = os.path.basename(filename)
    with pytest.raises(
        ValueError,
        match=f"File {filename} has not been logged in Librarian, "
        "so we cannot add to M&C.",
    ):
        test_session.ingest_metrics_file(filename, "firstcal")
    test_session.add_lib_file(filebase, obsid, t2, 0.1)
    test_session.commit()
    test_session.update_qm_list()
    test_session.ingest_metrics_file(filename, "firstcal")
    # Check that things got in
    firstcal_array_metrics = {
        "firstcal_metrics_agg_std_x",
        "firstcal_metrics_good_sol_x",
        "firstcal_metrics_max_std_x",
    }
    r = test_session.get_array_metric()
    assert len(r) == 3
    for result in r:
        assert result.metric in firstcal_array_metrics
    firstcal_ant_metrics = (
        set(get_firstcal_metrics_dict().keys()) - firstcal_array_metrics
    )
    r = test_session.get_ant_metric()
    for result in r:
        assert result.metric in firstcal_ant_metrics
