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

sub_array_designators = {'HH':'ro','PH':'rs','PI':'gs','PP':'bd','S':'bs'} #sub-arrays and plotting symbol

def plot_arrays(args, overplot=None):
    """Plot the various sub-array types"""
    global sub_array_designators
    vpos = {'E':0,'N':1,'Z':2}
    plt.figure(args.xgraph+args.ygraph)
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        sub_arrays = session.split_arrays(sub_array_designators.keys())
        for key in sub_arrays.keys():
            for loc in sub_arrays[key]:
                for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name==loc):
                    v = [a.easting,a.northing,a.elevation]
                plt.plot(v[vpos[args.xgraph]],v[vpos[args.ygraph]],sub_array_designators[key])
    if overplot:
        plt.plot(overplot[vpos[args.xgraph]],overplot[vpos[args.ygraph]],'ys', markersize=10,label=overplot[3])
        plt.legend(loc='upper right')
    if args.xgraph!='Z' and args.ygraph!='Z':
        plt.axis('equal')
    plt.plot(xaxis=args.xgraph,yaxis=args.ygraph)
    plt.show()

def locate_station(args, show_geo=False):
    """Return the location of station_name or station_number as contained in args.locate.  
       If sub_array data exists, print subarray name."""
    global sub_array_designators
    try:
        station_search = int(args.locate)
        station_desig = geo_location.GeoLocation.station_number
    except ValueError:
        if args.locate[0] == 'H':
            station_search = args.locate[1:]
        else:
            station_search = args.locate
        station_desig = geo_location.GeoLocation.station_name
    v = None
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        sub_arrays = session.split_arrays(sub_array_designators.keys())
        for a in session.query(geo_location.GeoLocation).filter(station_desig==station_search):
            if sub_arrays:
                for key in sub_arrays.keys():
                    if a.station_name in sub_arrays[key]:
                        this_sub_array = key
                        break
            else:
                this_sub_array = 'No sub-array information.'
            v = [a.easting,a.northing,a.elevation,a.station_name,this_sub_array]
            if show_geo:
                if args.verbosity=='m' or args.verbosity=='h':
                    print('station_name: ',a.station_name)
                    print('\tstation_number: ',a.station_number)
                    print('\teasting: ',a.easting)
                    print('\tnorthing: ',a.northing)
                    print('\televation: ',a.elevation)
                    print('\tsub-array: ',this_sub_array)
                elif args.verbosity=='l':
                    print(a,this_sub_array)
    if show_geo:
        if not v and args.verbosity=='m' or args.verbosity=='h':
            print(args.locate,' not found.')
    return v

if __name__=='__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-g','--graph',help="Graph data of all elements (per xgraph, ygraph args)",action='store_true')
    parser.add_argument('-s','--show',help='Graph and locate a station (same as geo.py -gl XX)',default=False)
    parser.add_argument('-l','--locate',help="Location of given s_name or s_number (assumed if <int>). Prepend with 'h' for HH s_name.",default=False)
    parser.add_argument('-v','--verbosity',help="Set verbosity {l,m,h} [m].",default="m")
    parser.add_argument('-x','--xgraph',help='X-axis of graph {N,E,Z} [E]',default='E')
    parser.add_argument('-y','--ygraph',help='Y-axis of graph {N,E,Z} [N]',default='N')
    args = parser.parse_args()
    args.xgraph = args.xgraph.upper()
    args.ygraph = args.ygraph.upper()
    located = None
    if args.show:
        args.locate = args.show 
        args.graph = True
    if args.locate:
        args.locate = args.locate.upper()
        located = locate_station(args, show_geo=True)
    if args.graph:
        plot_arrays(args,located)
