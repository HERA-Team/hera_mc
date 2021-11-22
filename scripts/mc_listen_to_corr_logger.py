#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Gather correlator log outputs and log them into M&C."""

import sys
import json
import redis
import socket
import logging

from astropy.time import Time

from hera_mc import mc
from hera_mc.correlator import DEFAULT_REDIS_ADDRESS


allowed_levels = ["DEBUG", "INFO", "NOTIFY", "WARNING", "ERROR", "CRITICAL"]
logging.addLevelName(logging.INFO + 1, "NOTIFY")

parser = mc.get_mc_argument_parser()
parser.add_argument(
    "--redishost",
    "-r",
    dest="redishost",
    default=DEFAULT_REDIS_ADDRESS,
    help="The redis db hostname",
)

parser.add_argument(
    "--channel",
    "-c",
    dest="channel",
    default="mc-log-channel",
    help="The redis channel to listen on.",
)

parser.add_argument(
    "-l",
    dest="level",
    type=str,
    default="NOTIFY",
    help=(
        "Don't log messages below this level. "
        "Allowed values are {vals:}".format(vals=allowed_levels)
    ),
    choices=allowed_levels,
)

args = parser.parse_args()
db = mc.connect_to_mc_db(args)

hostname = socket.gethostname()
redis_pool = redis.ConnectionPool(host=args.redishost)

level = logging.getLevelName(args.level)

while True:
    try:
        with db.sessionmaker() as session, redis.Redis(
            connection_pool=redis_pool
        ) as redis_db:
            pubsub = redis_db.pubsub()
            pubsub.ignore_subscribe_messages = True

            pubsub.subscribe(args.channel)
            # pubsub.listen() will create an infinite generator
            # that yields messages in our channel
            for message in pubsub.listen():
                if (
                    message["data"].decode()
                    != "UnicodeDecodeError on emit!"
                    # messages come as byte strings, make sure an error didn't occur
                ):
                    message_dict = json.loads(message["data"])

                    msg_level = message_dict["levelno"]
                    if msg_level >= level:
                        session.add_subsystem_error(
                            Time(message_dict["logtime"], format="unix"),
                            message_dict["subsystem"],
                            message_dict["severity"],
                            message_dict["message"],
                        )

                    session.add_daemon_status(
                        "mc_listen_to_corr_logger", hostname, Time.now(), "good"
                    )
                    session.commit()
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        # some common exceptions are this Nonetype being yielded by the iterator
        # and a forcible connection closure by the server.
        # Ignore for now and re-attach to the pubsub channel
        if not any(
            str(e).startswith(err)
            for err in [
                "'NoneType' object has no attribute 'readline'",
                "Connection closed by server.",
            ]
        ):
            print(e)
            session.add_daemon_status(
                "mc_listen_to_corr_logger", hostname, Time.now(), "errored"
            )
            session.commit()
        continue
