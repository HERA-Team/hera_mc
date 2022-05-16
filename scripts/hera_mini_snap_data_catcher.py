#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2022 the HERA Collaboration
# Licensed under the 2-clause BSD license.
"""Accumulate SNAP spectra from redis and write to a UVH5 file."""
import time
import socket
import logging
import argparse
import traceback

import numpy as np
from pyuvdata import UVData
from pyuvdata import utils as uvutils

# from astropy import units
from astropy.time import Time, TimeDelta

from hera_corr_cm import HeraCorrCM
from hera_corr_cm.redis_cm import read_maps_from_redis, read_cminfo_from_redis


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s - %(funcName)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__file__)

hostname = socket.gethostname()


def get_blt_index(antnum, time, ant_array, time_array):
    indices = np.nonzero(np.asarray(ant_array) == antnum)[0]

    if indices.size != 0:
        sub_inds = np.nonzero(np.asarray(time_array)[indices] == time)[0]
        if sub_inds.size != 0:
            return indices[sub_inds]
        else:
            return None
    else:
        return None


parser = argparse.ArgumentParser(
    description="Create UVH5 file from snap autocorrelations in Redis.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "-r",
    dest="redishost",
    type=str,
    default="redishost",
    help="Host servicing redis requests",
)
parser.add_argument(
    "--max_downtime",
    dest="max_downtime",
    type=float,
    default=60.0,
    help="Seconds between to wait between redis updates before restarting with new file.",
)

parser.add_argument(
    "--max_file_len",
    dest="max_file_len",
    type=float,
    default=60.0,
    help=(
        "Maximum length of a UVH5 file in seconds. "
        "This is the total time between the first and last entry in the time_array."
    ),
)

args = parser.parse_args()

