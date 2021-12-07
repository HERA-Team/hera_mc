#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 The HERA Collaboration
# Licensed under the 2-clause BSD License
"""
Launch an RTP workflow for the JD specified.

This script uses the RTPLaunchRecord database to determine observations for
which to launch an RTP workflow. If `jd` is specified, an RTP workflow is
launched for that day. Otherwise, it scans through all days for which a workflow
has not been launched and launches one for each day. For each observation
included in a launched workflow, the corresponding RTPLaunchRecord is updated.
"""

import os
import sys
import shutil
import warnings
import subprocess

import numpy as np
from astropy.time import Time

from hera_mc import mc

try:
    import h5py
except ImportError:
    sys.exit("h5py must be installed to use this script")

try:
    import hera_opm.mf_tools as mt
except ImportError:
    sys.exit("hera_opm must be installed to use this script")


def _get_obsids(filelist):
    """
    Compute the obsids for a list of files.

    Parameters
    ----------
    filelist : list of str
        The list of UVH5 files for which to infer obsids.

    Returns
    -------
    obsids : list of int
        The corresponding list of obsids for the files.

    """
    obsids = []
    for filename in filelist:
        try:
            with h5py.File(filename, "r") as h5f:
                time_array = h5f["Header/time_array"][()]
        except KeyError:
            raise ValueError(f"error reading file {filename}")
        starttime = Time(np.unique(time_array)[0], scale="utc", format="jd")
        obsids.append(int(np.floor(starttime.gps)))

    return obsids


ap = mc.get_mc_argument_parser()
ap.description = """Launch an RTP workflow for the JD specified"""
ap.add_argument(
    "jd", type=int, default=None, nargs="?", help="JD to launch an RTP job for"
)
ap.add_argument(
    "-c",
    "--workflow_config",
    type=str,
    default="/home/obs/src/hera_pipelines/pipelines/h5c/rtp/v1/h5c_rtp_stage_1.toml",
    help="hera_opm configuration to use for workflow",
)
ap.add_argument(
    "-d",
    "--working_directory",
    type=str,
    default="/home/obs/rtp_makeflow",
    help="working directory for RTP",
)
ap.add_argument(
    "--scan-files",
    action="store_true",
    default=False,
    help=(
        "Scan metadata of HERA data files before including in workflow. "
        "Requires pyuvdata"
    ),
)
ap.add_argument(
    "--rename-bad-files",
    action="store_true",
    default=False,
    help=(
        "Rename files with bad metadata (found with --scan-files) with suffix "
        "set by --bad-suffix."
    ),
)
ap.add_argument(
    "--bad-suffix",
    default=".METADATA_ERROR",
    type=str,
    help=(
        "String to append to files pyuvdata could not read after running with "
        "--scan-filea and --rename-bad-files. Default '.METADATA_ERROR'."
    ),
)
ap.add_argument(
    "-e",
    "--conda_env",
    default="RTP",
    type=str,
    help=("The conda environment to activate before launching RTP workflow."),
)

args = ap.parse_args()
db = mc.connect_to_mc_db(args)

if args.jd is None:
    # launch a separate job for each un-launched day
    jd_list = []
    with db.sessionmaker() as session:
        results = session.get_rtp_launch_record_by_rtp_attempts(0)
        for result in results:
            if result.jd not in jd_list:
                jd_list.append(result.jd)
else:
    jd_list = [args.jd]


# We'll accumulate all our errors into a single entry.
# This way we can try to start every JD in jd_list.
rtp_error = []

for jd in jd_list:
    filelist = []
    with db.sessionmaker() as session:
        results = session.get_rtp_launch_record_by_jd(jd)
        if len(results) == 0:
            warnings.warn(f"No RTP launch records found for JD {jd}, skipping")
            continue
        for result in results:
            # build full filename
            filename = os.path.join(result.prefix, result.filename)
            filelist.append(filename)

    # sort list
    filelist = sorted(filelist)

    # scan files if desired
    obsids = []
    if args.scan_files:
        try:
            from pyuvdata import UVData
        except ImportError:
            sys.exit("pyuvdata must be installed to use the --scan-files option")

        bad_metadata_files = []
        for filename in filelist:
            try:
                uvd = UVData()
                uvd.read(filename, read_data=False)
            except (KeyError, OSError, ValueError):
                bad_metadata_files.append(filename)
                filelist.remove(filename)
                if args.rename_bad_files:
                    os.rename(filename, filename + args.bad_suffix)
            else:
                # if file is valid, add obsid to running list
                starttime = Time(np.unique(uvd.time_array)[0], scale="utc", format="jd")
                obsids.append(int(np.floor(starttime.gps)))

    # go to working directory
    os.chdir(args.working_directory)
    jd_folder = os.path.join(os.getcwd(), f"{jd:d}")
    if not os.path.isdir(jd_folder):
        os.makedirs(jd_folder)
    os.chdir(jd_folder)

    # copy config file as a reference
    shutil.copy2(args.workflow_config, jd_folder)

    # make name of output makeflow file
    mf_filename = os.path.basename(args.workflow_config).rstrip(".toml") + ".mf"
    mf_filename = os.path.join(jd_folder, mf_filename)

    # make a workflow
    mt.build_makeflow_from_config(
        filelist, args.workflow_config, mf_filename, jd_folder
    )

    # launch workflow inside of tmux
    cmd = (
        "source /home/obs/.bashrc; "
        "conda deactivate; "
        f"conda activate {args.conda_env}; "
        f"makeflow -T slurm {mf_filename} -J 100; /bin/bash -l"
    )
    session_name = f"rtp_{jd}"
    tmux_cmd = ["tmux", "new-session", "-d", "-s", session_name, cmd]
    try:
        subprocess.check_call(tmux_cmd)
    except subprocess.CalledProcessError as e:
        rtp_error.append(
            f"Error spawning tmux session: command was {e.cmd}; "
            f"returncode was {e.returncode:d}; output was {e.output}; "
            f"stderr was {e.stderr}."
        )
        continue

    # update RTP launch records
    if len(obsids) == 0:
        obsids = _get_obsids(filelist)
    t0 = Time.now()
    with db.sessionmaker() as session:
        for filename, obsid in zip(filelist, obsids):
            try:
                session.update_rtp_launch_record(obsid, t0)
            except RuntimeError:
                rtp_error.append(
                    f"Error updating RTP Launch Record for file {filename}."
                )
                continue
        session.commit()

if len(rtp_error) > 0:
    sys.exit(rtp_error)
