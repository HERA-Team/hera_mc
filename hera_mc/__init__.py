# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function
from types import MethodType
import numpy as np

# Before we can do anything else, we need to initialize some core, shared
# variables.

from sqlalchemy.ext.declarative import declarative_base
MCDeclarativeBase = declarative_base()


def MCDeclarativeBase_repr(self):
    columns = self.__table__.columns.keys()
    rep_str = '<' + self.__class__.__name__ + '('
    for c in columns:
        rep_str += str(getattr(self, c)) + ', '
    rep_str = rep_str[0:-2]
    rep_str += ')>'
    return rep_str


# define some default tolerances for various units
DEFAULT_DAY_TOL = {'atol': 1e-3 / (3600. * 24.), 'rtol': 0}  # ms
DEFAULT_HOUR_TOL = {'atol': 1e-3 / (3600), 'rtol': 0}  # ms
DEFAULT_MIN_TOL = {'atol': 1e-3 / (3600), 'rtol': 0}  # ms
DEFAULT_GPS_TOL = {'atol': 1e-3, 'rtol': 0}  # ms


def MCDeclarativeBase_close(self, other):
    if not isinstance(other, self.__class__):
        return False

    self_columns = self.__table__.columns
    other_columns = other.__table__.columns
    if set(c.name for c in self_columns) != set(c.name for c in other_columns):
        print('set of columns are not the same')
        return False

    for c in self_columns:
        self_c = getattr(self, c.name)
        other_c = getattr(other, c.name)
        if isinstance(self_c, (str, unicode, int, long)):
            if self_c != other_c:
                print('column {col} is string-like or int-like, values are not '
                      'equal'.format(col=c))
                return False
        elif isinstance(self_c, (np.ndarray)) and isinstance(self_c.dtype, (int, long)):
            if not np.all(self_c == other_c):
                print('column {col} is an int-like array, values are not equal'.format(col=c))
                return False
        else:
            if hasattr(self, 'tols') and c.name in self.tols.keys():
                atol = self.tols[c.name]['atol']
                rtol = self.tols[c.name]['rtol']
            else:
                # use numpy defaults
                atol = 1e-08
                rtol = 1e-05
            if not np.isclose(self_c, other_c, atol=atol, rtol=rtol):
                print('column {col} is an float-like array, values are not equal'.format(col=c))
                return False
    return True


MCDeclarativeBase.__repr__ = MethodType(MCDeclarativeBase_repr, None, MCDeclarativeBase)
MCDeclarativeBase.isclose = MethodType(MCDeclarativeBase_close, None, MCDeclarativeBase)

import logging
logger = logging.getLogger(__name__)

# Now we can pull in the rest of our definitions.


def NotNull(kind, **kwargs):
    from sqlalchemy import Column
    return Column(kind, nullable=False, **kwargs)

from .version import __version__
from . import autocorrelations
from . import part_connect
from . import geo_location
from . import temperatures
from . import observations
from . import subsystem_error
from . import server_status
from . import librarian
from . import rtp
from . import qm
from . import mc  # keep this last.
