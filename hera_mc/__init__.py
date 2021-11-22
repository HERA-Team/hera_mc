# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Define package structure."""

import numpy as np
from setuptools_scm import get_version
from pathlib import Path
from pkg_resources import get_distribution, DistributionNotFound

from .branch_scheme import branch_scheme

try:  # pragma: nocover
    # get accurate version for developer installs
    version_str = get_version(Path(__file__).parent.parent, local_scheme=branch_scheme)

    __version__ = version_str

except (LookupError, ImportError):
    try:
        # Set the version automatically from the package details.
        __version__ = get_distribution(__name__).version
    except DistributionNotFound:  # pragma: nocover
        # package is not installed
        pass

# Before we can do anything else, we need to initialize some core, shared
# variables.

from sqlalchemy.ext.declarative import declarative_base


# define some default tolerances for various units
DEFAULT_DAY_TOL = {"atol": 1e-3 / (3600.0 * 24.0), "rtol": 0}  # ms
DEFAULT_HOUR_TOL = {"atol": 1e-3 / (3600), "rtol": 0}  # ms
DEFAULT_MIN_TOL = {"atol": 1e-3 / (3600), "rtol": 0}  # ms
DEFAULT_GPS_TOL = {"atol": 1e-3, "rtol": 0}  # ms


class MCDeclarativeBase(object):
    """Base table object."""

    def __repr__(self):
        """Define standard representation."""
        columns = self.__table__.columns.keys()
        rep_str = "<" + self.__class__.__name__ + "("
        for c in columns:
            rep_str += str(getattr(self, c)) + ", "
        rep_str = rep_str[0:-2]
        rep_str += ")>"
        return rep_str

    def isclose(self, other):
        """Test if two objects are nearly equal."""
        if not isinstance(other, self.__class__):
            print("not the same class")
            return False

        self_columns = self.__table__.columns
        other_columns = other.__table__.columns
        if {c.name for c in self_columns} != {c.name for c in other_columns}:
            print("set of columns are not the same")
            return False

        for c in self_columns:
            self_c = getattr(self, c.name)
            other_c = getattr(other, c.name)
            if isinstance(self_c, int):
                if self_c != other_c:
                    print("column {col} is int, values are not equal".format(col=c))
                    return False
            elif isinstance(self_c, str):
                if self_c != other_c:
                    print("column {col} is str, values are not equal".format(col=c))
                    return False
            elif isinstance(self_c, np.ndarray) and self_c.dtype.kind == "i":
                if not np.all(self_c == other_c):
                    print(
                        "column {col} is an int-like array, values are not equal".format(
                            col=c
                        )
                    )
                    return False
            elif self_c is None:
                if other_c is None:
                    pass  # nullable columns, both null
                else:
                    print(
                        "column {col} is None in first object and {val} in the second.".format(
                            col=c, val=other_c
                        )
                    )
                    return False
            else:
                if hasattr(self, "tols") and c.name in self.tols.keys():
                    atol = self.tols[c.name]["atol"]
                    rtol = self.tols[c.name]["rtol"]
                else:
                    # use numpy defaults
                    atol = 1e-08
                    rtol = 1e-05
                if not np.isclose(self_c, other_c, atol=atol, rtol=rtol):
                    print(
                        "column {col} is float-like or a float-like array, "
                        "values are not equal".format(col=c)
                    )
                    return False
        return True


MCDeclarativeBase = declarative_base(cls=MCDeclarativeBase)

import logging  # noqa

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Now we can pull in the rest of our definitions.


def NotNull(kind, **kwargs):
    """Define a non-nullable column."""
    from sqlalchemy import Column

    return Column(kind, nullable=False, **kwargs)


from . import autocorrelations  # noqa
from . import cm_transfer  # noqa
from . import cm_dossier  # noqa
from . import cm_active  # noqa
from . import cm_sysdef  # noqa
from . import cm_utils  # noqa
from . import cm_sysutils  # noqa
from . import cm_partconnect  # noqa
from . import correlator  # noqa
from . import daemon_status  # noqa
from . import geo_location  # noqa
from . import observations  # noqa
from . import subsystem_error  # noqa
from . import server_status  # noqa
from . import librarian  # noqa
from . import node  # noqa
from . import rtp  # noqa
from . import qm  # noqa
from . import weather  # noqa
from . import mc  # noqa keep this last.
