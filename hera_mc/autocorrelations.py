# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of antenna autocorrelation powers.

These are key data for tracking antenna performance and failures.

"""

from __future__ import absolute_import, division, print_function

from math import floor
from astropy.time import Time
import numpy as np
import six
from sqlalchemy import (BigInteger, Column, DateTime, Float, Integer,
                        SmallInteger, String)

from . import MCDeclarativeBase, NotNull


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

    names = ["median"]
    "A list of textual names corresponding to each value."


MeasurementTypes = _MeasurementTypes()


class HeraAuto(MCDeclarativeBase):
    """
    Definition of median antenna autocorrelation table of hera antennas.

    Attributes
    ----------
    time : BigInteger Column
        The time in GPS seconds of the observation, floored as an int. Part of primary_key
    antenna_number : Integer Column
        Antenna number. Part of primary_key.
    antenna_feed_pol : String Column
        Feed polarization, either 'e' or 'n'. Part of primary_key.
    measurement_type : SmallInt Column
        The type of measurement; see MeasurementTypes enumeration.
        Cannot be None.
    value : Float Columnn
        53 precision autocorrelation value.
        Cannot be None
    """

    __tablename__ = "hera_autos"

    time = Column(BigInteger, primary_key=True)
    antenna_number = Column(Integer, primary_key=True)
    antenna_feed_pol = Column(String, primary_key=True)
    measurement_type = Column(SmallInteger, nullable=False)
    # recommended portable way of getting double-precision float.
    value = Column(Float(precision="53"), nullable=False)

    @classmethod
    def create(cls, time, antenna_number, antenna_feed_pol, measurement_type, value):
        """
        Create a new Autocorrelation table object.

        Parameters
        ----------
        time : astropy time object
            Astropy time object based on timestamp of autocorrelation.
        antenna_number : int
            Antenna Number
        antenna_feed_pol : str
            Feed polarization, either 'e' or 'n'.
        measurement_type : Int
            The type of measurement as defined in the MeasurementTypes class.
            Currently only supports 'median'.
        value : float
            The median autocorrelation value as a float.

        """
        if not isinstance(time, Time):
            raise ValueError("time must be an astropy Time object.")
        auto_time = floor(time.gps)

        if antenna_feed_pol not in ['e', 'n']:
            raise ValueError("antenna_feed_pol must be 'e' or 'n'.")

        if isinstance(measurement_type, six.string_types):
            try:
                measurement_type = MeasurementTypes.names.index(measurement_type.lower())
            except ValueError:
                raise ValueError(
                    "Autocorrelation type {0} not supported. "
                    "Only the following types are supported: {1}"
                    .format(measurement_type, MeasurementTypes.names)
                )

        if measurement_type not in list(six.moves.range(len(MeasurementTypes.names))):
            raise ValueError(
                "Input measurement type is not in range of accepted values. "
                "Input {0}, Allowed range 0-{1}"
                .format(measurement_type, len(MeasurementTypes.names) - 1)
            )

        return cls(time=auto_time, antenna_number=antenna_number,
                   antenna_feed_pol=antenna_feed_pol, measurement_type=0, value=value)

    @property
    def measurement_type_name(self):
        return MeasurementTypes.names[self.measurement_type]

    def __repr__(self):
        return("<HeraAuto time={self.time} antenna_number={self.antenna_number} "
               "polarization={self.antenna_feed_pol} measurement_type={self.measurement_type_name} "
               "value={self.value}>").format(self=self)


def plot_HERA_autocorrelations_for_plotly(session, offline_testing=False):
    if six.PY3:
        from plotly import graph_objects as go
    else:
        from plotly import graph_objs as go

    from chart_studio import plotly as py

    data = []
    all_autos = session.get_autocorrelation(most_recent=True)

    antennas = set(['{ant}{pol}'.format(ant=item.antenna_number, pol=item.antenna_feed_pol)
                    for item in all_autos])
    data = {}
    for ant in antennas:
        data[ant] = []
    for item in all_autos:
        key = '{ant}{pol}'.format(ant=item.antenna_number, pol=item.antenna_feed_pol)
        data[key].append([Time(item.time, format='gps').isot, item.value])
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


# This table is deprecated and no longer maintained
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
