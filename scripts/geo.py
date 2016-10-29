#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location

"""
from __future__ import absolute_import, division, print_function

from hera_mc import geo_location, mc

import copy
import matplotlib.pyplot as plt

def split_arrays(args):
    """Get split out of the various sub-arrays.  Return dictionary keyed on type, with list of station_names"""
    sub_array_designators = ['HH','PI','PH','PP','S','N']
    sub_arrays = {}
    for sad in sub_array_designators:
        sub_arrays[sad] = []
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        locations  = session.query(geo_location.GeoLocation).all()
        for a in locations:
            for sad in sub_array_designators:
                try:
                    hh = int(a.station_name)
                    test_for_sub = 'HH'[:len(sad)]
                except ValueError:
                    test_for_sub = a.station_name[:len(sad)]
                if test_for_sub == sad:
                    sub_arrays[sad].append(a.station_name)
    return sub_arrays

def plot_arrays(args, sub_arrays):
    """Plot the various sub-array types"""
    markers = {'HH':'ro','PH':'rs','PI':'gs','PP':'bd','S':'bs'}
    plt.figure(args.graph)
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        for key in sub_arrays.keys():
            for loc in sub_arrays[key]:
                for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name==loc):
                    x = a.easting
                    if args.graph=='XY':
                        y = a.northing
                    else:
                        y = a.elevation
                plt.plot(x,y,markers[key])
    if args.graph=='XY':
        plt.axis('equal')
    plt.show()

def locate_station(args, sub_arrays):
    db = mc.connect_to_mc_db(args)
    try:
        station_search = int(args.locate)
        station_desig = geo_location.GeoLocation.station_number
    except ValueError:
        if args.locate[0].lower() == 'h':
            station_search = args.locate[1:]
        else:
            station_search = args.locate
        station_desig = geo_location.GeoLocation.station_name
    with db.sessionmaker() as session:
        for a in session.query(geo_location.GeoLocation).filter(station_desig==station_search):
            for key in sub_arrays.keys():
                if a.station_name in sub_arrays[key]:
                    this_sub_array = key
                    break
            if args.verbose:
                print('station_name: ',a.station_name)
                print('\tstation_number: ',a.station_number)
                print('\teasting: ',a.easting)
                print('\tnorthing: ',a.northing)
                print('\televation: ',a.elevation)
                print('\tsub-array: ',this_sub_array)
            else:
                print(a,this_sub_array)

if __name__=='__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-g','--graph',help="Graph data:  XY or Z, default is No",default=False)
    parser.add_argument('-l','--locate',help="Print out location of given station_name. Prepend with 'h' for HH station_name. Integer if station_number",default=False)
    parser.add_argument('-v','--verbose',help="Set to print out long forms of things.",action="store_true")
    args = parser.parse_args()
    sub_arrays = split_arrays(args)
    if args.graph:
        plot_arrays(args,sub_arrays)
    if args.locate:
        located = locate_station(args, sub_arrays)