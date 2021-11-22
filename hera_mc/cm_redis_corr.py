# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Methods for handling locating correlator and various system aspects."""

import json
import redis
import time
import warnings
from . import cm_sysutils, correlator

REDIS_CMINFO_HASH = "cminfo"
REDIS_CORR_HASH = "corr:map"


def cminfo_redis_snap(cminfo):
    """
    Build a dictionary of correlator mappings.

    Use hera_mc's get_cminfo_correlator method to build a dictionary
    of correlator mappings for redis insertion.

    Parameters
    ----------
    cminfo : dict
        Dictionary as returned from get_cminfo_correlator()

    Returns
    -------
    snap_to_ant : dict
        Dictionary mapping the snaps to the antennas
    ant_to_snap : dict
        Dictionary mapping each antenna to its snap
    """
    snap_to_ant = {}
    ant_to_snap = {}
    all_snap_inputs = {}
    snap_to_serial = {}
    for _n, ant in enumerate(cminfo["antenna_numbers"]):
        name = cminfo["antenna_names"][_n]
        corr_inp = cminfo["correlator_inputs"][_n]
        snap_snr = cminfo["snap_serial_numbers"][_n]
        ant_to_snap[ant] = {}
        for _i, psnap in enumerate(corr_inp):
            pol = psnap.lower()[0]
            if pol not in ["e", "n"] or ">" not in psnap:
                warnings.warn(f"{psnap} is not an allowed correlator input")
                continue
            snap_input, snap_hostname = psnap.split(">")
            channel = int(snap_input[1:]) // 2  # divide by 2 because ADC is in demux 2
            ant_to_snap[ant][pol] = {"host": snap_hostname, "channel": channel}
            snap_to_ant.setdefault(snap_hostname, [None] * 6)
            snap_to_ant[snap_hostname][channel] = name + pol.upper()
            all_snap_inputs.setdefault(snap_hostname, [])
            all_snap_inputs[snap_hostname].append(snap_input)
            try:  # if already present make sure it agrees
                if snap_to_serial[snap_hostname] != snap_snr[_i]:
                    msg = "Snap hostname-to-serial inconsistent:\n"
                    msg += (
                        "\tCurrent for antpol {}{} -> hostname={}, serial={}\n".format(
                            ant, pol, snap_hostname, snap_snr[_i]
                        )
                    )
                    msg += "\tStored -> hostname={}, serial={}".format(
                        snap_hostname, snap_to_serial[snap_hostname]
                    )
                    raise ValueError(msg)
            except KeyError:  # if not present, add it
                snap_to_serial[snap_hostname] = snap_snr[_i]

    for key, value in all_snap_inputs.items():
        all_snap_inputs[key] = sorted(value)
    return snap_to_ant, ant_to_snap, all_snap_inputs, snap_to_serial


def set_redis_cminfo(
    redishost=correlator.DEFAULT_REDIS_ADDRESS, session=None, testing=False
):
    """
    Write config info to redis database for the correlator.

    Parameters
    ----------
    redishost : None or str
        Hostname for the redis database.  If None uses default
    session : None or hera_mc session
        Session for hera_mc instance.  None uses default
    testing : bool
        If True, will use the testing_ hash in redis
    """
    # This is retained so that explicitly providing redishost=None has the desired behavior
    if redishost is None:  # pragma: no cover
        redishost = correlator.DEFAULT_REDIS_ADDRESS
    redis_pool = redis.ConnectionPool(host=redishost)
    rsession = redis.Redis(connection_pool=redis_pool)

    # Write cminfo content into redis (cminfo)
    h = cm_sysutils.Handling(session=session)
    cminfo = h.get_cminfo_correlator()
    redhkey = {}
    for key, value in cminfo.items():
        redhkey[key] = json.dumps(value)
    redis_hash = REDIS_CMINFO_HASH
    if testing:
        redis_hash = "testing_" + REDIS_CMINFO_HASH
    rsession.hset(redis_hash, mapping=redhkey)
    if testing:
        rsession.expire(redis_hash, 300)

    # Write correlator mappings to redis (corr:map)
    redis_hash = REDIS_CORR_HASH
    if testing:
        redis_hash = "testing_" + REDIS_CORR_HASH
    snap_to_ant, ant_to_snap, all_snap_inputs, snap_to_serial = cminfo_redis_snap(
        cminfo
    )
    redhkey = {}
    redhkey["snap_to_ant"] = json.dumps(snap_to_ant)
    redhkey["ant_to_snap"] = json.dumps(ant_to_snap)
    redhkey["all_snap_inputs"] = json.dumps(all_snap_inputs)
    redhkey["snap_to_serial"] = json.dumps(snap_to_serial)
    redhkey["update_time"] = time.time()
    redhkey["update_time_str"] = time.ctime(redhkey["update_time"])
    rsession.hset(redis_hash, mapping=redhkey)
    if testing:
        rsession.expire(redis_hash, 300)
