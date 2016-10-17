#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

from hera_mc import host_status, mc,autocorrelations

parser = mc.get_mc_argument_parser()
args = parser.parse_args()

try:
    db = mc.connect_to_mc_db(args)
except RuntimeError as e:
    raise SystemExit(str(e))

with db.sessionmaker() as session:
    host_status.plot_host_status_for_plotly(session)
    autocorrelations.plot_HERA_autocorrelations_for_plotly(session)
