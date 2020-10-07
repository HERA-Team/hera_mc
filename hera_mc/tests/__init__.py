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
TEST_DEFAULT_REDIS_HOST = 'redishost'


TEST_CORR_CONFIG = b'dest_port: 8511\neth: false\nfengines:\n  heraNode0Snap0:\n    ants:\n    - 0\n    - 1\n    - 2\n    phase_switch_index:\n    - 1\n    - 2\n    - 3\n    - 4\n    - 5\n    - 6\n  heraNode0Snap1:\n    ants:\n    - 3\n    - 4\n    - 5\n    phase_switch_index:\n    - 7\n    - 8\n    - 9\n    - 10\n    - 11\n    - 12\n  heraNode0Snap2:\n    ants:\n    - 6\n    - 7\n    - 8\n    phase_switch_index:\n    - 13\n    - 14\n    - 15\n    - 16\n    - 17\n    - 18\n  heraNode0Snap3:\n    ants:\n    - 9\n    - 10\n    - 11\n    phase_switch_index:\n    - 19\n    - 20\n    - 21\n    - 22\n    - 23\n    - 24\nfft_shift: 15086\nfpgfile: redis:snap_fengine_2020-07-16_1253.fpg\ninitialize: false\nlog_walsh_step_size: 3\nnoise: false\nsync: pps\ntvg: false\nwalsh_delay: 600\nwalsh_order: 32\nxengines:\n  0:\n    chan_range:\n    - 1536\n    - 1920\n    even:\n      ip: 10.80.40.197\n      mac: 2207786215621\n    odd:\n      ip: 10.80.40.206\n      mac: 2207786215630\n  1:\n    chan_range:\n    - 1920\n    - 2304\n    even:\n      ip: 10.80.40.229\n      mac: 2207786215653\n    odd:\n      ip: 10.80.40.238\n      mac: 2207786215662\n'  # noqa


def redis_online():
    try:
        import redis
        r = redis.Redis(TEST_DEFAULT_REDIS_HOST)
        hera_redis = len([k for k in r.keys() if 'hera' in k.decode()]) > 0
    except:  # noqa
        hera_redis = False
    return (socket.gethostname() == 'qmaster') or hera_redis


requires_redis = pytest.mark.skipif(not redis_online(),
                                    reason='This test requires a working redis database.')


def is_onsite():
    return (socket.gethostname() == 'qmaster')


onsite = pytest.mark.skipif(not is_onsite(),
                            reason='This test only works on site')


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


def checkWarnings(func, func_args=[], func_kwargs={},
                  category=UserWarning,
                  nwarnings=1, message=None, known_warning=None):
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
            print('wrong number of warnings. Expected number was {nexp}, '
                  'actual number was {nact}.'.format(nexp=nwarnings, nact=len(w)))
            for idx, wi in enumerate(w):
                print('warning {i} is: {w}'.format(i=idx, w=wi))
            assert(False)
        else:
            for i, w_i in enumerate(w):
                if w_i.category is not category[i]:
                    assert(False)
                if message[i] is not None:
                    if message[i] not in str(w_i.message):
                        print('expected message ' + str(i) + ' was: ', message[i])
                        print('message ' + str(i) + ' was: ', str(w_i.message))
                        assert(False)
        return retval
