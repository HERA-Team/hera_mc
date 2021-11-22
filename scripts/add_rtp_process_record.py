#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Add individual processing record to M&C database from RTP."""

import warnings
from pkg_resources import parse_version

import numpy as np
from astropy.time import Time

import hera_mc.mc as mc
import hera_qm
import hera_opm
import hera_cal
import pyuvdata


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "file",
        metavar="file",
        type=str,
        nargs=1,
        help="Basename of file processed by RTP",
    )
    parser.add_argument(
        "--pipeline_list",
        dest="pipeline_list",
        type=str,
        required=True,
        help=("List of actions taken on " "file concatenated as a string"),
    )
    args = parser.parse_args()

    # get version info for relevant repos
    hera_qm_version_info = hera_qm.version.construct_version_info()
    hera_cal_version_info = hera_cal.version.construct_version_info()
    hera_opm_version_info = hera_opm.version.construct_version_info()

    # special handling for pyuvdata because it uses setuptools_scm
    pyuvdata_version = pyuvdata.__version__
    parsed_version = parse_version(pyuvdata_version)
    pyuvdata_tag = parsed_version.base_version
    local = parsed_version.local

    if local is None:
        # we're running from a "clean" (tagged/released) repo
        # get the git info from GitHub directly
        from subprocess import CalledProcessError, check_output

        gitcmd = [
            "git",
            "ls-remote",
            "https://github.com/RadioAstronomySoftwareGroup/pyuvdata.git",
            f"v{pyuvdata_tag}",
        ]

        try:
            output = check_output(gitcmd).decode("utf-8")
            pyuvdata_git_hash = output.split()[0]
        except CalledProcessError:
            pyuvdata_git_hash = "???"
    else:
        # check if version has a "dirty" tag
        split_local = local.split(".")
        if len(split_local) > 1:
            warnings.warn(
                "pyuvdata was installed with uncommited changes. Please commit "
                "changes and reinstall."
            )

        # get git info from tag -- the hash has a leading "g" that we ignore
        pyuvdata_git_hash = split_local[0][1:]

    uv = pyuvdata.UVData()
    # args.file is a length-1 list
    uv.read_uvh5(args.file[0], read_data=False, run_check_acceptability=False)
    t0 = Time(np.unique(uv.time_array)[0], scale="utc", format="jd")
    obsid = int(np.floor(t0.gps))

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        session.add_rtp_process_record(
            time=Time.now(),
            obsid=obsid,
            pipeline_list=args.pipeline_list,
            rtp_git_version=hera_opm_version_info["version"],
            rtp_git_hash=hera_opm_version_info["git_hash"],
            hera_qm_git_version=hera_qm_version_info["version"],
            hera_qm_git_hash=hera_qm_version_info["git_hash"],
            hera_cal_git_version=hera_cal_version_info["version"],
            hera_cal_git_hash=hera_cal_version_info["git_hash"],
            pyuvdata_git_version=pyuvdata_tag,
            pyuvdata_git_hash=pyuvdata_git_hash,
        )
