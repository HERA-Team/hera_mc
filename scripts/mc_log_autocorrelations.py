#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Record information about antenna autocorrelations, as logged into the Redis
server by the correlator software.

"""
from __future__ import absolute_import, division, print_function

import datetime
import numpy as np
import redis
import sys

import six.moves as sm

from hera_mc import autocorrelations, mc


# Yay hardcoded config settings:

redis_host = 'redishost'

sm.range
antnums = sm.range(128)

# End of config.


parser = mc.get_mc_argument_parser()
parser.add_argument('--debug', action='store_true',
                    help='Print out debugging information.')
parser.add_argument('--noop', action='store_true',
                    help='Do not actually save information to the database.')
args = parser.parse_args()
db = mc.connect_to_mc_db(args)
n_failures = 0

with db.sessionmaker() as dbsession:
    rsession = redis.Redis(redis_host)

    # We put an identical timestamp for all records. The records from the
    # redis server also include timestamps (as JDs), but I think it's actually
    # preferable to use our own clock here. Note that we also ensure that the
    # records grabbed in one execution of this script have identical
    # timestamps, which is a nice property.
    time = datetime.datetime.utcnow()

    for ant in antnums:
        for pol in 'xy':
            try:
                data = rsession.hgetall('visdata://%d/%d/%s%s' % (ant, ant, pol, pol))
            except Exception as e:
                print('failed to get autocorrelation %d%s: %s (%s)' % (ant, pol, e, e.__class__.__name__),
                      file=sys.stderr)
                n_failures += 1
                continue

            data = data.get('data')
            if data is None:
                print('failed to get autocorrelation %d%s: no "data" item?' % (ant, pol),
                      file=sys.stderr)
                n_failures += 1
                continue

            data = np.fromstring(data, dtype=np.float32)

            # For now, we just compute the median:

            ac = autocorrelations.Autocorrelations()
            ac.time = time
            ac.antnum = ant
            ac.polarization = pol
            ac.measurement_type = autocorrelations.MeasurementTypes.median
            ac.value = np.asscalar(np.median(data))  # must turn np.float32 into plain Python float

            if args.debug:
                print(data.shape, repr(ac))
            if not args.noop:
                dbsession.add(ac)

if n_failures:
    print('error: %d fetches failed' % n_failures, file=sys.stderr)
    sys.exit(1)
