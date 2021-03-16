#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 The HERA Collaboration
# Licensed under the 2-clause BSD license.

import numpy as np
from astropy.time import Time

from pyuvdata import UVData

from hera_mc import mc
from hera_mc.rtp import RTPLaunchRecord

ap = mc.get_mc_argument_parser()
ap.description = """Add or update the RTP Launch Record for an observation."""
ap.add_argument(
    "files",
    metavar="files",
    type=str,
    nargs="*",
    default=[],
    help="*.uvh5 files to process",
)
args = ap.parse_args()
db = mc.connect_to_mc_db(args)

for uvfile in args.files:
    # assume our data is uvh5
    uv = UVData()
    uv.read(uvfile, read_data=False)
    times = np.unique(uv.time_array)
    starttime = Time(times[0], scale="utc", format="jd")
    int_jd = int(np.floor(starttime.jd))
    obsid = int(np.floor(starttime.gps))
    obs_tag = uv.extra_keywords["tag"]

    with db.sessionmaker() as session:
        obs = session.get_obs(obsid)
        if len(obs) == 0:
            print(f"observation {obsid} not in M&C, skipping")
            continue
        result = mc.get_rtp_launch_record(obsid)
        if len(query) == 0:
            # add a new launch record
            mc.add_rtp_launch_record(obsid, int_jd, obs_tag)
        else:
            # update existing record
            t0 = Time.now()
            mc.update_rtp_launch_record(obsid, t0)

    session.commit()
