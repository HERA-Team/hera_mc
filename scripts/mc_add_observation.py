#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import os
import numpy as np
from astropy.time import Time

import aipy
from pyuvdata import UVData

from hera_mc import mc

a = mc.get_mc_argument_parser()
a.description = """Read the obsid from a file and create a record in M&C."""
a.add_argument('files', metavar='file', type=str, nargs='*', default=[],
               help='*.uv files to extract')
args = a.parse_args()
db = mc.connect_to_mc_db(args)


for uvfile in args.files:
    if os.path.isdir(uvfile):
        # assume it's a miriad file
        # we need aipy to read the stopt and duration because everything is awful
        # but first tell AIPY we're allowed to read these variables
        aipy.miriad.itemtable['stopt'] = 'd'
        aipy.miriad.itemtable['duration'] = 'd'
        UV = aipy.miriad.UV(uvfile)
        obsid = UV['obsid']
        stoptime = Time(UV['stopt'], scale='utc', format='gps')
        starttime = Time(UV['startt'], scale='utc', format='gps')
    else:
        # assume it's uvh5
        uv = UVData()
        uv.read_uvh5(uvfile, read_data=False)
        times = np.unique(uv.time_array)
        starttime = Time(times[0], scale='utc', format='jd')
        stoptime = Time(times[-1], scale='utc', format='jd')
        obsid = int(np.floor(starttime.gps))

    with db.sessionmaker() as session:
        obs = session.get_obs(obsid)
        if len(obs) > 0:
            print("observation {obs} already in M&C, skipping".format(obs=obsid))
            continue
        print("Inserting obsid into M&C:" + str(obsid))

        session.add_obs(starttime, stoptime, obsid)
    session.commit()
