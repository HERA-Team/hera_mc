#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for weather

"""
from __future__ import absolute_import, division, print_function

from hera_mc import cm_utils, mc

wx_options = ['wind_speed', 'wind_gust', 'wind_direction', 'humidity', 'pressure', 'temperature', 'rain']
if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-v', '--variables', help="Variables csv-list. [all]", choices=wx_options, default='all')
    parser.add_argument('--start-date', dest='start_date', help="Start date YYYY/MM/DD", default=None)
    parser.add_argument('--start-time', dest='start_time', help="Start time in HH:MM", default='17:00')
    parser.add_argument('--stop-date', dest='stop_date', help="Stop date YYYY/MM/DD", default=None)
    parser.add_argument('--stop-time', dest='stop_time', help="Stop time in HH:MM", default='7:00')
    parser.add_argument('--add-to-db', dest='add_to_db', help="Flag to only print data to screen", action='store_true')
    parser.add_argument('-l', '--last-period', dest='last_period', default=None,
                        help="Time period into past to produce (in minutes).  If present ignore start/stop.")

    args = parser.parse_args()

    if args.variables.lower() == 'all':
        variables = wx_options
    else:
        variables = cm_utils.listify(args.variables)
    if args.last_period:
        from astropy.time import Time
        from astropy.time import TimeDelta
        stop_time = Time.now()
        start_time = stop_time - TimeDelta(float(args.last_period) / 24.0, format='jd')
    else:
        start_time = cm_utils.get_astropytime(args.start_date, args.start_time)
        stop_time = cm_utils.get_astropytime(args.stop_date, args.stop_time)

    if isinstance(start_time, Time) and isinstand(stop_time, Time):
        if args.add_to_db:
            db = mc.connect_to_mc_db(args)
            session = db.sessionmaker()
            session.add_weather_data_from_sensors(start_time, stop_time, variables)
        else:
            import weather
            wx = weather.create_from_sensor(start_time, stop_time, variables)
            for w in wx:
                displayTime = cm_utils.get_displayTime(w.time)
                print("{}: {} ({}) -- {}".format(w.variable, w.time, displayTime, w.time, w.value))
    else:
        print("Need valid start/stop times - or can specify last-period.")
