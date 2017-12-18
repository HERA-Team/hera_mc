#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Gather temperatures from the correlator ROACH devices and log them into M&C

The temperatures cycle out of the Redis store every minute, so cron can't
sample quickly enough (and starting a new process every minute feels like a
bit much).

"""
from __future__ import absolute_import, division, print_function

import sqlalchemy.exc
import sys
import time
import traceback

from hera_mc import mc

MONITORING_INTERVAL = 45  # seconds

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

with db.sessionmaker() as session:
    try:
        while True:
            time.sleep(MONITORING_INTERVAL)

            try:
                session.add_roach_temperature_from_redis()
            except Exception as e:
                print('%s -- error adding ROACH temperatures' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.commit()
            except sqlalchemy.exc.SQLAlchemyError as e:
                print('%s -- SQL error committing new temperature data' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                session.rollback()
                continue
            except Exception as e:
                print('%s -- error committing new temperature data' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue
    except KeyboardInterrupt:
        pass
