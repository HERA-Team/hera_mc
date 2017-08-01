#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import hera_mc.mc as mc
from hera_qm import ant_metrics
import os
import numpy as np
import warnings


def fill_desc(s, m):
    # Function to fill description of metric in db.
    warnings.warn('Metric ' + metric + ' not found in db. Adding a filler description.'
                  'Please update ASAP with hera_mc/scripts/update_qm_list.py.')
    s.add_metric_desc(metric, 'Auto-generated description. Update with '
                      'hera_mc/scripts/update_qm_list.py')
    s.commit()


parser = mc.get_mc_argument_parser()
parser.add_argument('files', metavar='files', type=str, nargs='+',
                    help='json files to read and enter into db.')
args = parser.parse_args()
db = mc.connect_to_mc_db(args)
session = db.sessionmaker()

files = args.files
if len(files) == 0:
    raise AssertionError('Please provide a list of ant_metrics json files')

for f in files:
    d = ant_metrics.load_antenna_metrics(f)
    obsids = []
    for df in d['datafile_list']:
        obsids.append(session.get_lib_files(filename=os.path.basename(df))[0].obsid)
    obsid = np.unique(obsids)
    if len(obsid) > 1:
        raise ValueError('Metric file ' + f + ' is derived from multiple obsids.')
    else:
        obsid = obsid[0]

    # Record metrics
    for category in ['final_metrics', 'final_mod_z_scores']:
        for met, array in d[category].items():
            metric = '_'.join([category, met])
            # Check to see metric is in db
            r = session.get_metric_desc(metric)
            if len(r) == 0:
                fill_desc(session, metric)
            for antpol, val in array.items():
                session.add_ant_metric(obsid, antpol[0], antpol[1], metric, val)

    for metric in ['crossed_ants', 'dead_ants', 'xants', 'removal_iteration']:
        r = session.get_metric_desc(metric)
        if len(r) == 0:
            fill_desc(session, metric)
        for antpol in d[metric]:
            session.add_ant_metric(obsid, antpol[0], antpol[1], metric, 1)

session.commit()
