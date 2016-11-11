#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""This is meant to hold utility scripts for geo_location

"""
from __future__ import absolute_import, division, print_function

from hera_mc import geo_location, mc

import matplotlib.pyplot as plt

def split_update_request(request):
    """
    splits out the update request

    return nested list

    Parameters:
    ------------
    request:  station0:column0:value0,[station1:]column1:value1,[...]
        stationN:  station_name or station_number, first entry must have one, if absent propagate first
        columnN:  name of geo_location column
        valueN:  corresponding new value
    """
    data = []
    data_to_proc = request.split(',')
    station0 = data_to_proc[0].split(':')[0]
    for d in data_to_proc:
        scv = d.split(':')
        if len(scv)==3:
            pass
        elif len(scv)==2:
            scv.insert(0,station0)
        data.append(scv)
    return data

def plot_arrays(args, overplot=None):
    """Plot the various sub-array types"""
    vpos = {'E':0,'N':1,'Z':2}
    plt.figure(args.xgraph+args.ygraph)
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        sub_arrays = session.split_arrays()
        for key in sub_arrays.keys():
            for loc in sub_arrays[key]['Stations']:
                for a in session.query(geo_location.GeoLocation).filter(geo_location.GeoLocation.station_name==loc):
                    v = [a.easting,a.northing,a.elevation]
                plt.plot(v[vpos[args.xgraph]],v[vpos[args.ygraph]],sub_arrays[key]['Marker'],label=a.station_name)
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
    station, station_col = geo_location.station_name_or_number(args.locate)
    v = None
    db = mc.connect_to_mc_db(args)
    with db.sessionmaker() as session:
        sub_arrays = session.split_arrays()
        for a in session.query(geo_location.GeoLocation).filter(station_col==station):
            for key in sub_arrays.keys():
                if a.station_name in sub_arrays[key]['Stations']:
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
                    print('\tsub-array: ',this_sub_array,sub_arrays[this_sub_array]['Description'])
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
    parser.add_argument('-u','--update',help="Update station records.  Format station0:col0:val0,[station1:]col1:val1...",default=None)
    parser.add_argument('-v','--verbosity',help="Set verbosity {l,m,h} [m].",default="m")
    parser.add_argument('-x','--xgraph',help='X-axis of graph {N,E,Z} [E]',default='E')
    parser.add_argument('-y','--ygraph',help='Y-axis of graph {N,E,Z} [N]',default='N')
    args = parser.parse_args()
    args.xgraph = args.xgraph.upper()
    args.ygraph = args.ygraph.upper()
    located = None
    if args.update:
        data = split_update_request(args.update)
        geo_location.update(args,data)
    if args.show:
        args.locate = args.show 
        args.graph = True
    if args.locate:
        args.locate = args.locate.upper()
        located = locate_station(args, show_geo=True)
    if args.graph:
        plot_arrays(args,located)
