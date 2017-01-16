#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle installing a new station into system.  All parameters are part of args.
The flag -q will force a query.
"""

from __future__ import absolute_import, division, print_function

from hera_mc import mc, geo_location, cm_utils, part_connect
import sys
import os.path

default_coord_file_name = os.path.join(mc.data_path, 'HERA_350.txt')


def get_coord_from_file(station_name, coord_filename):
    coords = None
    if station_name is not None:
        fp = open(coord_filename, 'r')
        for line in fp:
            data = line.split()
            if data[0].upper() == station_name:
                coords = [data[0], float(data[1]), float(
                    data[2]), float(data[3])]
                break
        fp.close()
    return coords


def query_geo_information(args):
    """
    Gets geo_location information from user
    """
    if args.station_name == None:
        args.station_name = raw_input('Station name:  ').upper()
    if not args.from_file:
        args.from_file = cm_utils._query_yn(
            'Do you want to get coords from default file?', 'y')
    if args.from_file:
        coords = get_coord_from_file(args.station_name, args.from_file)
        if coords:
            args.easting = coords[1]
            args.northing = coords[2]
            args.elevation = coords[3]
        else:
            print(args.station_name, ' not found in coords file.')
            sys.exit()
    else:
        args.easting = float(raw_input('Easting:  '))
        args.northing = float(raw_input('Northing:  '))
        args.elevation = float(raw_input('Elevation:  '))
        args.datum = cm_utils._query_default('datum', args)
        args.tile = cm_utils._query_default('tile', args)
    args.station_type_name = cm_utils._query_default('station_type_name', args)
    args.date = cm_utils._query_default('date', args)
    return args


def entry_OK_to_add(args):
    OK = True
    if geo_location.is_station_present(args, args.station_name):
        print(args.station_name, ' already present.')
        OK = False
    return OK


def add_entry_to_geo_location(args):
    # NotNull
    sname = args.station_name
    dt = cm_utils._get_datetime(args.date, args.time)
    data = [[sname, 'station_name', sname],
            [sname, 'station_type_name', args.station_type_name],
            [sname, 'created_date', dt]]
    # Other
    if args.datum:
        data.append([sname, 'datum', args.datum])
    if args.tile:
        data.append([sname, 'tile', args.tile])
    if args.northing:
        data.append([sname, 'northing', args.northing])
    if args.easting:
        data.append([sname, 'easting', args.easting])
    if args.elevation:
        data.append([sname, 'elevation', args.elevation])
    geo_location.update(args, data)


def add_entry_to_parts(args):
    # NotNull
    hpn = args.station_name
    rev = 'A'
    dt = cm_utils._get_datetime(args.date, args.time)
    data = [[hpn, rev, 'hpn', hpn],
            [hpn, rev, 'hpn_rev', rev],
            [hpn, rev, 'hptype', 'station'],
            [hpn, rev, 'start_date', dt]]
    part_connect.update_part(args, data)

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.add_argument('station_name', nargs='?',
                        help="Name of station (HH# for hera)", default=None)
    parser.add_argument(
        '-q', '--query', help="Flag to query user for parameters [False]", action='store_true')
    parser.add_argument('-e', '--easting',
                        help="Easting of new station", default=None)
    parser.add_argument('-n', '--northing',
                        help="Northing of new station", default=None)
    parser.add_argument('-z', '--elevation',
                        help="Elevation of new station", default=None)
    parser.add_argument('--date', help="MM/DD/YY or now [now]", default='now')
    parser.add_argument('--time', help="hh:mm or now [now]", default='now')
    parser.add_argument(
        '--station_type_name', help="Station category name [herahex]", default='herahex')
    parser.add_argument(
        '--datum', help="Datum of UTM [WGS84]", default='WGS84')
    parser.add_argument('--tile', help="UTM tile [34J]", default='34J')
    parser.add_argument(
        '-v', '--verbosity', help="Set verbosity. [h].", choices=['l', 'm', 'h'], default="h")
    parser.add_argument(
        '--add_new_geo', help="Flag to allow update to add a new record.  [True]", action='store_false')
    parser.add_argument(
        '--add_new_part', help="Flag to allow update to add a new record.  [True]", action='store_false')
    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument('-f', '--use-file', help="Use default coordinate file",
                            dest='from_file', action='store_const', const=default_coord_file_name)
    file_group.add_argument('-X', '--dont-use-file', help="Don't use file for coordinates.",
                            dest='from_file', action='store_const', const=False)
    file_group.add_argument(
        '--from_file', help="Use file to retrieve coordinate information.")
    parser.set_defaults(from_file=default_coord_file_name)

    args = parser.parse_args()
    args.verbosity = args.verbosity.lower()
    if args.station_name:
        args.station_name = args.station_name.upper()

    if len(sys.argv) == 1:
        args.query = True

    if args.from_file:
        coords = get_coord_from_file(args.station_name, args.from_file)
        if coords:
            args.easting = coords[1]
            args.northing = coords[2]
            args.elevation = coords[3]

    if args.query:
        args = query_geo_information(args)

    if entry_OK_to_add(args):
        cm_utils._log('add_station', args=args)
        add_entry_to_geo_location(args)
        add_entry_to_parts(args)
