#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to generate table initialization files (package from db to csv).
"""

import argparse

from hera_mc import cm_redis_corr
from hera_mc.correlator import DEFAULT_REDIS_ADDRESS

parser = argparse.ArgumentParser()
parser.add_argument(
    "-r", "--redishost", help="Redis host name", default=DEFAULT_REDIS_ADDRESS
)
args = parser.parse_args()

cm_redis_corr.set_redis_cminfo(redishost=args.redishost)
