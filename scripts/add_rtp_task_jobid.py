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


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "obsid", dest="obsid",
        type=int,
        help="obsid processed by RTP, or obsid_start for multiple obsid tasks."
    )
    parser.add_argument(
        "task_name", dest="task_name", type=str, help="RTP task name"
    )
    parser.add_argument(
        "job_id", dest="job_id", type=int, help="Slurm Job ID of the RTP task."
    )
    parser.add_argument(
        "--obsid_list",
        dest="obsid_list",
        nargs='+',
        type=int,
        default=None,
        help="List of obsids included in this task, only used for multiple obsid tasks. "
        "Will add entries to the `rtp_task_multiple_track` and "
        "`rtp_task_multiple_resource_record` tables rather than to the "
        "`rtp_task_jobid` table."
    )
    parser.add_argument(

    )
    args = parser.parse_args()

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        if args.obsid_list is not None:
            for obsid in args.obsid_list:
                session.add_rtp_task_multiple_track(
                    obsid_start=args.obsid,
                    task_name=args.task_name,
                    obsid=obsid,
                )

            session.add_rtp_task_multiple_jobid(
                obsid_start=args.obsid,
                task_name=args.task_name,
                start_time=Time.now(),
                job_id=args.job_id,
            )
        else:
            session.add_rtp_task_jobid(
                obsid=args.obsid,
                task_name=args.task_name,
                start_time=Time.now(),
                job_id=args.job_id,
            )
