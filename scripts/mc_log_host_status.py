#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Record some basic numbers about this computer's status in the M&C database.
This should be run out of a cronjob, although it likely will need a wrapper
shell script to set up the right environment to find the Python modules.

"""
from __future__ import absolute_import, division, print_function

from hera_mc import host_status, mc

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

with db.sessionmaker () as session:
    session.add (host_status.HostStatus ())
