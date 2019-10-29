# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of antenna autocorrelation powers.

These are key data for tracking antenna performance and failures.

"""

from __future__ import absolute_import, division, print_function

import numpy as np
import six
from sqlalchemy import (BigInteger, Column, DateTime, Float, Integer,
                        SmallInteger, String)

from . import MCDeclarativeBase, NotNull, cm_sysutils


class _MeasurementTypes(object):
    """A read-only enumeration of different ways we can measure the
    autocorrelation power, since each autocorrelation measurement is a
    spectrum. For now we only have one type, but in the future we might add
    min/max/rms, different sub-windows of the spectra, etc.

    These values are logged into the M&C database. Once a certain value is
    created, never remove or change it!

    """
    median = 0
    "The median value across the whole autocorrelation spectrum."

    names = ['median']
    "A list of textual names corresponding to each value."


MeasurementTypes = _MeasurementTypes()


class Autocorrelations(MCDeclarativeBase):
    """A table logging antenna autocorrelations.

    """
    __tablename__ = 'autocorrelations'

    id = Column(BigInteger, primary_key=True)
    "A unique ID number for each record; no intrinsic meaning."

    time = NotNull(DateTime)
    "The time when the information was generated; stored as SqlAlchemy UTC DateTime."

    antnum = NotNull(Integer)
    "The internal antenna number to which this record pertains."

    polarization = NotNull(String(1))
    """Which polarization this record refers to: "x" or "y"."""

    measurement_type = NotNull(SmallInteger)
    "The type of measurement; see MeasurementTypes enumeration."

    # recommended portable way of getting double-precision float.
    value = NotNull(Float(precision='53'))
    "The autocorrelation value."

    @property
    def measurement_type_name(self):
        return MeasurementTypes.names[self.measurement_type]

    def __repr__(self):
        return('<Autocorrelations id={self.id} time={self.time} antnum={self.antnum} '
               'polarization={self.polarization} measurement_type={self.measurement_type_name} '
               'value={self.value}>').format(self=self)


def plot_HERA_autocorrelations_for_plotly(session, offline_testing=False):
    if six.PY3:
        from plotly import graph_objects as go
    else:
        from plotly import graph_objs as go

    from chart_studio import plotly as py

    hsession = cm_sysutils.Handling(session)
    stations = hsession.get_all_fully_connected_at_date(at_date='now')

    hera_ants = []
    for station in stations:
        if station.antenna_number not in hera_ants:
            hera_ants = np.append(hera_ants, station.antenna_number)
    hera_ants = np.unique(hera_ants).astype(int).tolist()

    data = []

    # Plot antennas labeled as fully hooked up
    q = (session.query(Autocorrelations).
         filter(Autocorrelations.measurement_type == 0).
         filter(Autocorrelations.antnum.in_(hera_ants)).
         order_by(Autocorrelations.time).
         all())
    antennas = set(['{ant}{pol}'.format(ant=item.antnum, pol=item.polarization)
                    for item in q])
    data = {}
    for ant in antennas:
        data[ant] = []
    for item in q:
        key = '{ant}{pol}'.format(ant=item.antnum, pol=item.polarization)
        data[key].append([item.time, item.value])
    scatters = []
    for ant in data:
        d = np.array(data[ant])
        scatters.append(go.Scatter(x=d[:, 0],
                                   y=d[:, 1],
                                   name=ant,
                                   ))

    # Finish plot

    layout = go.Layout(showlegend=True,
                       title='HERA Autocorrelations',
                       xaxis={'title': 'Date',
                              },
                       yaxis={'title': 'auto power',
                              },
                       )
    fig = go.Figure(data=scatters,
                    layout=layout,
                    )
    if offline_testing:
        return fig
    else:
        py.plot(fig, auto_open=False,
                filename='HERA_daily_autos',
                )
