# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`."""

from __future__ import absolute_import, division, print_function

import os

from .. import cm_utils, cm_dataview
from ..tests import checkWarnings


def test_ant_by_day(mcsession):
    dv = cm_dataview.Dataview(session=mcsession)
    start = cm_utils.get_astropytime(1184354550)
    stop = cm_utils.get_astropytime(1184354600)
    interval = 1.0
    filename = None
    output_date_format = 'jd'
    c = checkWarnings(dv.ants_by_day, [start, stop, interval, filename, output_date_format],
                      message='More than one active connection for HH68')
    assert len(c) == 1
    filename = os.path.expanduser('~/hera_mc_dataview_test.txt')
    output_date_format = 'iso'
    c = checkWarnings(dv.ants_by_day, [start, stop, interval, filename, output_date_format],
                      message='More than one active connection for HH68')
    assert len(c) == 1
    os.remove(filename)


def test_connected_by_day(mcsession):
    dv = cm_dataview.Dataview(session=mcsession)
    start = cm_utils.get_astropytime(1184354550)
    stop = cm_utils.get_astropytime(1184354600)
    interval = 10.0
    filename = None
    n = dv.connected_by_day(start, stop, interval)
    assert len(n.keys()) == 1
    filename = os.path.expanduser('~/hera_mc_dataview_test.txt')
    n = dv.connected_by_day(start, stop, interval, output=filename, output_date_format='iso')
    assert len(n.keys()) == 1
    os.remove(filename)
