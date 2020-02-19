# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Methods for handling locating correlator and various system aspects."""

from __future__ import absolute_import, division, print_function

import json
import redis
import time
import six
from . import cm_sysutils
from .correlator import DEFAULT_REDIS_ADDRESS

REDIS_CORR_HASH = 'corr:map'


def snap_part_to_host_input(part, redis_info=None):
    """
    Parse a part string for the putative hostname and adc number.

    If a redis session is supplied and key available it returns the hostname, otherwise
    it returns the SNAP name.  If None, returns the SNAP name.  An example part is
    'e2>SNPC000008'

    Parameters
    ----------
    part : str
        port>snap part string as returned by cminfo
    redis_info : None or dict
        If dict and the key is available it returns the hostname, otherwise SNAP name
        If None, returns the SNAP name

    Returns
    -------
    hostname : str
        hostname as parsed from input 'part' and redis
    adc_num : str
        port ADC number, as parsed from input 'part'
    """
    adc, name = part.split('>')
    adc_num = int(adc[1:]) // 2  # divide by 2 because ADC is in demux 2
    if redis_info is None:
        hostname = name
    else:
        _x = redis_info['rsession'].hget(redis_info['rhash'], redis_info['rkey'])
        if _x is None:
            hostname = name
        else:
            try:
                hostname = json.loads(_x)[name]
            except KeyError:
                hostname = name
    return hostname, adc_num


def cminfo_redis_snap(cminfo, redis_info=None):
    """
    Build a dictionary of correlator mappings.

    Use hera_mc's get_cminfo_correlator method to build a dictionary
    of correlator mappings for redis insertion.

    Parameters
    ----------
    cminfo : dict
        Dictionary as returned from get_cminfo_correlator()
    redis_info : None or dict
        Pass through of redis information to retrieve snap hostname

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
    for antn, ant in enumerate(cminfo['antenna_numbers']):
        name = cminfo['antenna_names'][antn]
        pol_info = {}
        for pol_snap in cminfo['correlator_inputs'][antn]:
            pol = pol_snap.lower()[0]
            if pol in ['e', 'n'] and '>' in pol_snap:
                pol_info[pol] = pol_snap
        ant_to_snap[ant] = {}
        for pol, psnap in six.iteritems(pol_info):
            snapi, channel = snap_part_to_host_input(psnap, redis_info=redis_info)
            ant_to_snap[ant][pol] = {'host': snapi, 'channel': channel}
            snap_to_ant.setdefault(snapi, [None] * 6)
            snap_to_ant[snapi][channel] = name + pol.upper()
            snap, adc_num = snap_part_to_host_input(psnap, None)
            all_snap_inputs.setdefault(snap, [])
            all_snap_inputs[snap].append(adc_num)
    for key, value in all_snap_inputs.items():
        all_snap_inputs[key] = sorted(value)
    return snap_to_ant, ant_to_snap, all_snap_inputs


def cminfo_redis_loc(cminfo):
    """
    Places the positional data into redis for use by the correlator.

    Parameter
    ---------
    cminfo : dict
        Dictionary as returned from get_cminfo_correlator()

    Returns
    -------
    ant_pos : dict
        Dictionary containing the ECEF positions of all of the antennas.
    cofa : dict
        Dictionary containing the lat, lon, alt of the center-of-array
    """
    locations = {}
    locations['antenna_numbers'] = cminfo['antenna_numbers']
    locations['antenna_names'] = cminfo['antenna_names']
    antenna_positions = []
    for _x in cminfo['antenna_positions']:
        antenna_positions.append(list(_x))
    locations['antenna_positions'] = antenna_positions
    locations['antenna_utm_eastings'] = cminfo['antenna_utm_eastings']
    locations['antenna_utm_northings'] = cminfo['antenna_utm_northings']
    locations['antenna_alts'] = cminfo['antenna_alt']
    locations['cofa'] = {'lat': cminfo['cofa_lat'], 'lon': cminfo['cofa_lon'],
                         'alt': cminfo['cofa_alt']}
    locations['cofa_xyz'] = {'X': cminfo['cofa_X'], 'Y': cminfo['cofa_Y'],
                             'Z': cminfo['cofa_Z']}
    return locations


def set_redis_cminfo(redishost=DEFAULT_REDIS_ADDRESS, session=None, testing=False):
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
    h = cm_sysutils.Handling(session=session)
    cminfo = h.get_cminfo_correlator()

    # This is retained so that explicitly providing redishost=None has the desired behavior
    if redishost is None:  # pragma: no cover
        redishost = DEFAULT_REDIS_ADDRESS
    redis_pool = redis.ConnectionPool(host=redishost)
    rsession = redis.Redis(connection_pool=redis_pool)
    redis_hash = REDIS_CORR_HASH
    if testing:
        redis_hash = 'testing_' + REDIS_CORR_HASH
    redis_info = {'rsession': rsession, 'rhash': redis_hash, 'rkey': 'snap_host'}
    snap_to_ant, ant_to_snap, all_snap_inputs = cminfo_redis_snap(cminfo, redis_info=redis_info)
    locations = cminfo_redis_loc(cminfo)
    redhkey = {}
    for key, value in six.iteritems(locations):
        redhkey[key] = json.dumps(value)
    redhkey['snap_to_ant'] = json.dumps(snap_to_ant)
    redhkey['ant_to_snap'] = json.dumps(ant_to_snap)
    redhkey['all_snap_inputs'] = json.dumps(all_snap_inputs)
    redhkey['update_time'] = time.time()
    redhkey['update_time_str'] = time.ctime(redhkey['update_time'])
    redhkey['cm_version'] = cminfo['cm_version']

    rsession.hmset(redis_hash, redhkey)
    if testing:
        redis_hash = 'testing_' + REDIS_CORR_HASH  # this is here to avert potential disaster
        rsession.expire(redis_hash, 300)
