# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.subsystem_error`."""
from __future__ import absolute_import, division, print_function

from math import floor
import pytest

from astropy.time import Time, TimeDelta

from ..subsystem_error import SubsystemError


time = Time.now()
subsystem_error_names = ['id', 'time', 'subsystem', 'mc_time', 'severity',
                         'log']
subsystem_error_values = [1, time, 'librarian', time, 1, 'bad problem']
subsystem_error_columns = dict(zip(subsystem_error_names,
                                   subsystem_error_values))


def test_add_subsystem_error(mcsession):
    test_session = mcsession
    exp_columns = subsystem_error_columns.copy()
    exp_columns['time'] = int(floor(exp_columns['time'].gps))
    exp_columns['mc_time'] = int(floor(exp_columns['mc_time'].gps))
    expected = SubsystemError(**exp_columns)

    # try testing mode
    error_obj = test_session.add_subsystem_error(
        subsystem_error_values[1], subsystem_error_values[2],
        *subsystem_error_values[4:], testing=True)

    # error_obj.id isn't set because that's autoincremented by the database
    error_obj.id = expected.id

    # mc times may be different, set them equal to test the rest
    expected.mc_time = error_obj.mc_time

    assert error_obj.isclose(expected)

    test_session.add_subsystem_error(subsystem_error_values[1],
                                     subsystem_error_values[2],
                                     *subsystem_error_values[4:])
    # now actually add it
    result = test_session.get_subsystem_error(
        starttime=subsystem_error_columns['time']
        - TimeDelta(2 * 60, format='sec'))
    assert len(result) == 1
    result = result[0]

    assert result.isclose(expected)

    test_session.add_subsystem_error(subsystem_error_values[1], 'rtp',
                                     *subsystem_error_values[4:])
    result_subsystem = \
        test_session.get_subsystem_error(
            starttime=subsystem_error_columns['time']
            - TimeDelta(2, format='sec'),
            subsystem=subsystem_error_columns['subsystem'],
            stoptime=subsystem_error_columns['time']
            + TimeDelta(2 * 60, format='sec'))
    assert len(result_subsystem) == 1
    result_subsystem = result_subsystem[0]
    assert result_subsystem.isclose(expected)

    result_mult = test_session.get_subsystem_error(
        starttime=subsystem_error_columns['time']
        - TimeDelta(2, format='sec'),
        stoptime=subsystem_error_columns['time']
        + TimeDelta(2 * 60, format='sec'))

    assert len(result_mult) == 2
    ids = [res.id for res in result_mult]
    assert ids == [1, 2]
    subsystems = [res.subsystem for res in result_mult]
    assert subsystems == ['librarian', 'rtp']

    result2 = test_session.get_subsystem_error(
        starttime=subsystem_error_columns['time'] - TimeDelta(2, format='sec'),
        subsystem='rtp')[0]

    assert not result2.isclose(expected)


def test_errors_subsystem_error(mcsession):
    test_session = mcsession
    pytest.raises(ValueError, test_session.add_subsystem_error,
                  'foo', subsystem_error_values[2],
                  *subsystem_error_values[4:])

    test_session.add_subsystem_error(subsystem_error_values[1],
                                     subsystem_error_values[2],
                                     *subsystem_error_values[4:])
    pytest.raises(ValueError, test_session.get_subsystem_error,
                  starttime='foo')
    pytest.raises(ValueError, test_session.get_subsystem_error,
                  starttime=subsystem_error_columns['time'], stoptime='foo')
