# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.qm`."""
from __future__ import absolute_import, division, print_function

import os

import pytest
from astropy.time import Time, TimeDelta

from hera_qm.firstcal_metrics import get_firstcal_metrics_dict
from hera_qm.utils import get_metrics_dict

from .. import mc
from .. import utils
from ..tests import checkWarnings
from ..qm import AntMetrics, ArrayMetrics


@pytest.fixture(scope='module')
def metrics_dict():
    return get_metrics_dict()


@pytest.mark.parametrize('pol_x,pol_y', [('x', 'y'),
                                         ('n', 'e')
                                         ]
                         )
def test_AntMetrics(mcsession, pol_x, pol_y):
    test_session = mcsession
    # Initialize
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format='sec'), t2,
                         obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format='sec'), t2,
                         obsid + 10)
    # Same for metric description
    test_session.add_metric_desc('test', 'Test metric')
    test_session.commit()

    # now the tests
    test_session.add_ant_metric(obsid, 0, pol_x, 'test', 4.5)
    r = test_session.get_ant_metric(metric='test')
    assert len(r) == 1
    assert r[0].antpol == (0, pol_x)
    assert r[0].metric == 'test'
    assert r[0].val == 4.5

    # Test more exciting queries
    test_session.add_ant_metric(obsid, 0, pol_y, 'test', 2.5)
    test_session.add_ant_metric(obsid, 3, pol_x, 'test', 2.5)
    test_session.add_ant_metric(obsid, 3, pol_y, 'test', 2.5)
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
    r = test_session.get_ant_metric(starttime=obsid - 10, stoptime=obsid + 4)
    assert len(r) == 4
    t1 = Time(obsid - 10, format='gps')
    t2 = Time(obsid + 4, format='gps')
    r = test_session.get_ant_metric(starttime=t1, stoptime=t2)
    assert len(r) == 4
    r = test_session.get_ant_metric(ant=[0, 3], pol=[pol_x, pol_y])
    assert len(r) == 4


@pytest.mark.parametrize(
    'ant,pol,metric,val,err_msg',
    [('0', 'x', 'test', 4.5, 'antenna must be an integer.'),
     (0, u'\xff', 'test', 4.5, 'pol must be string "x"'),
     (0, 'Q', 'test', 4.5, 'pol must be string'),
     (0, 'x', 4, 4.5, 'metric must be string.'),
     (0, 'x', 'test', 'value', 'val must be castable as float'),
     ]

)
def test_add_AntMetrics_errors(mcsession, ant, pol, metric, val, err_msg):
    test_session = mcsession
    # Initialize
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format='sec'), t2,
                         obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format='sec'), t2,
                         obsid + 10)
    # Same for metric description
    test_session.add_metric_desc('test', 'Test metric')
    test_session.commit()

    # Test exceptions
    with pytest.raises(ValueError) as cm:
        test_session.add_ant_metric(obsid, ant, pol, metric, val)
    assert str(cm.value).startswith(err_msg)


def test_add_AntMetrics_bad_obsid(mcsession):
    test_session = mcsession
    # Initialize
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format='sec'), t2,
                         obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format='sec'), t2,
                         obsid + 10)
    # Same for metric description
    test_session.add_metric_desc('test', 'Test metric')
    test_session.commit()
    with pytest.raises(ValueError) as cm:
        test_session.add_ant_metric('obs', 0, 'x', 'test', 4.5)
    assert str(cm.value).startswith('obsid must be an integer')


def test_create_AntMetrics_bad_mc_time(mcsession):
    # # Initialize a time
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    obsid = utils.calculate_obsid(t1)
    with pytest.raises(ValueError) as cm:
        AntMetrics.create(obsid, 0, 'x', 'test', obsid, 4.5)
    assert str(cm.value).startswith('db_time must be an astropy Time object')


