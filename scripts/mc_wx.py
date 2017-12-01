#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for weather

"""
from __future__ import absolute_import, division, print_function

from hera_mc import cm_utils, weather, mc

wx_options = ['wind_speed', 'wind_gust', 'wind_direction', 'temperature', 'humidity', 'temperature', 'rain']
if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-v', '--variables', help="Part number, csv-list (required). [None]",
                        choices=wx_options, default='temperature')
    parser.add_argument('--start-date', dest='start_date', help="Start date YYYY/MM/DD", default=None)
    parser.add_argument('--start-time', dest='start_time', help="Start time in HH:MM", default='17:00')
    parser.add_argument('--stop-date', dest='stop_date', help="Stop date YYYY/MM/DD", default=None)
    parser.add_argument('--stop-time', dest='stop_time', help="Stop time in HH:MM", default='7:00')

    args = parser.parse_args()

    variables = cm_utils.listify(args.variables)
    start_time = cm_utils.get_astropytime(args.start_date, args.start_time)
    stop_time = cm_utils.get_astropytime(args.stop_date, args.stop_time)

    wx = weather.create_from_sensors(start_time, stop_time, variables)
    for w in wx:
        print(w.time, w.value)
