#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2021 The HERA Collaboration
# Licensed under the 2-clause BSD License
"""
Launch an RTP workflow for completed JDs in redis.

This script uses the RTPLaunchRecord database to determine observations for
which to launch an RTP workflow.  For each observation
included in a launched workflow, the corresponding RTPLaunchRecord is updated.
"""

import re
import os
import shutil
import subprocess
import sys
import warnings
import numpy as np
from hera_mc import mc
import h5py
import hera_opm.mf_tools as mt
from astropy.time import Time

REDISHOST = 'redishost'
JD_KEY = 'corr:files:jds'
JD_READY = 2
JD_FAIL = -1

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
        except KeyError as err:
            raise ValueError(f"error reading file {filename}") from err
        starttime = Time(np.unique(time_array)[0], scale="utc", format="jd")
        obsids.append(int(np.floor(starttime.gps)))

    return obsids


if __name__ == '__main__':
    import redis
    import time

    SCAN_FILES = True
    RENAME_BAD_FILES = True
    BAD_SUFFIX = '.METADATA_ERROR'
    CONDA_ENV = 'RTP'
    WORKING_DIRECTORY = "/home/obs/rtp_makeflow"
    WORKFLOW_CONFIG = "/home/obs/src/hera_pipelines/pipelines/h6c/rtp/v2/h6c_rtp_stage_1.toml"

    db = mc.connect_to_mc_db(None)
    r = redis.Redis(REDISHOST, decode_responses=True)

    while True:
        jds = r.hgetall(JD_KEY)
        jds = [jd for jd, val in jds.items() if int(val) == JD_READY]
        if len(jds) == 0:
            print("No JDs ready")
            time.sleep(10)
            continue

        # just process one jd at a time
        jd_redis = jds[0]
        # set status to fail in case something happens
        r.hset(JD_KEY, jd_redis, JD_FAIL)
        jd = int(jd_redis)
        print("Processing JD", jd)

        filelist = []
        with db.sessionmaker() as session:
            results = session.get_rtp_launch_record_by_jd(jd)
            if len(results) == 0:
                # this shouldn't happen if processing works correctly
                warnings.warn(f"No RTP launch records found for JD {jd}. Flagging as failed.")
                continue
            for result in results:
                # build full filename
                filename = os.path.join(result.prefix, result.filename)
                filelist.append(filename)
        filelist = sorted(filelist)
        print(f'Found {len(filelist)} files for JD {jd}')
        existing_files = [f for f in filelist if os.path.exists(f)]
        if len(existing_files) == 0:
            warnings.warn("None of these files are on disk. Flagging as failed.")
            continue

        # scan files if desired
        obsids = []
        if SCAN_FILES:
            print('Scanning files')
            from pyuvdata import UVData

            bad_metadata_files = []
            for filename in filelist:
                try:
                    uvd = UVData()
                    uvd.read(filename, read_data=False)
                except (KeyError, OSError, ValueError):
                    bad_metadata_files.append(filename)
                    filelist.remove(filename)
                    if RENAME_BAD_FILES:
                        os.rename(filename, filename + BAD_SUFFIX)
                else:
                    # if file is valid, add obsid to running list
                    starttime = Time(np.unique(uvd.time_array)[0], scale="utc", format="jd")
                    obsids.append(int(np.floor(starttime.gps)))

        # go to working directory
        os.chdir(WORKING_DIRECTORY)
        jd_folder = os.path.join(os.getcwd(), f"{jd:d}")
        if not os.path.isdir(jd_folder):
            os.makedirs(jd_folder)
        os.chdir(jd_folder)

        # copy config file as a reference
        shutil.copy2(WORKFLOW_CONFIG, jd_folder)

        # make name of output makeflow file
        mf_filename = os.path.basename(WORKFLOW_CONFIG).rstrip(".toml") + ".mf"
        mf_filename = os.path.join(jd_folder, mf_filename)

        print('Building Makeflow')
        # make a workflow
        mt.build_makeflow_from_config(
            filelist, WORKFLOW_CONFIG, mf_filename, jd_folder
        )

        # launch workflow inside of tmux
        cmd = (
            "source /home/obs/.bashrc; "
            "conda deactivate; "
            f"conda activate {CONDA_ENV}; "
            f"makeflow -T slurm {mf_filename} -J 100; /bin/bash -l"
        )
        session_name = f"rtp_{jd}"
        tmux_cmd = ["tmux", "new-session", "-d", "-s", session_name, cmd]
        try:
            print('Launching:', tmux_cmd)
            subprocess.check_call(tmux_cmd)
        except subprocess.CalledProcessError as e:
            warnings.warn(
                f"Error spawning tmux session: command was {e.cmd}; "
                f"returncode was {e.returncode:d}; output was {e.output}; "
                f"stderr was {e.stderr}."
            )
            continue

        # if we get to here, assume launch was successful and delete jd from
        # list of unprocessed
        print(f'Removing redis key JD={jd}')
        r.hdel(JD_KEY, jd_redis)

        # update RTP launch records
        print('Updating RTP launch records')
        if len(obsids) == 0:
            obsids = _get_obsids(filelist)
        t0 = Time.now()
        with db.sessionmaker() as session:
            for filename, obsid in zip(filelist, obsids):
                session.update_rtp_launch_record(obsid, t0)
            session.commit()
        print(f'Finished JD={jd}')