def test_ArrayMetrics(mcsession):
    test_session = mcsession
    # Initialize
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format='sec'), t2, obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format='sec'), t2, obsid + 10)
    # Same for metric description
    test_session.add_metric_desc('test', 'Test metric')
    test_session.commit()

    # now the tests
    test_session.add_array_metric(obsid, 'test', 6.2)
    r = test_session.get_array_metric()
    assert r[0].metric == 'test'
    assert r[0].val == 6.2

    # Test more exciting queries
    test_session.add_array_metric(obsid + 10, 'test', 2.5)
    test_session.add_array_metric(obsid - 10, 'test', 2.5)
    r = test_session.get_array_metric(metric='test')
    assert len(r) == 3
    r = test_session.get_array_metric(starttime=obsid)
    assert len(r) == 2
    r = test_session.get_array_metric(stoptime=obsid)
    assert len(r) == 2
    t1 = Time(obsid - 20, format='gps')
    t2 = Time(obsid + 20, format='gps')
    r = test_session.get_array_metric(starttime=t1, stoptime=t2)
    assert len(r) == 3

    # Test exceptions
    pytest.raises(ValueError, test_session.add_array_metric, 'obs', 'test', 4.5)
    pytest.raises(ValueError, test_session.add_array_metric, obsid, 4, 4.5)
    pytest.raises(ValueError, test_session.add_array_metric, obsid,
                  'test', 'value')
    pytest.raises(ValueError, ArrayMetrics.create, obsid, 'test', obsid, 4.5)


def test_MetricList(mcsession):
    test_session = mcsession
    # Initialize
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.add_obs(t1 - TimeDelta(10.0, format='sec'), t2, obsid - 10)
    test_session.add_obs(t1 + TimeDelta(10.0, format='sec'), t2, obsid + 10)

    # now the tests
    test_session.add_metric_desc('test', 'test desc')
    r = test_session.get_metric_desc(metric='test')
    assert r[0].metric == 'test'
    assert r[0].desc == 'test desc'

    test_session.update_metric_desc('test', 'new desc')
    r = test_session.get_metric_desc(metric='test')
    assert r[0].desc == 'new desc'

    # Test exceptions
    pytest.raises(ValueError, test_session.add_metric_desc, 4, 'desc')
    pytest.raises(ValueError, test_session.add_metric_desc, 'test', 5)

    # Test check_metric_desc function to auto-fill descriptions
    test_session.check_metric_desc('test')
    r = test_session.get_metric_desc(metric='test')
    assert r[0].desc == 'new desc'
    checkWarnings(test_session.check_metric_desc, ['test2'],
                  message='Metric test2 not found in db')
    r = test_session.get_metric_desc(metric='test2')
    assert 'Auto-generated description.' in r[0].desc


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
    test_session.update_metric_desc(metric, 'foo')
    test_session.commit()
    # Doing it again will update rather than insert.
    test_session.update_qm_list()
    r = test_session.get_metric_desc(metric=metric)
    assert r[0].desc == metrics_dict[metric]


def test_ingest_metrics_file(mcsession):
    test_session = mcsession
    # Initialize
    t1 = Time('2016-01-10 01:15:23', scale='utc')
    t2 = t1 + TimeDelta(120.0, format='sec')
    obsid = utils.calculate_obsid(t1)
    # Create obs to satifsy foreign key constraints
    test_session.add_obs(t1, t2, obsid)
    test_session.commit()
    filename = os.path.join(mc.test_data_path, 'example_firstcal_metrics.json')
    filebase = os.path.basename(filename)
    pytest.raises(ValueError, test_session.ingest_metrics_file,
                  filename, 'firstcal')
    test_session.add_lib_file(filebase, obsid, t2, 0.1)
    test_session.commit()
    test_session.update_qm_list()
    test_session.ingest_metrics_file(filename, 'firstcal')
    # Check that things got in
    firstcal_array_metrics = set(['firstcal_metrics_agg_std_x',
                                  'firstcal_metrics_good_sol_x',
                                  'firstcal_metrics_max_std_x'])
    r = test_session.get_array_metric()
    assert len(r) == 3
    for result in r:
        assert result.metric in firstcal_array_metrics
    firstcal_ant_metrics = (set(get_firstcal_metrics_dict().keys())
                            - firstcal_array_metrics)
    r = test_session.get_ant_metric()
    for result in r:
        assert result.metric in firstcal_ant_metrics
