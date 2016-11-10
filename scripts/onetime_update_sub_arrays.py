#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Onetime transfer of geo-locations of antennas into the M&C database.

"""
from __future__ import absolute_import, division, print_function

from hera_mc import geo_location, mc

data = {}
data['HH'] = ['HERA Hex locations','ro']
data['PH'] = ['PAPER Hex locations','rs']
data['PI'] = ['PAPER Imaging locations','gs']
data['PP'] = ['PAPER Polarize locations','bd']
data['S']  = ['Station grid locations','ks']

sorted_keys = sorted(data.keys())

parser = mc.get_mc_argument_parser()
args = parser.parse_args()
db = mc.connect_to_mc_db(args)

with db.sessionmaker() as session:
    for k in sorted_keys:
        d = geo_location.SubArray()
        d.prefix = k
        d.description = data[k][0]
        d.plot_marker = data[k][1]
        session.add(d)
        print(d)

