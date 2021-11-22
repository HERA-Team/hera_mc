# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Setup testing environment.

"""

import warnings
import sys
import socket

import pytest

from hera_mc.utils import get_iterable
from hera_mc.correlator import DEFAULT_REDIS_ADDRESS

TEST_DEFAULT_REDIS_HOST = "redishost"


def redis_online():
    try:
        import redis

        r = redis.Redis(TEST_DEFAULT_REDIS_HOST)
        hera_redis = any(k for k in r.keys() if "hera" in k.decode()) > 0
    except:  # noqa
        hera_redis = False
    return (socket.gethostname() == "qmaster") or hera_redis


requires_redis = pytest.mark.skipif(
    not redis_online(), reason="This test requires a working redis database."
)


def default_redishost():
    return TEST_DEFAULT_REDIS_HOST == DEFAULT_REDIS_ADDRESS


# In practice, tests marked with `requires_default_redis` should also be marked with
# `requires_redis`. I don't want to add a `redis_online()` call to this decorator
# definition, though, because `redis_online()` take a long time to run if there's no
# redis online (because it waits a long time for a time out).
requires_default_redis = pytest.mark.skipif(
    not default_redishost(),
    reason="This test requires that the redis database used for testing has the default hostname.",
)


def is_onsite():
    return socket.gethostname() == "qmaster"


onsite = pytest.mark.skipif(not is_onsite(), reason="This test only works on site")


# Functions that are useful for testing:
def clearWarnings():
    """Quick code to make warnings reproducible."""
    for name, mod in list(sys.modules.items()):
        try:
            reg = getattr(mod, "__warningregistry__", None)
        except ImportError:
            continue
        if reg:
            reg.clear()


def checkWarnings(
    func,
    func_args=[],
    func_kwargs={},
    category=UserWarning,
    nwarnings=1,
    message=None,
    known_warning=None,
):
    """
    Check expected warnings.

    Useful for checking that appropriate warnings are raised and to capture
    (and silence) warnings in tests.

    Parameters
    ----------
    func : function
        Function or method to check warnings for.
    func_args : list, optional
        List of positional parameters to pass `func`
    func_kwargs : dict, optional
        Dict of keyword parameter to pass func. Keys are the parameter names,
        values are the values to pass to the parameters.
    nwarnings : int
        Number of expected warnings.
    category : warning type or list of warning types
        Expected warning type(s). If a scalar is passed and `nwarnings` is
        greater than one, the same category will be expected for all warnings.
    message : str or list of str
        Expected warning string(s). If a scalar is passed and `nwarnings` is
        greater than one, the same warning string will be expected for all warnings.
    known_warning : {'miriad', 'paper_uvfits', 'fhd'}, optional
        Shorthand way to specify one of a standard set of warnings.

    Returns
    -------
    Value returned by `func`

    Raises
    ------
    AssertionError
        If the warning(s) raised by func do not match the expected values.

    """
    if (not isinstance(category, list) or len(category) == 1) and nwarnings > 1:
        if isinstance(category, list):
            category = category * nwarnings
        else:
            category = [category] * nwarnings

    if (not isinstance(message, list) or len(message) == 1) and nwarnings > 1:
        if isinstance(message, list):
            message = message * nwarnings
        else:
            message = [message] * nwarnings

    category = get_iterable(category)
    message = get_iterable(message)

    clearWarnings()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")  # All warnings triggered
        retval = func(*func_args, **func_kwargs)  # Run function
        # Verify
        if len(w) != nwarnings:
            print(
                "wrong number of warnings. Expected number was {nexp}, "
                "actual number was {nact}.".format(nexp=nwarnings, nact=len(w))
            )
            for idx, wi in enumerate(w):
                print("warning {i} is: {w}".format(i=idx, w=wi))
            assert False
        else:
            for i, w_i in enumerate(w):
                if w_i.category is not category[i]:
                    assert False
                if message[i] is not None:
                    if message[i] not in str(w_i.message):
                        print("expected message " + str(i) + " was: ", message[i])
                        print("message " + str(i) + " was: ", str(w_i.message))
                        assert False
        return retval
