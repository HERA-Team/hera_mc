# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Setup testing environment."""

import socket

import pytest

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
