#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to check region(s) of a list of antenna(s).
"""

import argparse
from hera_mc import geo_sysdef

parser = argparse.ArgumentParser()
parser.add_argument("ants", help="Antenna or list of antennas.")
args = parser.parse_args()

args.ants = args.ants.split(",")
regions = geo_sysdef.ant_region(args.ants)

for this_ant, this_region in zip(args.ants, regions):
    print(f"{this_ant} --> {this_region}")
