#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Gather correlator status info and log them into M&C

"""
from __future__ import absolute_import, division, print_function

import sqlalchemy.exc
import sys
import time
import traceback

from hera_mc import mc

MONITORING_INTERVAL = 60  # seconds

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

with db.sessionmaker() as session:
    try:
        while True:
            time.sleep(MONITORING_INTERVAL)

            try:
                session.add_correlator_control_state_from_corrcm()
            except Exception as e:
                print('{t} -- error adding correlator control state'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue
            try:
                session.commit()
            except sqlalchemy.exc.SQLAlchemyError as e:
                print('{t} -- SQL error committing new correlator control state'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                session.rollback()
                continue
            except Exception as e:
                print('{t} -- error committing new correlator control state'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.add_correlator_config_from_corrcm()
            except Exception as e:
                print('{t} -- error adding correlator config'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue
            try:
                session.commit()
            except sqlalchemy.exc.SQLAlchemyError as e:
                print('{t} -- SQL error committing new correlator config'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                session.rollback()
                continue
            except Exception as e:
                print('{t} -- error committing new correlator config'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.add_snap_status_from_corrcm()
            except Exception as e:
                print('{t} -- error adding snap status'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.commit()
            except sqlalchemy.exc.SQLAlchemyError as e:
                print('{t} -- SQL error committing new snap status'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                session.rollback()
                continue
            except Exception as e:
                print('{t} -- error committing new snap status'.format(t=time.asctime()), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.add_antenna_status_from_corrcm()
            except Exception as e:
                print('%s -- error adding antenna status' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

            try:
                session.commit()
            except sqlalchemy.exc.SQLAlchemyError as e:
                print('%s -- SQL error committing new antenna status' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                session.rollback()
                continue
            except Exception as e:
                print('%s -- error committing new antenna status' % time.asctime(), file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                continue

    except KeyboardInterrupt:
        print("exiting on SIGINT")
        sys.exit()
