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
from astropy.time import Time, TimeDelta
import numpy as np
import redis


from hera_mc import autocorrelations, mc


def test_redis_connection(rsession, redispool, max_tries=3):
    redis_count = 0
    while redis_count <= max_tries:
        try:
            rsession.ping()
            # got a good connection return to the monitor
            return rsession
        except redis.exceptions.ConnectionError:
            print("Redis connection not found, attempting to reconnect.")
            rsession = redis.Redis(connection_pool=redis_pool)
            redis_count += 1
            if redis_count == max_tries:
                raise


# Preliminaries.
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

            rsession = test_redis_connection(rsession, redis_pool)

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
                    pols.append(pol)
            ants = np.unique(ants)
            pols = np.unique(pols)

            now = Time.now()
            auto_time = Time(
                np.frombuffer(rsession.get("auto:timestamp"), dtype=np.float64).item(),
                format="jd",
            )

            if abs(now - auto_time) >= TimeDelta(300, format='sec'):
                print(
                    "Autocorrelations are at least 5 minutes old, "
                    "or from the future, adding values as None."
                )
                autos_none = True
            else:
                autos_none = False

            for ant in ants:
                for pol in pols:

                    auto = rsession.get("auto:{ant:d}{pol:s}".format(ant=ant, pol=pol))
                    # For now, we just compute the median:

                    if autos_none or auto is None:
                        auto = None
                    else:
                        # copy the value because frombuffer returns immutable type
                        auto = np.frombuffer(auto, dtype=np.float32).copy()
                        auto = np.median(auto).item()

                    if args.debug:

                        ac = autocorrelations.HeraAuto.create(
                            time=auto_time,
                            antenna_number=ant,
                            antenna_feed_pol=pol,
                            measurement_type="median",
                            value=auto
                        )
                        print(auto.shape, ac)
                    if not args.noop:

                        dbsession.add_autocorrelation(
                            time=auto_time,
                            antenna_number=ant,
                            antenna_feed_pol=pol,
                            measurement_type="median",
                            value=auto
                        )

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
