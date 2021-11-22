#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Finds node for antenna numbers.
"""
import argparse
from hera_mc import cm_sysutils


parser = argparse.ArgumentParser()
parser.add_argument("ants", help="Antennas (csv-list).")
args = parser.parse_args()

ant_node = cm_sysutils.which_node(args.ants)
cm_sysutils.print_which_node(ant_node)
