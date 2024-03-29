#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Add RTP task resource records to the M&C database.

This script finds all entries in RTPTaskJobID (RTPTaskMultipleJobID) that
have no corresponding entry in RTPTaskResourceRecord
(RTPTaskMultipleResourceRecord).  Computing information (time, memory, cpu
usage) for all missing entries is obtained from the SLURM database and added
to the corresponding M&C task resource record tables.

"""

from subprocess import check_output

import numpy as np
from astropy.time import Time

from hera_mc import mc
from hera_mc.rtp import (
    RTPTaskJobID,
    RTPTaskMultipleJobID,
    RTPTaskMultipleProcessEvent,
    RTPTaskMultipleResourceRecord,
    RTPTaskProcessEvent,
    RTPTaskResourceRecord,
)


def cpu_time_to_seconds(time_str):
    """
    Convert `time_str` from 'D-HH:MM:SS' (format of CPUTime from SLURM) to seconds.

    Parameters
    ----------
    time_str : str
        String with format 'D-HH:MM:SS' or 'HH:MM:SS'.

    Returns
    -------
    secs : float
        Number of seconds.

    """
    if "-" in time_str:
        days = float(time_str.split("-")[0])
        time_str = time_str.split("-")[1]
    else:
        days = 0.0

    if len(time_str.split(":")) == 2:
        mins, secs = time_str.split(":")
        mins = float(mins)
        secs = float(secs)
    else:
        hours, mins, secs = time_str.split(":")
        hours = float(hours)
        mins = float(mins)
        secs = float(secs)
        secs += hours * 3600.0
    secs += mins * 60 + days * 24 * 60 * 60
    return secs


def query_slurm_db(jobid):
    """
    Query the SLURM database using `sacct` and the `--format` flag.

    Only the columns specified by `format_cols` are included in the query.
    For all available columns see `sacct --helpformat`.

    Parameters
    ----------
    jobid : int
        SLURM JobID to query.

    Returns
    -------
    slurm_dict : dictionary
        Dictionary containing SLURM start time, stop time, max memory (MaxRSS),
        and average CPU load for `jobid`.

    """
    query_state = ["sacct", "-j", "{}".format(jobid), "--format=state"]
    output_state = check_output(query_state).decode("utf-8")
    if "completed" not in output_state.lower():
        return None

    format_cols = [
        "JobID",
        "Start",
        "End",
        "MaxRSS",
        "TotalCPU",
        "CPUTime",
        "NCPUS",
    ]
    format_opts_str = "--format=" + ",".join(format_cols)
    query = ["sacct", "-j", "{}".format(jobid), format_opts_str]

    output = check_output(query).decode("utf-8")
    output = output.split("\n")
    line_to_use = np.where([line.startswith("{}.".format(jobid)) for line in output])[
        0
    ][0]
    output = output[line_to_use].split()

    slurm_dict = {}

    start_time = Time(output[1], format="isot", scale="utc")
    slurm_dict["start_time"] = start_time

    stop_time = Time(output[2], format="isot", scale="utc")
    slurm_dict["stop_time"] = stop_time

    memory_field = output[3]
    # MaxRSS might have a suffix like "K", "M", "G", etc.;
    # we record the value in megabytes.
    if memory_field[-1].lower() == "k":
        max_memory = float(memory_field[:-1]) / 1e3
    elif memory_field[-1].lower() == "m":
        max_memory = float(memory_field[:-1])
    elif memory_field[-1].lower() == "g":
        max_memory = float(memory_field[:-1]) * 1e3
    else:
        max_memory = float(memory_field) / 1e6
    slurm_dict["max_memory"] = max_memory

    totalcpu = cpu_time_to_seconds(output[4])
    cputime = cpu_time_to_seconds(output[5])
    ncpus = int(output[6])
    slurm_dict["avg_cpu_load"] = totalcpu / cputime * ncpus

    return slurm_dict


def get_jobid_from_finished_tasks(event_query, jobid_query, jobid_table, event_table):
    """
    Find the SLURM JobID associated with the most recent finished task.

    For all jobs with matching obsid and task_name values, determines the
    SLURM JobID from `jobid_query` with the closest start time to the
    start time of the most recent finished task in `event_query`.
    `jobid_query` and `event_query` must only contain entries for tasks
    with a given obsid and task_name.  If no job for a given obsid and task_name
    is marked as finished, that obsid and task_name pair is ignored.

    Parameters
    ----------
    event_query : query
        Query containing all task process events with a matching obsid and
        task_name.
    jobid_query : query
        Query containing all SLURM tasks with a matching obsid and task_name.
    jobid_table : class
        Class specifying the SLURM JobID table to query, i.e. RTPTaskJobID
        or RTPTaskMultipleJobID.
    event_table : class
        Class specifying the event table to query, i.e. RTPTaskProcessEvent
        or RTPTaskMultipleProcessEvent.

    Returns
    -------
    task : object
        `jobid_table` entry with a start time closest to the most recent
        finished task in `event_table`.  If no finished tasks found, returns
        None.

    """
    finished_tasks = event_query.filter(event_table.event == "finished")
    if finished_tasks.count() > 0:
        finish_time = finished_tasks[-1].time
        started_tasks = event_query.filter(event_table.event == "started")
        start_times = started_tasks.with_entities(event_table.time)
        start_times = start_times.order_by(event_table.time)
        start_times = np.array([t[0] for t in start_times.all()], dtype=int)
        start_time_ind = np.argmin(np.abs(finish_time - start_times))
        start_time_tpe = start_times[start_time_ind]
        mult_times = jobid_query.with_entities(jobid_table.start_time)
        mult_times = mult_times.order_by(jobid_table.start_time)
        mult_times = np.array([t[0] for t in mult_times.all()], dtype=int)
        closest_time_ind = np.argmin(np.abs(start_time_tpe - mult_times))
        closest_time = int(mult_times[closest_time_ind])
        task = jobid_query.filter(jobid_table.start_time == closest_time)
        task = task[0]
        return task
    else:
        return None


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "--nrows",
        type=int,
        default=1000,
        help="Sets the maximum number of rows to be added to the resource "
        "record tables.",
    )
    args = parser.parse_args()

    db = mc.connect_to_mc_db(None)

    with db.sessionmaker() as session:
        task_objs = session.query(RTPTaskJobID)
        task_objs = task_objs.filter(RTPTaskJobID.obsid > 0)
        task_objs = task_objs.join(
            RTPTaskResourceRecord,
            (RTPTaskJobID.obsid == RTPTaskResourceRecord.obsid)
            & (RTPTaskJobID.task_name == RTPTaskResourceRecord.task_name),
            isouter=True,
        )
        task_objs = task_objs.filter(RTPTaskResourceRecord.obsid.is_(None))
        task_objs = task_objs.order_by(RTPTaskJobID.obsid.desc())
        for task in task_objs.limit(args.nrows):
            trr_query = session.query(RTPTaskResourceRecord)
            trr_query = trr_query.filter(
                (RTPTaskResourceRecord.obsid == task.obsid)
                & (RTPTaskResourceRecord.task_name == task.task_name)
            )
            if trr_query.count() == 0:
                # Check for multiple run attempts and either pull the attempt
                # marked as "finished" or use the most recent attempt
                mult_attempts = task_objs.filter(
                    (RTPTaskJobID.obsid == task.obsid)
                    & (RTPTaskJobID.task_name == task.task_name)
                )
                if mult_attempts.count() > 1:
                    tpe_query = session.query(RTPTaskProcessEvent)
                    tpe_query = tpe_query.filter(
                        (RTPTaskProcessEvent.obsid == task.obsid)
                        & (RTPTaskProcessEvent.task_name == task.task_name)
                    )
                    if tpe_query.count() == 0:
                        # Some JDs are missing from RTPTaskProcessEvent
                        # If a JD is missing, use the last attempt
                        task = mult_attempts.order_by(RTPTaskJobID.start_time)[-1]
                    else:
                        chosen_task = get_jobid_from_finished_tasks(
                            tpe_query, mult_attempts, RTPTaskJobID, RTPTaskProcessEvent
                        )
                        if chosen_task is not None:
                            task = chosen_task
                slurm_dict = query_slurm_db(task.job_id)
                if slurm_dict is not None:
                    session.add_rtp_task_resource_record(
                        task.obsid, task.task_name, **slurm_dict
                    )

        task_mult_objs = session.query(RTPTaskMultipleJobID)
        task_mult_objs = task_mult_objs.filter(RTPTaskMultipleJobID.obsid_start > 0)
        task_mult_objs = task_mult_objs.join(
            RTPTaskMultipleResourceRecord,
            (
                RTPTaskMultipleJobID.obsid_start
                == RTPTaskMultipleResourceRecord.obsid_start
            )
            & (
                RTPTaskMultipleJobID.task_name
                == RTPTaskMultipleResourceRecord.task_name
            ),
            isouter=True,
        )
        task_mult_objs = task_mult_objs.filter(
            RTPTaskMultipleResourceRecord.obsid_start.is_(None)
        )
        task_mult_objs = task_mult_objs.order_by(
            RTPTaskMultipleJobID.obsid_start.desc()
        )
        for task in task_mult_objs.limit(args.nrows):
            mtrr_query = session.query(RTPTaskMultipleResourceRecord)
            mtrr_query = mtrr_query.filter(
                (RTPTaskMultipleResourceRecord.obsid_start == task.obsid_start)
                & (RTPTaskMultipleResourceRecord.task_name == task.task_name)
            )
            if mtrr_query.count() == 0:
                # Check for multiple run attempts and either pull the attempt
                # marked as "finished" or use the most recent attempt
                mult_attempts = task_mult_objs.filter(
                    (RTPTaskMultipleJobID.obsid_start == task.obsid_start)
                    & (RTPTaskMultipleJobID.task_name == task.task_name)
                )
                if mult_attempts.count() > 1:
                    tpe_query = session.query(RTPTaskMultipleProcessEvent)
                    tpe_query = tpe_query.filter(
                        (RTPTaskMultipleProcessEvent.obsid_start == task.obsid_start)
                        & (RTPTaskMultipleProcessEvent.task_name == task.task_name)
                    )
                    if tpe_query.count() == 0:
                        # Some JDs are missing from RTPTaskMultipleProcessEvent
                        # If a JD is missing, use the last attempt
                        task = mult_attempts.order_by(RTPTaskMultipleJobID.start_time)[
                            -1
                        ]
                    else:
                        chosen_task = get_jobid_from_finished_tasks(
                            tpe_query,
                            mult_attempts,
                            RTPTaskMultipleJobID,
                            RTPTaskMultipleProcessEvent,
                        )
                        if chosen_task is not None:
                            task = chosen_task
                slurm_dict = query_slurm_db(task.job_id)
                if slurm_dict is not None:
                    session.add_rtp_task_multiple_resource_record(
                        task.obsid_start, task.task_name, **slurm_dict
                    )
