#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import argparse, aipy
from hera_mc.observations import Observation
from hera_mc import mc
from astropy.time import Time, TimeDelta

a = mc.get_mc_argument_parser()
a.description = """Read the obsid from a file and create a record in M&C."""
a.add_argument('files', metavar='file', type=str, nargs='*', default=[],
               help='*.uv files to extract')
args = a.parse_args()
db = mc.connect_to_mc_db(args)


for uvfile in args.files:
    # we need aipy to read the stopt and duration because everything is awful
    # but first tell AIPY we're allowed to read these variables
    aipy.miriad.itemtable['stopt'] = 'd'
    aipy.miriad.itemtable['duration'] = 'd'
    UV = aipy.miriad.UV(uvfile)
    obsid = UV['obsid']

    with db.sessionmaker() as session:
        obs = session.get_obs(obsid)
        if len(obs) > 0:
            print("observation {obs} already in M&C, skipping".format(obs=obsid))
            continue
        stoptime = Time(UV['stopt'], scale='utc', format='gps')
        starttime = Time(UV['startt'], scale='utc', format='gps')
        print("Inserting obsid into M&C:" + str(UV['obsid']))

        session.add_obs(starttime, stoptime, obsid)
    session.commit()
