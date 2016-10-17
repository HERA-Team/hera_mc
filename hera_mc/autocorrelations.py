# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""M&C logging of antenna autocorrelation powers.

These are key data for tracking antenna performance and failures.

"""

from __future__ import absolute_import, division, print_function

from argparse import Namespace
import datetime

import numpy as np

from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, SmallInteger, String

from . import MCDeclarativeBase, NotNull


class _MeasurementTypes (object):
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

MeasurementTypes = _MeasurementTypes ()


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

    value = NotNull(Float(precision='53')) # recommended portable way of getting double-precision float.
    "The autocorrelation value."

    @property
    def measurement_type_name (self):
        return MeasurementTypes.names[self.measurement_type]

    def __repr__(self):
        return ('<Autocorrelations id={self.id} time={self.time} antnum={self.antnum} '
                'polarization={self.polarization} measurement_type={self.measurement_type_name} '
                'value={self.value}>').format (self=self)


def plot_autocorrelations_for_plotly (session):
    # TBD.
    return
