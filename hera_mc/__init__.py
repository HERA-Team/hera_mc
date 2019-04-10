# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

from types import MethodType
import numpy as np
import six

# Before we can do anything else, we need to initialize some core, shared
# variables.

from sqlalchemy.ext.declarative import declarative_base


# define some default tolerances for various units
DEFAULT_DAY_TOL = {'atol': 1e-3 / (3600. * 24.), 'rtol': 0}  # ms
DEFAULT_HOUR_TOL = {'atol': 1e-3 / (3600), 'rtol': 0}  # ms
DEFAULT_MIN_TOL = {'atol': 1e-3 / (3600), 'rtol': 0}  # ms
DEFAULT_GPS_TOL = {'atol': 1e-3, 'rtol': 0}  # ms


class MCDeclarativeBase(object):
    def __repr__(self):
        columns = self.__table__.columns.keys()
        rep_str = '<' + self.__class__.__name__ + '('
        for c in columns:
            rep_str += str(getattr(self, c)) + ', '
        rep_str = rep_str[0:-2]
        rep_str += ')>'
        return rep_str

    def isclose(self, other):
        if not isinstance(other, self.__class__):
            print('not the same class')
            return False

        self_columns = self.__table__.columns
        other_columns = other.__table__.columns
        if set(c.name for c in self_columns) != set(c.name for c in other_columns):
            print('set of columns are not the same')
            return False

        for c in self_columns:
            self_c = getattr(self, c.name)
            other_c = getattr(other, c.name)
            if isinstance(self_c, six.string_types + six.integer_types):
                if self_c != other_c:
                    print('column {col} is string-like or int-like, values are not '
                          'equal'.format(col=c))
                    return False
            elif isinstance(self_c, np.ndarray) and self_c.dtype.kind == 'i':
                if not np.all(self_c == other_c):
                    print('column {col} is an int-like array, values are not equal'.format(col=c))
                    return False
            elif self_c is None and other_c is None:
                pass  # nullable columns, both null
            else:
                if hasattr(self, 'tols') and c.name in self.tols.keys():
                    atol = self.tols[c.name]['atol']
                    rtol = self.tols[c.name]['rtol']
                else:
                    # use numpy defaults
                    atol = 1e-08
                    rtol = 1e-05
                if not np.isclose(self_c, other_c, atol=atol, rtol=rtol):
                    print('column {col} is float-like or a float-like array, values are not equal'.format(col=c))
                    return False
        return True


MCDeclarativeBase = declarative_base(cls=MCDeclarativeBase)

import logging  # noqa
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Now we can pull in the rest of our definitions.


def NotNull(kind, **kwargs):
    from sqlalchemy import Column
    return Column(kind, nullable=False, **kwargs)


from . import version  # noqa
from . import autocorrelations  # noqa
from . import cm_transfer  # noqa
from . import cm_partconn  # noqa
from . import geo_location  # noqa
from . import observations  # noqa
from . import subsystem_error  # noqa
from . import server_status  # noqa
from . import librarian  # noqa
from . import rtp  # noqa
from . import qm  # noqa
from . import weather  # noqa
from . import node  # noqa
from . import correlator  # noqa
from . import mc    # noqa keep this last.

__version__ = version.version
