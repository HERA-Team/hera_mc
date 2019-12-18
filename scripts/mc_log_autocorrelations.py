#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Record information about antenna autocorrelations, as logged into the Redis
server by the correlator software.

"""
from __future__ import absolute_import, division, print_function

import socket
import time
from builtins import int

import re
import datetime
from astropy.time import Time
import numpy as np
import redis


from hera_mc import autocorrelations, mc


# Preliminaries. We have a small validity check since the M&C design specifies
# the memory, network, and system load are to be 5-minute averages.

MONITORING_INTERVAL = 60  # seconds
# End of config.


parser = mc.get_mc_argument_parser()
parser.add_argument("--redishost", "-r", default="redishost",
                    help="The hostname of the redis server.")
parser.add_argument('--redisport', '-p', default=6379,
                    help="Port for the redis server connection.")
parser.add_argument('--debug', action='store_true',
                    help='Print out debugging information.')
parser.add_argument('--noop', action='store_true',
                    help='Do not actually save information to the database.')
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

# allocate the maximum size of the autocorrelations as a buffer.
auto = np.zeros(8192, dtype=np.float32)

# make a redis pool and connect to redis
redis_pool = redis.ConnectionPool(host=args.redishost, port=args.redisport)
rsession = redis.Redis(connection_pool=redis_pool)

with db.sessionmaker() as dbsession:
    try:
        while True:
            hostname = socket.gethostname()
            keys = [
                k.decode("utf-8")
                for k in rsession.keys()
                if k.startswith(b"auto") and not k.endswith(b"timestamp")
            ]

            ants = []
            pols = []
            for key in keys:
                match = re.search(r"auto:(?P<ant>\d+)(?P<pol>e|n)", key)
                if match is not None:
                    ant, pol = int(match.group("ant")), match.group("pol")
                    ants.append(ant)
                    pols.append(pols)
            ants = np.unique(ants)
            pols = np.unique(ants)

            # We put an identical timestamp for all records. The records from the
            # redis server also include timestamps (as JDs), but I think it's actually
            # preferable to use our own clock here. Note that we also ensure that the
            # records grabbed in one execution of this script have identical
            # timestamps, which is a nice property.
            auto_time = datetime.datetime.utcnow()

            for ant in ants:
                for pol in pols:

                    d = rsession.get("auto:{ant:d}{pol:s}".format(ant=ant, pol=pol))
                    if d is not None:
                        auto = np.frombuffer(d, dtype=np.float32)

                        # For now, we just compute the median:

                        ac = autocorrelations.Autocorrelations()
                        ac.time = auto_time
                        ac.antnum = ant
                        ac.polarization = pol
                        ac.measurement_type = autocorrelations.MeasurementTypes.median
                        # must turn np.float32 into plain Python float
                        ac.value = np.median(auto).item()

                        if args.debug:
                            print(auto.shape, repr(ac))
                        if not args.noop:
                            dbsession.add(ac)

                            dbsession.add_daemon_status('mc_log_autocorrelations',
                                                        hostname, Time.now(), 'good')
                            dbsession.commit()

            time.sleep(MONITORING_INTERVAL)

    except KeyboardInterrupt:
        pass
    except Exception:
        dbsession.add_daemon_status('mc_log_autocorrelations',
                                    hostname, Time.now(), 'errored')
        dbsession.commit()
        raise
