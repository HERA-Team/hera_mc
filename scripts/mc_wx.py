#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for weather

"""
import sys
from astropy.time import Time

from hera_mc import cm_utils, mc

if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "-v",
        "--variables",
        help="Weather variable(s) in csv-list. Defaults to all.",
        default=None,
    )
    parser.add_argument(
        "--start-date", dest="start_date", help="Start date YYYY/MM/DD", default=None
    )
    parser.add_argument(
        "--start-time", dest="start_time", help="Start time in HH:MM", default="17:00"
    )
    parser.add_argument(
        "--stop-date", dest="stop_date", help="Stop date YYYY/MM/DD", default=None
    )
    parser.add_argument(
        "--stop-time", dest="stop_time", help="Stop time in HH:MM", default="7:00"
    )
    parser.add_argument(
        "--add-to-db",
        dest="add_to_db",
        help="Flag to actually write to database.",
        action="store_true",
    )
    parser.add_argument(
        "-l",
        "--last-period",
        dest="last_period",
        default=None,
        help="Time period from present for data (in minutes). "
        "If present ignores start/stop.",
    )

    args = parser.parse_args()

    variables = cm_utils.listify(args.variables)
    if args.last_period:
        from astropy.time import TimeDelta

        stop_time = Time.now()
        start_time = stop_time - TimeDelta(
            float(args.last_period) / (60.0 * 24.0), format="jd"
        )
    else:
        start_time = cm_utils.get_astropytime(args.start_date, args.start_time)
        stop_time = cm_utils.get_astropytime(args.stop_date, args.stop_time)

    if args.add_to_db:
        if not isinstance(start_time, Time) or not isinstance(stop_time, Time):
            print(
                "Need valid start/stop times - or can specify last-period.",
                file=sys.stderr,
            )
            sys.exit(1)

        db = mc.connect_to_mc_db(args)
        session = db.sessionmaker()
        session.add_weather_data_from_sensors(start_time, stop_time, variables)
        session.commit()
    else:
        from hera_mc import weather

        wx = weather.create_from_sensors(start_time, stop_time, variables)
        for w in wx:
            units = weather.weather_sensor_dict[w.variable]["units"]
            print(
                "{}: {} ({:.0f}) = {} {}".format(
                    w.variable,
                    cm_utils.get_time_for_display(w.time),
                    w.time,
                    w.value,
                    units,
                )
            )
