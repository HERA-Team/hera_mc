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


def snap_part_to_host_input(part):
    """
    Given a part string, eg. 'e2>SNPC000008', return the hostname and adc number
    """
    print(part)
    adc, name = part.split('>')
    # convert the string adc (eg "e2") into a channel number 0-2
    adc_num = int(adc[1:]) // 2  # divide by 2 because ADC is in demux 2
    # convert the name into something which should be a hostname.
    # name has the form SNPA0000123. Hostnames have the form herasnapA123
    # Edit 16 Sep 2019 -- This isn't true anymore. CM names and hostnames are now the same
    hostname = name  # "herasnap%s" % (name[3] + name[4:].lstrip('0'))
    # try:
    #     true_name, aliases, addresses = socket.gethostbyaddr(hostname)
    # except:
    #     logger.error('Failed to gethostbyname for host %s' % hostname)
    # assume that the one we want is the last thing in the hosts file line
    # return aliases[-1], adc_num
    return hostname, adc_num


def cminfo_redis():
    """
    Use hera_mc's get_cminfo_correlator method to build a dictionary
    of correlator mappings and antenna positions
    """
    h = cm_sysutils.Handling()
    cminfo = h.get_cminfo_correlator()
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
            snapi_e, channel_e = snap_part_to_host_input(cminfo['correlator_inputs'][antn][0])
            ant_to_snap[ant]['e'] = {'host': snapi_e, 'channel': channel_e}
            if snapi_e not in snap_to_ant.keys():
                snap_to_ant[snapi_e] = [None] * 6
            snap_to_ant[snapi_e][channel_e] = name + 'E'
        if n_pol != 'None':
            snapi_n, channel_n = snap_part_to_host_input(cminfo['correlator_inputs'][antn][1])
            ant_to_snap[ant]['n'] = {'host': snapi_n, 'channel': channel_n}
            if snapi_n not in snap_to_ant.keys():
                snap_to_ant[snapi_n] = [None] * 6
            snap_to_ant[snapi_n][channel_n] = name + 'N'
    return snap_to_ant, ant_to_snap


def set_redis_cminfo(redishost=None):
    """
    Gets the configuration management information and writes to the
    redis database for the correlator.

    Parameters
    ----------
    redishost : str
        Hostname for the redis database
    """
    if redishost is None:
        redishost = DEFAULT_REDIS_ADDRESS
    snap_to_ant, ant_to_snap = cminfo_redis()
    redhash = {'snap_to_ant': json.dumps(snap_to_ant), 'ant_to_snap': json.dumps(ant_to_snap)}
    redhash['update_time'] = time.time()
    redhash['update_time_str'] = time.ctime(redhash['update_time'])

    redis_pool = redis.ConnectionPool(host=redishost)
    rsession = redis.Redis(connection_pool=redis_pool)
    rsession.hmset('corr:map', redhash)
