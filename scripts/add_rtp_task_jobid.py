#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Add RTP task jobid entry to the M&C database with a start_time of "now".

This script can be used for either single obsid tasks or multiple obsid tasks. For
multiple obsid tasks, pass the list of obsids to the `--obsid_list` parameter.

This script adds entries with a start_time of "now" meaning that the job was just
started. To update the table with past times, use the appropriate methods on the
MCSession object.

"""

from astropy.time import Time

import hera_mc.mc as mc
import hera_mc.utils as mcutils


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "filename",
        type=str,
        help=(
            "file processed by RTP corresponding to obsid, or obsid_start for "
            "multiple obsid tasks."
        ),
    )
    parser.add_argument("task_name", type=str, help="RTP task name")
    parser.add_argument("job_id", type=int, help="Slurm Job ID of the RTP task.")
    parser.add_argument(
        "--file_list",
        dest="file_list",
        nargs="+",
        type=str,
        default=None,
        help="List of files included in this task, only used for multiple obsid tasks. "
        "Will add entries to the `rtp_task_multiple_track` and "
        "`rtp_task_multiple_resource_record` tables rather than to the "
        "`rtp_task_jobid` table.",
    )
    args = parser.parse_args()

    # extract obsid from input file
    obsid = mcutils.get_obsid_from_file(args.filename)

    if args.file_list is not None:
        # extract obsid for each file
        obsid_list = []
        for filename in args.file_list:
            oid = mcutils.get_obsid_from_file(filename)
            obsid_list.append(oid)

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        if args.file_list is not None:
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

            session.add_rtp_task_multiple_jobid(
                obsid_start=obsid,
                task_name=args.task_name,
                start_time=Time.now(),
                job_id=args.job_id,
            )
        else:
            session.add_rtp_task_jobid(
                obsid=obsid,
                task_name=args.task_name,
                start_time=Time.now(),
                job_id=args.job_id,
            )
