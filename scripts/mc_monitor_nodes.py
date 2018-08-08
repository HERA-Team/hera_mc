#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Gather node sensor and power status info and log them into M&C

The values cycle out of the Redis store every minute, so cron can't
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
                session.add_node_sensor_from_nodecontrol()
            except Exception as e:
                print('%s -- error adding node sensors' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.commit()
            except sqlalchemy.exc.SQLAlchemyError as e:
                print('%s -- SQL error committing new node sensor data' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                session.rollback()
                continue
            except Exception as e:
                print('%s -- error committing new node sensor data' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.add_node_power_status_from_nodecontrol()
            except Exception as e:
                print('%s -- error adding node power status' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.commit()
            except sqlalchemy.exc.SQLAlchemyError as e:
                print('%s -- SQL error committing new node power status' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                session.rollback()
                continue
            except Exception as e:
                print('%s -- error committing new node power status' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue
    except KeyboardInterrupt:
        pass
