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

import numpy as np
from subprocess import check_output
from astropy.time import Time
from hera_mc import mc
from hera_mc.rtp import (
    RTPTaskJobID,
    RTPTaskResourceRecord,
    RTPTaskMultipleJobID,
    RTPTaskMultipleResourceRecord,
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
    format_cols = [
        "JobID",
        "State",
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
    line_to_use = np.where(
        [line.startswith("{}.batch".format(jobid)) for line in output]
    )[0][0]
    output = output[line_to_use].split()
    job_state = output[1].lower()

    if job_state == "completed":
        slurm_dict = {}

        start_time = Time(output[2], format="isot", scale="utc")
        slurm_dict["start_time"] = start_time

        stop_time = Time(output[3], format="isot", scale="utc")
        slurm_dict["stop_time"] = stop_time

        max_memory = float(output[4][:-1])
        # SLURM provides the MaxRSS in bytes, but we choose to record in megabytes
        slurm_dict["max_memory"] = max_memory / 1e6

        totalcpu = cpu_time_to_seconds(output[5])
        cputime = cpu_time_to_seconds(output[6])
        ncpus = int(output[7])
        slurm_dict["avg_cpu_load"] = totalcpu / cputime * ncpus

        return slurm_dict
    else:
        return None


db = mc.connect_to_mc_db(None)

with db.sessionmaker() as session:
    task_objs = (
        session.query(RTPTaskJobID)
        .join(
            RTPTaskResourceRecord,
            (RTPTaskJobID.obsid == RTPTaskResourceRecord.obsid)
            & (RTPTaskJobID.task_name == RTPTaskResourceRecord.task_name),
            isouter=True,
        )
        .filter(RTPTaskResourceRecord.obsid.is_(None))
    )
    for task in task_objs.all():
        slurm_dict = query_slurm_db(task.job_id)
        if slurm_dict is not None:
            session.add_rtp_task_resource_record(
                task.obsid, task.task_name, **slurm_dict
            )

    task_mult_objs = (
        session.query(RTPTaskMultipleJobID)
        .join(
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
        .filter(RTPTaskMultipleResourceRecord.obsid_start.is_(None))
    )
    for task in task_mult_objs.all():
        slurm_dict = query_slurm_db(task.job_id)
        if slurm_dict is not None:
            session.add_rtp_task_multiple_resource_record(
                task.obsid_start, task.task_name, **slurm_dict
            )
