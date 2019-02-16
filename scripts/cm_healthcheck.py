#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to make various "health" checks on cm database
    check for duplicate connections
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_health

parser = mc.get_mc_argument_parser()
args = parser.parse_args()

db = mc.connect_to_mc_db(args)
session = db.sessionmaker()
health = cm_health.Connections(session)
health.check_for_duplicate_connections(display_results=True)
