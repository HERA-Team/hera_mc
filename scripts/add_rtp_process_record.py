#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Add individual processing record to M&C database from RTP."""
from __future__ import absolute_import, division, print_function

import numpy as np
from astropy.time import Time

import hera_mc.mc as mc
import hera_qm
import hera_opm
import hera_cal
import pyuvdata


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument('file', metavar='file', type=str, nargs='+',
                        help='Basename of file procesed by RTP')
    parser.add_argument('--pipeline_list', dest='pipeline_list', type=str,
                        required=True,
                        help=('List of actions taken on '
                              'file concatenated as a string')
                        )
    args = parser.parse_args()

    pyuvdata_version_info = pyuvdata.version.construct_version_info()
    hera_qm_version_info = hera_qm.version.construct_version_info()
    hera_cal_version_info = hera_cal.version.construct_version_info()
    hera_opm_version_info = hera_opm.version.construct_version_info()

    uv = pyuvdata.UVData()
    uv.read_uvh5(args.file, read_data=False, run_check_acceptability=False)
    t0 = Time(np.unique(uv.time_array)[0], scale='utc', format='jd')
    obsid = int(np.floor(t0.gps))

    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        session.add_rtp_process_record(
            time=Time.now(),
            obsid=obsid,
            pipeline_list=args.pipeline_list,
            rtp_git_version=hera_opm_version_info['version'],
            rtp_git_hash=hera_opm_version_info['git_hash'],
            hera_qm_git_version=hera_qm_version_info['version'],
            hera_qm_git_hash=hera_qm_version_info['git_hash'],
            hera_cal_git_version=hera_cal_version_info['version'],
            hera_cal_git_hash=hera_cal_version_info['git_hash'],
            pyuvdata_git_version=pyuvdata_version_info['version'],
            pyuvdata_git_hash=pyuvdata_version_info['git_hash']

        )
