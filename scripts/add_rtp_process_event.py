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


def get_obsid_from_file(filename):
    """
    Extract obsid from a UVH5 file.

    Parameters
    ----------
    filename : str
        The full path to the file.

    Returns
    -------
    obsid : int
        The obsid of the file.

    """
    with h5py.File(filename, "r") as h5f:
        time_array = h5f["Header/time_array"][()]
    t0 = np.unique(time_array)[0]
    time0 = Time(t0, format="jd", scale="utc")
    obsid = int(np.floor(time0.gps))

    return obsid


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "filename",
        metavar="FILE",
        type=str,
        help="Name of the file to add an event for.",
    )
    parser.add_argument("task_name", type=str, help="RTP task name")
    parser.add_argument(
        "event",
        metavar="EVENT",
        type=str,
        help=(
            "Event to add for the file. Must be one of: "
            '"started", "finished", "error"'
        ),
    )
    parser.add_argument(
        "--file_list",
        dest="file_list",
        nargs="+",
        type=str,
        default=None,
        help="List of files included in this task, only used for multiple obsid tasks. "
        "Will add entries to the `rtp_task_multiple_process_event` and "
        "`rtp_task_multiple_track` tables rather than to the `rtp_task_process_event` "
        "table.",
    )

    # parse args
    args = parser.parse_args()

    # get the obsid from the file
    obsid = get_obsid_from_file(args.filename)

    if args.file_list is not None:
        # extract obsid for each file
        obsid_list = []
        for filename in args.file_list:
            oid = get_obsid_from_file(filename)
            obsid_list.append(oid)

    # add the process event
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        if args.obsid_list is not None:
            for oid in obsid_list:
                # check to see if this has already been added
                rows = session.get_rtp_task_multiple_track(
                    obsid_start=obsid, task_name=args.task_name, obsid=oid
                )
                if len(rows) == 0:
                    # add the mapping
                    session.add_rtp_task_multiple_track(
                        obsid_start=obsid,
                        task_name=args.task_name,
                        obsid=oid,
                    )

            session.add_rtp_task_multiple_process_event(
                time=Time.now(),
                obsid_start=obsid,
                task_name=args.task_name,
                event=args.event,
            )
        else:
            session.add_rtp_task_process_event(
                time=Time.now(),
                obsid=obsid,
                task_name=args.task_name,
                event=args.event,
            )
