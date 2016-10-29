#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Onetime transfer of geo-locations of antennas into the M&C database.

"""
from __future__ import absolute_import, division, print_function

from hera_mc import geo_location, mc

import copy
import matplotlib.pyplot as plt

def split_arrays(args):
    geo = {}
    sub_array_designators = ['HH','PI','PH','PP','S','N']
    sub_arrays = {}
    for sad in sub_array_designators:
        sub_arrays[sad] = []
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        locations  = session.query(geo_location.GeoLocation).all()
        for a in locations:
            print(type(a))
            try:
                geo[a.station_name] = copy.deepcopy(a)
            except AttributeError:
                continue
            for sad in sub_array_designators:
                try:
                    hh = int(a.station_name)
                    test_for_sub = 'HH'[:len(sad)]
                except ValueError:
                    test_for_sub = a.station_name[:len(sad)]
                if test_for_sub == sad:
                    sub_arrays[sad].append(a.station_name)
    return geo, sub_arrays

def plot_arrays(geo, sub_arrays, graph='XY'):
    markers = {'HH':'ro','PH':'rs','PI':'gs','PP':'bd','S':'bs'}
    plt.figure(graph)
    for key in sub_arrays.keys():
        for a in sub_arrays[key]:
            x = geo[a].easting
            if graph=='XY':
                y = geo[a].northing
            else:
                y = geo[a].elevation
            plt.plot(x,y,markers[key])
    if graph=='XY':
        plt.axis('equal')
    plt.show()

if __name__=='__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-g','--graph',help="graph data:  XY or Z, default is No",default='XY')
    args = parser.parse_args()
    if args.graph:
        geo,sub_arrays = split_arrays(args)
        plot_arrays(geo,sub_arrays,args.graph)