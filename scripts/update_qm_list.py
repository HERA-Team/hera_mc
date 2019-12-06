#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import hera_mc.mc as mc

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)
session = db.sessionmaker()

session.update_qm_list()

session.commit()
