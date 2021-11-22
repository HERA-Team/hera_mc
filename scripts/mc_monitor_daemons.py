#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Gather correlator status info for correlator daemons and log them into M&C."""

import sys
import os
import time
import redis
import traceback
import socket

from astropy.time import Time

from hera_mc import mc

MONITORING_INTERVAL = 60  # seconds

parser = mc.get_mc_argument_parser()
parser.add_argument(
    "-r",
    "--redishost",
    default="redishost",
    type=str,
    help="The redis server host address.",
)
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

hostname = socket.gethostname()
script_redis_key = "status:script:{host:s}:{file:s}".format(
    host=hostname, file=__file__
)

this_daemon = os.path.basename(__file__)

daemons = [
    this_daemon,
    "hera_corr_cmd_handler.py",  # hera_corr_cm
    "hera_wr_redis_monitor.py",  # hera_node_mc (moved from hera_wr_cm)
    "hera_node_keep_alive.py",  # hera_node_mc
    "hera_node_receiver.py",  # hera_node_mc
    "hera_snap_redis_monitor.py",  # hera_corr_f
    "hera_cmd_handler.py",  # hera_corr_f: SNAP command handler
]

connection_pool = redis.ConnectionPool(host=args.redishost)
while True:
    # Use a single session unless there's an error that isn't fixed by a rollback.
    try:
        with db.sessionmaker() as session, redis.Redis(
            connection_pool=connection_pool
        ) as r:
            while True:
                r.set(script_redis_key, "alive", ex=MONITORING_INTERVAL * 2)
                for daemon in daemons:
                    state = "errored"
                    for k in r.scan_iter(
                        "status:script:*:*{daemon:s}".format(daemon=daemon)
                    ):
                        host, daemon_path = k.decode().split(":")[2:]
                        state = "good"
                    try:
                        session.add_daemon_status(daemon, host, Time.now(), state)
                        session.commit()
                    except Exception:
                        print(
                            "{t} -- error storing daemon status".format(
                                t=time.asctime()
                            ),
                            file=sys.stderr,
                        )
                        traceback.print_exc(file=sys.stderr)
                        session.rollback()
                        continue
                time.sleep(MONITORING_INTERVAL)
    except KeyboardInterrupt:
        sys.exit()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        with db.sessionmaker() as session:
            session.add_daemon_status(this_daemon, hostname, Time.now(), "errored")
            session.commit()
        continue
