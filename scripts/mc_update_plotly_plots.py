#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016-2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from hera_mc import mc, autocorrelations, server_status

parser = mc.get_mc_argument_parser()
args = parser.parse_args()

try:
    db = mc.connect_to_mc_db(args)
except RuntimeError as e:
    raise SystemExit(str(e))

with db.sessionmaker() as session:
    server_status.plot_host_status_for_plotly(session)
    autocorrelations.plot_HERA_autocorrelations_for_plotly(session)
