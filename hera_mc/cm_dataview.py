#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Allows some different data views of cm database.
"""

from __future__ import absolute_import, division, print_function

from astropy.time import Time, TimeDelta
import numpy as np
import os.path
import sys

from . import mc, cm_utils, cm_revisions, cm_sysutils, geo_handling


def read_antennas():
    """
    Reads in all of the 350 antenna positions from HERA_350.txt under hera_mc/data

    Returns
    -------
    dictionary
        keyed on station name, with a list of E, N and elevation
    """
    antenna_coord_file_name = os.path.join(mc.data_path, 'HERA_350.txt')
    antennas = {}
    with open(antenna_coord_file_name, 'r') as fp:
        for line in fp:
            data = line.split()
            coords = [data[0], float(data[1]), float(data[2]), float(data[3])]
            antennas[coords[0]] = {'E': coords[1], 'N': coords[2], 'elevation': coords[3]}
    return antennas


class Dataview:
    def __init__(self, session=None):
        """
        session: session on current database. If session is None, a new session
                 on the default database is created and used.
        """
        if session is None:  # pragma: no cover
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session

    def connected_by_day(self, start, stop, time_step, output=None, station_types_to_check='default', output_date_format='jd', hookup_type='parts_hera'):
        """
        Finds "connected" antennas (ie. a full hookup from station to correlator) by stepping over times between start and stop at the given time_step.

        Parameters
        ----------
        start:  start (astropy.Time)
        stop:  stop (astropy.Time)
        time_step:  desired time_step resolution in days or fractions thereof (float or int)
        output:  Optional filename to write (and shows on screen).  If None, only returns dictionary.
        station_types_to_check:  e.g. HH, default used hookup cache set (HH, HA, HB currently)
        output_date_format: jd or ymd

        Returns
        -------
        dictionary
            keyed on date; contains the list of station names added
        """
        if output is None:
            fplist = []
        else:
            fplist = [sys.stdout, open(output, 'w')]
        data_ret = {}
        sys_handle = cm_sysutils.Handling(self.session)
        time_step = TimeDelta(time_step * 3600.0 * 24.0, format='sec')
        at_date = start
        while at_date <= stop:
            stn_info_list = sys_handle.get_all_fully_connected_at_date(at_date, station_types_to_check=station_types_to_check,
                                                                       hookup_type=hookup_type)
            y = [x.station_name for x in stn_info_list]
            s = ', '.join(y)
            if output_date_format == 'jd':
                printable_date = "{:04f}".format(at_date.jd)
            else:
                printable_date = cm_utils.get_time_for_display(at_date)
            data_ret[printable_date] = y
            for fp in fplist:
                print("{}:  {}  <{}>".format(printable_date, s, len(y)), file=fp)
            at_date += time_step
        return data_ret

    def ants_by_day(self, start, stop, time_step, output=None, output_date_format='jd'):
        """
        Finds "installed" antennas (established station-antenna connection) by stepping over times between start and stop at the given time_step.

        Parameters
        ----------
        start:  start (astropy.Time)
        stop:  stop (astropy.Time)
        time_step:  desired time_step resolution in days or fractions thereof (float or int)
        output:  Optional filename to write (and shows on screen).  If None, only returns dictionary.
        output_date_format: jd or ymd

        Returns
        -------
        dictionary
            keyed on date; contains the number of antennas installed on that date
        """
        if output is None:
            fplist = []
        else:
            fplist = [sys.stdout, open(output, 'w')]
        data_ret = {}
        G = geo_handling.Handling(self.session)
        ants_to_check = list(read_antennas().keys())
        time_step = TimeDelta(time_step * 3600.0 * 24.0, format='sec')
        at_date = start
        while at_date <= stop:
            if output_date_format == 'jd':
                printable_date = "{:.4f}".format(at_date.jd)
            else:
                printable_date = cm_utils.get_time_for_display(at_date)
            ctr = 0
            for a in ants_to_check:
                ants = G.find_antenna_at_station(a, at_date)
                if ants[0] is not None:
                    ctr += 1
            data_ret[printable_date] = ctr
            for fp in fplist:
                print("{} {}".format(printable_date, ctr), file=fp)
            at_date += time_step
        return data_ret
