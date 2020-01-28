#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Record information about antenna autocorrelations, as logged into the Redis
server by the correlator software.

"""
from __future__ import absolute_import, division, print_function

import sys
import time
import socket

from astropy.time import Time

from hera_mc import mc, utils

# Preliminaries. We have a small validity check since the M&C design specifies
# the memory, network, and system load are to be 5-minute averages.

MONITORING_INTERVAL = 60  # seconds
# End of config.

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

hostname = socket.gethostname()

while True:
    try:
        with db.sessionmaker() as session:
            while True:
                try:
                    time.sleep(MONITORING_INTERVAL)

                    session.add_autocorrelations_from_redis()
                    session.commit()
                    session.add_daemon_status(
                        "mc_log_autocorrelations",
                        hostname,
                        Time.now(),
                        "good"
                    )
                    session.commit()

                except Exception:
                    print(
                        "{t} -- error calling command {c}".format(
                            t=time.asctime(),
                            c="add_autocorrelations_from_redis"
                        ),
                        file=sys.stderr
                    )

                    session.rollback()
                    try:
                        session.add_daemon_status(
                            "mc_log_autocorrelations",
                            hostname,
                            Time.now(),
                            "errored"
                        )
                        session.commit()
                    except Exception:
                        utils._reraise_context(
                            "error logging daemon status after command '%r'",
                            "add_autocorrelations_from_redis"
                        )
                    continue
    except Exception:
        # Try to log an error with a new session
        with db.sessionmaker() as new_session:
            try:
                # try to update the daemon_status table and add an
                # error message to the subsystem_error table
                session.add_daemon_status(
                    "mc_log_autocorrelations",
                    hostname,
                    Time.now(),
                    "errored"
                )
            except Exception:
                # if we can't log error messages to the new session we're in
                # real trouble
                utils._reraise_context(
                    'error logging to daemon status with a new session')
        # logging with a new session worked, so restart to get a new session
        continue
