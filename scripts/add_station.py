#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle installing a new station into system.  All parameters are part of args.
The flag -q will force a query.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, geo_location, cm_utils
import sys, os.path

def get_coord_from_file(station_name,coord_filename):
    coords = None
    if station_name is not None:
        fp = open(coord_filename,'r')
        for line in fp:
            data = line.split()
            if data[0].upper() == station_name:
                coords = [data[0],float(data[1]),float(data[2]),float(data[3])]
                break
        fp.close()
    return coords

def query_default(a,args):
    vargs = vars(args)
    default = vargs[a]
    s = '%s [%s]:  ' % (a,str(default))
    v = raw_input(s).strip()
    if len(v) == 0:
        v = default
    return v

def query_geo_information(args):
    """
    Gets geo_location information from user
    """
    if args.station_name == None:
        args.station_name = raw_input('Station name:  ').upper()
    args.from_file = cm_utils._query_yn('Do you want to get coords from default file?','y')
    if args.from_file:
        coords = get_coord_from_file(args.station_name,args.coord_filename)
        if coords:
            args.easting = coords[1]
            args.northing = coords[2]
            args.elevation = coords[3]
        else:
            print(args.station_name,' not found in coords file.')
            sys.exit()
    else:
        args.easting = float(raw_input('Easting:  '))
        args.northing = float(raw_input('Northing:  '))
        args.elevation = float(raw_input('Elevation:  '))
        args.datum = query_default('datum',args)
        args.tile = query_default('tile',args)
        
    args.meta_class_name = query_default('meta_class_name',args)
    args.station_number = int(raw_input('Station number:  '))
    args.date = query_default('date',args)
    args.time = query_default('time',args)
    return args

def entry_OK_to_add(args):
    OK = True
    if geo_location.is_station_present(args,args.station_name,args.station_number):
        print(args.station_name,'/',args.station_number,' already present.')
        OK = False
    if OK:
        if geo_location.is_station_active(args,args.station_name):
            print(args.station_name,'is already active.')
            if cm_utils._query_yn('Shall I deactivate it to add new station_number?'):
                dt = cm_utils._get_datetime(args.date,args.time)
                old_station_number = geo_location.is_station_active(args,args.station_name,True)
                data = [[args.station_name,old_station_number,'station_number_stop_date',dt]]
                geo_location.update(args,data)
            else:
                OK = False
    return OK
def add_entry(args):
    ###NotNull
    sname = args.station_name
    snumb = args.station_number
    start = cm_utils._get_datetime(args.date,args.time)
    mclsn = args.meta_class_name
    data = [[sname,snumb,'station_name',sname],
            [sname,snumb,'station_number',snumb],
            [sname,snumb,'meta_class_name',mclsn],
            [sname,snumb,'station_number_start_date',start]]
    ###Other
    if args.datum:
        data.append([sname,snumb,'datum',args.datum])
    if args.tile:
        data.append([sname,snumb,'tile',args.tile])
    if args.northing:
        data.append([sname,snumb,'northing',args.northing])
    if args.easting:
        data.append([sname,snumb,'easting',args.easting])
    if args.elevation:
        data.append([sname,snumb,'elevation',args.elevation])

    geo_location.update(args,data)

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('-f', '--from_file',help="If present, will find station_name for coordinates in file \
                                                  (see --coord_filename) [False].", action='store_true')
    parser.add_argument('--coord_filename', help="Name of file containing coordinates of stations [data/HERA_350.txt]",
                         default='HERA_350.txt')
    parser.add_argument('-q', '--query', help="Flag to query user for parameters [False]",action='store_true')
    parser.add_argument('-p', '--station_number', help="Station number at new station (PAPER antenna number)", default=None)
    parser.add_argument('-s', '--station_name', help="Name of station (HH# for hera)", default=None)
    parser.add_argument('-e', '--easting',help="Easting of new station", default=None)
    parser.add_argument('-n', '--northing', help="Northing of new station", default=None)
    parser.add_argument('-z', '--elevation', help="Elevation of new station", default=None)
    parser.add_argument('--meta_class_name', help="Station category name [herahex]", default='herahex')
    parser.add_argument('--date', help="Start date of number at station. MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="Start time of number at station. hh:mm or now [now]", default='now')
    parser.add_argument('--datum', help="Datum of UTM [WGS84]",default='WGS84')
    parser.add_argument('--tile', help="UTM tile [34J]",default='34J')
    parser.add_argument('-v', '--verbosity', help="Set verbosity {l, m, h}. [h].", choices=['l','m','h'], default="h")
    parser.add_argument('--add_new_geo', help="Flag to allow update to add a new record.  [True]", action='store_false')

    args = parser.parse_args()
    args.verbosity = args.verbosity.lower()
    if args.station_name:
        args.station_name = args.station_name.upper()
    if args.station_number != None:
        args.station_number = int(args.station_number)

    if len(sys.argv)==1:
        args.query = True

    if args.coord_filename[0] != '.' and args.coord_filename[0] != '/':
        args.coord_filename = os.path.join(mc.data_path,args.coord_filename)
    if args.from_file:
        coords = get_coord_from_file(args.station_name,args.coord_filename)
        if coords:
            args.easting = coords[args.station_name][1]
            args.northing = coords[args.station_name][2]
            args.elevation = coords[args.station_name][3]

    if args.query:
        args = query_geo_information(args)

    if entry_OK_to_add(args):
        add_entry(args)


