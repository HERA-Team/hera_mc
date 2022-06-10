#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Add individual processing record to M&C database from RTP."""

import warnings
import importlib
from pkg_resources import parse_version

import numpy as np
from astropy.time import Time

import hera_mc.mc as mc
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
        help=("List of actions taken on file concatenated as a string"),
    )
    args = parser.parse_args()

    version_info = {}
    for repo_name in ["pyuvdata", "hera_qm", "hera_cal", "hera_opm"]:

        version_info[repo_name] = {}

        # we're importing things at an odd place here
        # but this lets us script up the version info
        local_version_info = importlib.import_module(repo_name).__version__

        parsed_version = parse_version(local_version_info)
        version_info[repo_name]["tag"] = parsed_version.base_version
        local = parsed_version.local

        if repo_name == "pyuvdata":
            url = "RadioAstronomySoftwareGroup"
        else:
            url = "HERA-Team"
        if local is None:
            # we're running from a "clean" (tagged/released) repo
            # get the git info from GitHub directly
            from subprocess import CalledProcessError, check_output

            gitcmd = [
                "git",
                "ls-remote",
                f"https://github.com/{url}/{repo_name}.git",
                f"v{version_info[repo_name]['tag']}",
            ]

            try:
                output = check_output(gitcmd).decode("utf-8")
                version_info[repo_name]["hash"] = output.split()[0]
            except CalledProcessError:
                version_info[repo_name]["hash"] = "???"
        else:
            # check if version has a "dirty" tag
            split_local = local.split(".")
            if len(split_local) > 1:
                warnings.warn(
                    f"{repo_name} was installed with uncommited changes. Please commit "
                    "changes and reinstall."
                )

            # get git info from tag -- the hash has a leading "g" that we ignore
            version_info[repo_name]["hash"] = split_local[0][1:]

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
            rtp_git_version=version_info["hera_opm"]["tag"],
            rtp_git_hash=version_info["hera_opm"]["hash"],
            hera_qm_git_version=version_info["hera_qm"]["tag"],
            hera_qm_git_hash=version_info["herq_qm"]["hash"],
            hera_cal_git_version=version_info["hera_cal"]["tag"],
            hera_cal_git_hash=version_info["hera_cal"]["hash"],
            pyuvdata_git_version=version_info["pyuvdata"]["tag"],
            pyuvdata_git_hash=version_info["pyuvdata"]["hash"],
        )
