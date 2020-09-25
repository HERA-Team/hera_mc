#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Prints Time info for given date/time.  This is being deprecated for mc_clock.py

"""
from astropy.time import Time
import warnings

from hera_mc import mc, cm_utils

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-g', '--gps', help="Convert from gps seconds to time.", default=None)
    cm_utils.add_date_time_args(parser)
    args = parser.parse_args()

warn_msg = "mc_gps.py is deprecated in favor of mc_clock.py "\
           "- mc_gps.py will be retained until January 2021"
warnings.warn(warn_msg, DeprecationWarning)

if args.gps is None:
    Time_object = cm_utils.get_astropytime(args.date, args.time)
    print("\n\tThe supplied date was  {}".format(str(Time_object)))
    print("\t...corresponding gps is  {}\n".format(Time_object.gps))
    print("\tThe Julian Date is {}\n".format(Time_object.jd))
else:
    Time_object = Time(int(args.gps), format='gps')
    print("\n\tThe supplied gps second was {}".format(args.gps))
    print("\t...corresponding Time is {}".format(str(Time_object.isot)))
    print("\tThe Julian Date is {}\n".format(Time_object.jd))
