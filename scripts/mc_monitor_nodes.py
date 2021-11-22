#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Gather node sensor and power status info and log them into M&C

The values cycle out of the Redis store every minute, so cron can't
sample quickly enough (and starting a new process every minute feels like a
bit much).

"""

import sys
import time
import traceback
import socket

from astropy.time import Time

from hera_mc import mc

MONITORING_INTERVAL = 60  # seconds

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

hostname = socket.gethostname()

# List of commands (methods) to run on each iteration
commands_to_run = [
    "add_node_sensor_readings_from_node_control",
    "add_node_power_status_from_node_control",
    "add_node_power_command_from_node_control",
    "add_node_white_rabbit_status_from_node_control",
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
                            "mc_monitor_nodes", hostname, Time.now(), "good"
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
                                "mc_monitor_nodes", hostname, Time.now(), "errored"
                            )
                            session.add_subsystem_error(
                                Time.now(), "mc_node_monitor", 2, traceback_str
                            )
                        except Exception as e:
                            # if we can't log error messages to the session,
                            # need a new session
                            raise RuntimeError(
                                "error logging to subsystem_error "
                                "table after command" + command
                            ) from e
                        continue
    except Exception:
        # Try to log an error with a new session
        traceback.print_exc(file=sys.stderr)
        with db.sessionmaker() as new_session:
            try:
                # try to update the daemon_status table and add an
                # error message to the subsystem_error table
                session.add_daemon_status(
                    "mc_monitor_nodes", hostname, Time.now(), "errored"
                )
                session.add_subsystem_error(
                    Time.now(), "mc_node_monitor", 2, traceback_str
                )
            except Exception as e:
                # if we can't log error messages to the new session we're in real trouble
                raise RuntimeError(
                    "error logging to subsystem_error with a " "new session"
                ) from e
        # logging with a new session worked, so restart to get a new session
        continue
