#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Allows some different data views of cm database.
"""

from __future__ import absolute_import, division, print_function

from astropy.time import Time, TimeDelta
import numpy as np

from . import mc, cm_utils, cm_revisions, sys_handling


class Dataview:
    def __init__(self, session=None):
        """
        session: session on current database. If session is None, a new session
                 on the default database is created and used.
        """
        if session is None:
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session

    def ants_by_day(self, start, stop, interval, filename, station_types_to_check='default', output_date_format='jd'):
        """
        Return dated list of connected stations.

        Parameters:
        ------------
        start:  start astropy.Time
        stop:  stop astropy.Time
        interval:  interval in days
        filename:  filename to write to.  If stdout it will also return a dictionary
        station_types_to_check:  e.g. HH
        output_date_format: jd or ymd
        """
        if filename.lower() == 'stdout':
            import sys
            fp = sys.stdout
            data_ret = {}
        else:
            fp = open(filename, 'w')
            data_ret = None
        sys_handle = sys_handling.Handling(self.session)
        interval = TimeDelta(interval * 3600.0 * 24.0, format='sec')
        at_date = start
        while at_date < stop:
            stn_info_list = sys_handle.get_all_fully_connected_at_date(at_date, station_types_to_check='default')
            y = [x.station_name for x in stn_info_list]
            s = ', '.join(y)
            s.strip().strip(',')
            if output_date_format == 'jd':
                printable_date = at_date.jd
            else:
                printable_date = cm_utils.get_time_for_display(at_date)
            print("{}:  {}".format(printable_date, s), file=fp)
            if data_ret is not None:
                data_ret[printable_date] = y
            at_date += interval
        if data_ret is not None:
            return data_ret
