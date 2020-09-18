#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Prints Time info for given date/time with flexible format
"""

from hera_mc import cm_utils
import argparse


parser = argparse.ArgumentParser()
parser.add_argument(
    'date', help="Time in various formats:\n\t"
    "UTC YYYY/MM/DD\n\t</>\n\tnow\n\tgps\n\tjulian [now]", nargs='?',
    default='now')
parser.add_argument(
    'time', help="If UTC YMD, hh:mm or float (hours)", nargs='?', default=0.0)
args = parser.parse_args()

Time_object = cm_utils.get_astropytime(args.date, args.time)
print("\tDate    {}".format(str(Time_object.isot)))
print("\tgps     {}\n".format(Time_object.gps))
print("\tJulian  {}\n".format(Time_object.jd))
