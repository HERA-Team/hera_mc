#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import hera_mc.mc as mc
import os
import numpy as np
import warnings


parser = mc.get_mc_argument_parser()
parser.add_argument('files', metavar='files', type=str, nargs='+',
                    help='json files to read and enter into db.')
parser.add_argument('--type', dest='type', type=str, default=None,
                    help='File type to add to db. Options = ["ant", "firstcal", "omnical"]')
args = parser.parse_args()
db = mc.connect_to_mc_db(args)
session = db.sessionmaker()

files = args.files
if len(files) == 0:
    raise AssertionError('Please provide a list of quality metric files.')

for f in files:
    session.add_metrics_file(f, args.type)

session.commit()
