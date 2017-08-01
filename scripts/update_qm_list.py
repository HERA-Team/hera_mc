#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import hera_mc.mc as mc
from hera_qm.ant_metrics import metric_list
import numpy as np

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)
session = db.sessionmaker()

for metric, desc in metric_list.items():
    # Check if metric is already in db.
    r = session.get_metric_desc(metric=metric)
    if len(r) == 0:
        session.add_metric_desc(metric, desc)
    else:
        session.update_metric_desc(metric, desc)

session.commit()
