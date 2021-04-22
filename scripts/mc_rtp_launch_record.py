#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 The HERA Collaboration
# Licensed under the 2-clause BSD license.
"""
Add or update the RTP Launch Record for an observation.

This script takes a list of observations and either adds new RTP Launch Records
into the M&C database (if they do not yet exist) or updates them with the latest
launch time if they are. It is assumed that files corresponding to new
observations are added by the correlator as they are taken using this script,
and then updated when RTP launches a job containing them.
"""

import os
import socket
import numpy as np
from astropy.time import Time

from pyuvdata import UVData
from hera_mc import mc

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
    # get appropriate filename and prefix information
    filename = os.path.basename(uvfile)
    hostname = socket.gethostname()
    if "hera-sn1" in hostname:
        prefix = os.path.join("/mnt/sn1", f"{int_jd:d}")
    elif "hera-sn2" in hostname:
        prefix = os.path.join("/mnt/sn2", f"{int_jd:d}")
    else:
        # default
        prefix = "unknown"

    with db.sessionmaker() as session:
        obs = session.get_obs(obsid)
        if len(obs) == 0:
            print(f"observation {obsid} not in M&C, skipping")
            continue
        result = session.get_rtp_launch_record(obsid)
        if len(result) == 0:
            # add a new launch record
            session.add_rtp_launch_record(obsid, int_jd, obs_tag, filename, prefix)
        else:
            # update existing record
            t0 = Time.now()
            session.update_rtp_launch_record(obsid, t0)

        session.commit()
