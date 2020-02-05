# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Methods for handling locating correlator and various system aspects.
"""

from __future__ import absolute_import, division, print_function

import json
import redis
import time
from . import cm_sysutils
from .correlator import DEFAULT_REDIS_ADDRESS


def snap_part_to_host_input(part, rsession=None):
    """
    Given a part string, eg. 'e2>SNPC000008', return the hostname and adc number
    """
    adc, name = part.split('>')
    adc_num = int(adc[1:]) // 2  # divide by 2 because ADC is in demux 2
    if rsession is None:
        hostname = name
    else:
        _x = rsession.hget('corr:map', 'snap_host')
        if _x is None:
            hostname = name
        else:
            hostname = json.loads(_x)[name]
    return hostname, adc_num


def cminfo_redis_snap(cminfo, rsession=None):
    """
    Use hera_mc's get_cminfo_correlator method to build a dictionary
    of correlator mappings
    """
    snap_to_ant = {}
    ant_to_snap = {}
    for antn, ant in enumerate(cminfo['antenna_numbers']):
        name = cminfo['antenna_names'][antn]
        for pol in cminfo['correlator_inputs'][antn]:
            if pol.startswith('e'):
                e_pol = pol
            if pol.startswith('n'):
                n_pol = pol
        ant_to_snap[ant] = {}
        if e_pol != 'None':
            snapi_e, channel_e = snap_part_to_host_input(cminfo['correlator_inputs'][antn][0],
                                                         rsession=rsession)
            ant_to_snap[ant]['e'] = {'host': snapi_e, 'channel': channel_e}
            if snapi_e not in snap_to_ant.keys():
                snap_to_ant[snapi_e] = [None] * 6
            snap_to_ant[snapi_e][channel_e] = name + 'E'
        if n_pol != 'None':
            snapi_n, channel_n = snap_part_to_host_input(cminfo['correlator_inputs'][antn][1],
                                                         rsession=rsession)
            ant_to_snap[ant]['n'] = {'host': snapi_n, 'channel': channel_n}
            if snapi_n not in snap_to_ant.keys():
                snap_to_ant[snapi_n] = [None] * 6
            snap_to_ant[snapi_n][channel_n] = name + 'N'
    return snap_to_ant, ant_to_snap


def cminfo_redis_loc(cminfo):
    ant_pos = {}
    for num, loc in zip(cminfo['antenna_numbers'], cminfo['antenna_positions']):
        ant_pos[num] = list(loc)
    cofa = {'lat': cminfo['cofa_lat'], 'lon': cminfo['cofa_lon'], 'alt': cminfo['cofa_alt']}
    return ant_pos, cofa


def set_redis_cminfo(redishost=None, session=None, testing=False):
    """
    Gets the configuration management information and writes to the
    redis database for the correlator.

    Parameters
    ----------
    redishost : str
        Hostname for the redis database
    """
    h = cm_sysutils.Handling(session=session)
    cminfo = h.get_cminfo_correlator()
    if testing:
        rsession = None
    else:
        if redishost is None:
            redishost = DEFAULT_REDIS_ADDRESS
        redis_pool = redis.ConnectionPool(host=redishost)
        rsession = redis.Redis(connection_pool=redis_pool)

    snap_to_ant, ant_to_snap = cminfo_redis_snap(cminfo, rsession=rsession)
    ant_pos, cofa = cminfo_redis_loc(cminfo)
    redhash = {}
    redhash['snap_to_ant'] = json.dumps(snap_to_ant)
    redhash['ant_to_snap'] = json.dumps(ant_to_snap)
    redhash['ant_pos'] = json.dumps(ant_pos)
    redhash['cofa'] = json.dumps(cofa)
    redhash['update_time'] = time.time()
    redhash['update_time_str'] = time.ctime(redhash['update_time'])
    redhash['cm_version'] = cminfo['cm_version']

    if testing:
        return redhash
    else:
        rsession.hmset('corr:map', redhash)
