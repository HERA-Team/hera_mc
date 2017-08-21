#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Prints Time info for given date/time

"""
from __future__ import absolute_import, division, print_function
from hera_mc import mc, cm_utils
from astropy.time import Time

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-g', '--gps', help="Convert from gps seconds to time.", default=None)
    cm_utils.add_date_time_args(parser)
    args = parser.parse_args()

if args.gps is None:
    Time_object = cm_utils._get_astropytime(args.date, args.time)
    print("\n\tThe supplied date was  {}".format(str(Time_object)))
    print("\t...corresponding gps is  {}\n".format(Time_object.gps))
else:
    Time_object = Time(int(args.gps), format='gps')
    print("\n\tThe supplied gps second was {}".format(args.gps))
    print("\t...corresponding Time is {}".format(str(Time_object.isot)))