logger.info("Starting HERA snap mini data catcher.")
while True:
    try:
        corr_cm = HeraCorrCM(redishost=args.redishost)
        logger.info("HERA CorrCM Redis connection established.")

        mapping = read_maps_from_redis()
        snap_to_ant_mapping = mapping["snap_to_ant"]
        if mapping is None:
            raise ValueError(
                "None value encountered for antenna/snap mappings in redis."
            )

        last_time_mapping = {}

        logger.info("Beginning data catching.")
        while True:
            try:

                # use future_array_shapes
                # Nblts, Nfreqs, Npols
                # a little rough but we don't necessarily know how many freqs we'll have.
                # it is most likely 1024 but this will guard against X-Engine changes.
                data_array = None
                # Nblts
                time_array = []
                ant_array = []

                downtime = 0
                file_len = 0

                while downtime < args.max_downtime and file_len < args.max_file_len:
                    time.sleep(0.01)
                    # do the thing
                    # get integrations from HeraCorrCM.get_snaprf_status()
                    # compare to the last time for each snap

                    for (
                        snap_hostname,
                        status,
                    ) in corr_cm.get_snaprf_status().items():

                        if status["timestamp"] is None or status["timestamp"] == "None":
                            continue

                        snap, stream = snap_hostname.split(":")
                        stream = int(stream)

                        hera_ant_num = snap_to_ant_mapping[snap][stream]
                        if hera_ant_num is None:
                            continue

                        # arbitrarily assign east as polarization 0
                        pol = hera_ant_num[-1].lower()
                        pol_ind = 0 if pol == "e" else 1

                        # trim off the HH and the Polarization
                        hera_ant_num = int(hera_ant_num[2:-1])

                        timestamp = Time(status["timestamp"]).jd

                        if snap_hostname not in last_time_mapping:
                            last_time_mapping[snap_hostname] = timestamp
                        else:
                            if timestamp <= last_time_mapping[snap_hostname]:
                                # Time has not progressed yet.
                                # Just sit tight
                                continue

                        auto_corr = status["autocorrelation"]

                        if data_array is None:
                            data_array = np.zeros(
                                (0, auto_corr.shape[0], 2), dtype=np.float32
                            )
                        data_index = get_blt_index(
                            hera_ant_num, timestamp, ant_array, time_array
                        )
                        if data_index is not None:
                            # this baseline is already in the time array
                            # insert into the correct polarization
                            # at the given index
                            data_array[data_index, :, pol_ind] = auto_corr

                        else:
                            # otherwise append the data array and insert the meta-data
                            data_insert = np.zeros(
                                (1, auto_corr.shape[0], 2), dtype=np.float32
                            )
                            data_insert[..., pol_ind] = auto_corr

                            data_array = np.append(data_array, data_insert, axis=0)
                            time_array.append(timestamp)
                            ant_array.append(hera_ant_num)

                    last_time = max(last_time_mapping.values())
                    downtime = (Time.now() - Time(last_time, format="jd")).to_value("s")
                    if len(time_array) > 0:
                        file_len = TimeDelta(
                            time_array[-1] - time_array[0], format="jd"
                        ).to_value("s")

                time_array = np.asarray(time_array)
                if time_array.size == 0:
                    # No Data was taken
                    logger.info(
                        f"Downtime Timeout. No New Data recieved since {last_time}."
                    )
                    continue

                ant_array = np.asarray(ant_array)

                uvd = UVData()

                # let's us not have to Spectral windows
                uvd._set_future_array_shapes()

                uvd.data_array = data_array.astype(np.complex64)
                uvd.vis_units = "UNCALIB"
                uvd.time_array = time_array

                uvd.Nblts = time_array.shape[0]
                uvd.Ntimes = np.unique(uvd.time_array).size

                uvd.Nfreqs = data_array.shape[1]
                uvd.freq_array = np.linspace(0, 256, uvd.Nfreqs) * 1e6

                uvd.channel_width = np.full_like(
                    uvd.freq_array, np.diff(uvd.freq_array)[0]
                )
                uvd.Nants_data = np.unique(ant_array).size
                uvd.Nbls = uvd.Nants_data
                uvd.Nspws = 1
                uvd.Npols = 2

                uvd.ant_1_array = ant_array
                uvd.ant_2_array = ant_array
                uvd.baseline_array = uvd.antnums_to_baseline(
                    uvd.ant_1_array, uvd.ant_2_array
                )

                uvd.nsample_array = np.ones_like(uvd.data_array, np.float32)
                uvd.integration_time = np.ones((uvd.Nblts), np.float32)
                uvd.flag_array = np.zeros_like(uvd.data_array, dtype=bool)
                uvd.x_orientation = "north"
                uvd.Nants_data = len(set(ant_array))
                uvd.polarization_array = uvutils.polstr2num(
                    ["ee", "nn"], x_orientation=uvd.x_orientation
                )
                uvd.spw_array = np.array([0])

                cminfo = read_cminfo_from_redis(return_as="dict")

                uvd.antenna_positions = np.asarray(cminfo["antenna_positions"])
                uvd.antenna_names = np.asarray(cminfo["antenna_names"])
                uvd.antenna_numbers = np.asarray(cminfo["antenna_numbers"])
                uvd.Nants_telescope = len(uvd.antenna_numbers)
                lat, lon, alt = (
                    cminfo["cofa_lat"],
                    cminfo["cofa_lon"],
                    cminfo["cofa_alt"],
                )
                uvd.telescope_location_lat_lon_alt_degrees = (lat, lon, alt)
                uvd.set_uvws_from_antenna_positions()
                uvd.set_lsts_from_time_array()

                uvd.object_name = ""
                uvd.multi_phase_center = False
                uvd.telescope_name = "HERA"
                uvd.instrument = "HERA"
                uvd.history = f"Created by {__file__}."
                uvd.phase_type = "drift"

                uvd.reorder_blts("time", "baseline")
                fname = f"zen.{Time.now().jd:.6f}.snap_autos.uvh5"
                logger.info(f"Writing output file {fname}.")
                uvd.write_uvh5(fname)

            except Exception:
                logger.error(
                    "{t} -- error while accumulating datafile".format(t=time.asctime()),
                )
                logger.error(traceback.print_exc())
                continue

    except Exception:
        logger.error(traceback.print_exc())
        continue
