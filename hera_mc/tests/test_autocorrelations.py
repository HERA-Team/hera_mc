# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.autocorrelations`."""
from __future__ import absolute_import, division, print_function

import pytest

from hera_mc import autocorrelations, cm_sysutils

import six
if six.PY3:
    from plotly import graph_objects as go
else:
    from plotly import graph_objs as go


@pytest.fixture(scope='function')
def test_figure(mcsession):
    test_session = mcsession
    figure = autocorrelations.plot_HERA_autocorrelations_for_plotly(
        test_session, offline_testing=True
    )
    yield figure

    del figure


@pytest.fixture(scope='function')
def sys_handle(mcsession):
    return cm_sysutils.Handling(mcsession)


def test_figure_is_created(test_figure):
    assert isinstance(test_figure, go.Figure)


def test_ants_in_figure(mcsession, test_figure, sys_handle):
    # This test is a little tautological however it does check that all
    # antennas we "think" are connected have autocorrelations.
    # the test session has no entries in this table so it should be null
    figure = test_figure

    ants_in_fig = [d.name for d in figure.data]

    assert ants_in_fig == []
