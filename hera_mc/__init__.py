# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Define package structure.

isort:skip_file
"""

from pathlib import Path
import warnings

import numpy as np
from importlib.metadata import version, PackageNotFoundError
from setuptools_scm import get_version

from .branch_scheme import branch_scheme


try:  # pragma: nocover
    # get accurate version for developer installs
    version_str = get_version(Path(__file__).parent.parent, local_scheme=branch_scheme)

    __version__ = version_str

except (LookupError, ImportError):
    try:
        # Set the version automatically from the package details.
        __version__ = version("hera_mc")
    except PackageNotFoundError:  # pragma: nocover
        # package is not installed
        pass

# Before we can do anything else, we need to initialize some core, shared
# variables.

from sqlalchemy.orm import declarative_base

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
        # the following is structured as an assert because I cannot make it fail but
        # think it should be checked.
        assert {col.name for col in self_columns} == {
            col.name for col in other_columns
        }, (
            "Set of columns are not the same. This should not happen, please make an "
            "issue in our repo."
        )
        for col in self_columns:
            self_col = getattr(self, col.name)
            other_col = getattr(other, col.name)
            if not isinstance(other_col, type(self_col)):
                print(
                    f"column {col} has different types, left is {type(self_col)}, "
                    f"right is {type(other_col)}."
                )
                return False
            if isinstance(self_col, int):
                if self_col != other_col:
                    print(f"column {col} is int, values are not equal")
                    return False
            elif isinstance(self_col, str):
                if self_col != other_col:
                    print(f"column {col} is str, values are not equal")
                    return False
            elif self_col is None:
                pass  # nullable columns, both null (otherwise caught as different types)
            else:
                if hasattr(self, "tols") and col.name in self.tols.keys():
                    atol = self.tols[col.name]["atol"]
                    rtol = self.tols[col.name]["rtol"]
                else:
                    # use numpy defaults
                    atol = 1e-08
                    rtol = 1e-05
                if isinstance(self_col, (np.ndarray, list)):
                    if not np.allclose(self_col, other_col, atol=atol, rtol=rtol):
                        print(
                            f"column {col} is float-like or a float-like array, "
                            "values are not equal"
                        )
                        return False
                else:
                    if not np.isclose(self_col, other_col, atol=atol, rtol=rtol):
                        print(
                            f"column {col} is float-like or a float-like array, "
                            "values are not equal"
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


with warnings.catch_warnings():
    # This filter can be removed when pyuvdata (and maybe other imported packages?)
    # are updated to use importlib.metadata rather than pkg_resources
    warnings.filterwarnings("ignore", "Implementing implicit namespace packages")
    from . import autocorrelations  # noqa
    from . import cm_transfer  # noqa this needs to come before several others
    from . import cm_active  # noqa
    from . import cm_dossier  # noqa
    from . import cm_partconnect  # noqa
    from . import cm_sysdef  # noqa
    from . import cm_sysutils  # noqa
    from . import cm_utils  # noqa
    from . import correlator  # noqa
    from . import daemon_status  # noqa
    from . import geo_location  # noqa
    from . import librarian  # noqa
    from . import node  # noqa
    from . import observations  # noqa
    from . import qm  # noqa
    from . import rtp  # noqa
    from . import subsystem_error  # noqa
    from . import server_status  # noqa
    from . import weather  # noqa
    from . import mc  # noqa keep this last.
