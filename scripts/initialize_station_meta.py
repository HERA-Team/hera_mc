#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Onetime transfer of geo-locations of antennas into the M&C database.

"""
from __future__ import absolute_import, division, print_function

from hera_mc import geo_location, mc

data = {}
data['HH'] = ['herahex','HERA Hex locations', 'ro']
data['PH'] = ['paperhex','PAPER Hex locations', 'rs']
data['PI'] = ['paperimaging','PAPER Imaging locations', 'gs']
data['PP'] = ['paperpolarized','PAPER Polarized locations', 'bd']
data['S'] = ['stationgrid','Station grid locations', 'ks']
data['CR'] = ['container','Container location', 'k*']
data['ND'] = ['node','Node location', 'r*']

sorted_keys = sorted(data.keys())

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

with db.sessionmaker() as session:
    for k in sorted_keys:
        d = geo_location.StationMeta()
        d.prefix = k
        d.meta_class_name = data[k][0]
        d.description = data[k][1]
        d.plot_marker = data[k][2]
        session.add(d)
