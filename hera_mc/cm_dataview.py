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

    def ants_by_day(self, start, stop, time_step, output=None, station_types_to_check='default', output_date_format='jd'):
        """
        Return dated list of connected stations.

        Parameters:
        ------------
        start:  start (astropy.Time)
        stop:  stop (astropy.Time)
        time_step:  time_step in days between start/stop (float or int)
        output:  Optional filename to write (and shows on screen).  If None, only returns dictionary.
        station_types_to_check:  e.g. HH, default used hookup cache set (HH, HA, HB currently)
        output_date_format: jd or ymd
        """
        if output is None:
            fplist = []
            data_ret = {}
        else:
            import sys
            fplist = [sys.stdout, open(output, 'w')]
            data_ret = None
        sys_handle = sys_handling.Handling(self.session)
        time_step = TimeDelta(time_step * 3600.0 * 24.0, format='sec')
        at_date = start
        while at_date <= stop:
            stn_info_list = sys_handle.get_all_fully_connected_at_date(at_date, station_types_to_check=station_types_to_check)
            y = [x.station_name for x in stn_info_list]
            s = ', '.join(y)
            s.strip().strip(',')
            if output_date_format == 'jd':
                printable_date = at_date.jd
            else:
                printable_date = cm_utils.get_time_for_display(at_date)
            for fp in fplist:
                print("{}:  {}".format(printable_date, s), file=fp)
            if data_ret is not None:
                data_ret[printable_date] = y
            at_date += time_step
        if data_ret is not None:
            return data_ret
