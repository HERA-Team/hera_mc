#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Prints Time info for given date/time

"""
from __future__ import absolute_import, division, print_function
from hera_mc import mc, cm_utils

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    cm_utils.add_date_time_args(parser)
    args = parser.parse_args()
    Time_object = cm_utils._get_astropytime(args.date,args.time)

    print("\n\tThe supplied date was  {}".format(str(Time_object)))
    print("\t...corresponding gps is  {}\n".format(Time_object.gps))
