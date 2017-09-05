#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

import argparse,aipy
from hera_mc.observations import Observation
from hera_mc import mc
from astropy.time import Time,TimeDelta
a = mc.get_mc_argument_parser()
a.description = """Read the obsid from a file and create a record in M&C."""
a.add_argument('files',metavar='file',type=str,nargs='*',default=[],
        help='*.uv files to extract')
args = a.parse_args()
db = mc.connect_to_mc_db(args)


for uvfile in args.files:
    #we need aipy to read the stopt and duration because everything is aweful
    #but first tell AIPY we're allowed to read these variables
    aipy.miriad.itemtable['stopt'] = 'd'
    aipy.miriad.itemtable['duration'] = 'd'
    UV = aipy.miriad.UV(uvfile)
    stoptime = Time(UV['stopt'],scale='utc',format='gps')
    starttime = Time(UV['startt'],scale='utc',format='gps')
    obsid = UV['startt']

    with db.sessionmaker() as session:
        session.add_obs(starttime, stoptime, obsid)
    session.commit()
