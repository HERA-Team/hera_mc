#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to show cm_log_file.  Extremely simplified here - can fancify later.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import cm_utils, mc
import sys
import os.path


if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    cm_utils.add_verbosity_args(parser)
    args = parser.parse_args()
    args.verbosity = args.verbosity.lower()

    with open(mc.cm_log_file, 'r') as log_file:
        for line in log_file:
            print(line.strip())
