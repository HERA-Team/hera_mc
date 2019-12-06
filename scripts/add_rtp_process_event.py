#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD License

"""
Script to add an RTP process event record to M&C.
"""
import numpy as np
import h5py
from astropy.time import Time

import hera_mc.mc as mc

parser = mc.get_mc_argument_parser()
parser.add_argument(
    "filename", metavar="FILE", type=str, help="Name of the file to add an event for."
)
parser.add_argument(
    "event",
    metavar="EVENT",
    type=str,
    help=(
        "Event to add for the file. Must be one of: "
        '"queued", "started", "finished", "error"'
    ),
)

# parse args
args = parser.parse_args()

# get the obsid from the file
with h5py.File(args.filename, "r") as h5f:
    time_array = h5f["Header/time_array"][()]
t0 = Time(np.unique(time_array)[0], scale="utc", format="jd")
obsid = int(np.floor(t0.gps))

# add the process event
db = mc.connect_to_mc_db(args)
with db.sessionmaker() as session:
    session.add_rtp_process_event(time=Time.now(), obsid=obsid, event=args.event)
