#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Gather correlator status info and log them into M&C"""

import socket
import sys
import time
import traceback

from astropy.time import Time

from hera_mc import mc

MONITORING_INTERVAL = 60  # seconds

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

hostname = socket.gethostname()

# List of commands (methods) to run on each iteration
commands_to_run = [
    "add_array_signal_source_from_redis",
    "add_correlator_component_event_time_from_redis",
    "add_correlator_catcher_file_from_redis",
    "add_correlator_file_queues_from_redis",
    "update_correlator_file_eod_from_redis",
    "add_correlator_config_from_corrcm",
    "add_snap_status_from_corrcm",
    "add_snap_feng_init_status_from_redis",
    "add_corr_snap_versions_from_corrcm",
    "add_antenna_status_from_corrcm",
    "add_autocorrelations_from_redis",
]

while True:
    try:
        # Use a single session unless there's an error that isn't fixed by a
        # rollback.
        with db.sessionmaker() as session:
            while True:
                time.sleep(MONITORING_INTERVAL)

                for command in commands_to_run:
                    try:
                        getattr(session, command)()
                        session.commit()
                        session.add_daemon_status(
                            "mc_monitor_correlator", hostname, Time.now(), "good"
                        )
                        session.commit()
                    except Exception:
                        print(
                            "{t} -- error calling command {c}".format(
                                t=time.asctime(), c=command
                            ),
                            file=sys.stderr,
                        )
                        traceback.print_exc(file=sys.stderr)
                        traceback_str = traceback.format_exc()
                        session.rollback()
                        try:
                            # try to update the daemon_status table and add an
                            # error message to the subsystem_error table
                            session.add_daemon_status(
                                "mc_monitor_correlator", hostname, Time.now(), "errored"
                            )
                            session.add_subsystem_error(
                                Time.now(), "mc_correlator_monitor", 2, traceback_str
                            )
                        except Exception as e:
                            # if we can't log error messages to the session,
                            # need a new session
                            raise RuntimeError(
                                "error logging to subsystem_error table after "
                                "command" + command
                            ) from e
                        continue
    except Exception:
        # Try to log an error with a new session
        traceback.print_exc(file=sys.stderr)
        traceback_str = traceback.format_exc()
        with db.sessionmaker() as new_session:
            try:
                # try to update the daemon_status table and add an
                # error message to the subsystem_error table
                new_session.add_daemon_status(
                    "mc_monitor_correlator", hostname, Time.now(), "errored"
                )
                new_session.add_subsystem_error(
                    Time.now(), "mc_correlator_monitor", 2, traceback_str
                )
            except Exception as e:
                # if we can't log error messages to the new session we're in real trouble
                raise RuntimeError(
                    "error logging to subsystem_error with a new session"
                ) from e
        # logging with a new session worked, so restart to get a new session
        continue
