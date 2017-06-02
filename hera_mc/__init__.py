# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function
from types import MethodType
import datetime
import pytz
import numpy as np

# Before we can do anything else, we need to initialize some core, shared
# variables.

from sqlalchemy.ext.declarative import declarative_base
MCDeclarativeBase = declarative_base()


def __repr__(self):
    columns = self.__table__.columns.keys()
    rep_str = '<' + self.__class__.__name__ + '('
    for c in columns:
        rep_str += str(getattr(self, c)) + ', '
    rep_str = rep_str[0:-2]
    rep_str += ')>'
    return rep_str


def __eq__(self, other):
    if isinstance(other, self.__class__):

        self_columns = self.__table__.columns.keys()
        other_columns = other.__table__.columns.keys()
        if set(self_columns) != set(other_columns):
            print('Sets of columns do not match. Left is {lset},'
                  ' right is {rset}'.format(lset=self_columns,
                                            rset=other_columns))
            return False

        c_equal = True
        for c in self_columns:
            self_c = getattr(self, c)
            other_c = getattr(other, c)
            print('column ', c, ', type is ', type(self_c))
            if isinstance(self_c, (str, unicode)):
                if self_c != other_c:
                    print('column ', c, ' does not match. Left is ', self_c, ' Right is ', other_c)
                    c_equal = False
            elif isinstance(self_c, datetime.datetime):
                self_c = self_c.astimezone(pytz.utc)
                other_c = other_c.astimezone(pytz.utc)
                if self_c != other_c:
                    print('column ', c, ' does not match. Left is ', self_c, ' Right is ', other_c)
                    c_equal = False
            else:
                if not np.isclose(self_c, other_c):
                    print('column ', c, ' does not match. Left is ', self_c, ' Right is ', other_c)
                    c_equal = False
        return c_equal
    else:
        print('Classes do not match')
        return False


MCDeclarativeBase.__repr__ = MethodType(__repr__, None, MCDeclarativeBase)
MCDeclarativeBase.__eq__ = MethodType(__eq__, None, MCDeclarativeBase)


import logging
logger = logging.getLogger(__name__)

# Now we can pull in the rest of our definitions.


def NotNull(kind, **kwargs):
    from sqlalchemy import Column
    return Column(kind, nullable=False, **kwargs)

from .version import __version__
from . import autocorrelations
from . import host_status
from . import part_connect
from . import geo_location
from . import temperatures
from . import observations
from . import server_status
from . import mc  # keep this last.
