#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Runs the method that pulls correlator configuration data out of redis into hera_mc

"""

from hera_mc import cm_redis_corr

cm_redis_corr.parse_snap_config_to_psql()
