#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to handle installing a new station into system.
"""

from hera_mc import mc, geo_location, cm_utils, cm_partconnect, geo_handling, geo_sysdef


def query_geo_information(args):
    """
    Gets geo_location information from user
    """
    if args.easting is None:
        args.easting = float(input("Easting:  "))
    if args.northing is None:
        args.northing = float(input("Northing:  "))
    if args.elevation is None:
        args.elevation = float(input("Elevation:  "))
    if args.sernum is None:
        args.sernum = input("Serial number:  ")
    args.datum = cm_utils.query_default("datum", args)
    args.tile = cm_utils.query_default("tile", args)
    if args.station_type_name is None:
        args.station_type_name = input("Station type name: ")
    args.date = cm_utils.query_default("date", args)
    return args


def entry_OK_to_add(session, station_name, geo_handle):
    OK = True
    if geo_handle.is_in_database(station_name):
        print(station_name, " already present.")
        OK = False
    geo_handle.close()
    return OK


def add_entry_to_geo_location(session, args):
    # NotNull
    sname = args.station_name
    dt = cm_utils.get_astropytime(args.date, args.time, args.format)
    data = [
        [sname, "station_name", sname],
        [sname, "station_type_name", args.station_type_name],
        [sname, "created_gpstime", dt.gps],
    ]
    # Other
    if args.datum:
        data.append([sname, "datum", args.datum])
    if args.tile:
        data.append([sname, "tile", args.tile])
    if args.northing:
        data.append([sname, "northing", args.northing])
    if args.easting:
        data.append([sname, "easting", args.easting])
    if args.elevation:
        data.append([sname, "elevation", args.elevation])
    geo_location.update(session, data, args.add_new_geo)


def add_entry_to_parts(session, args):
    # NotNull
    hpn = args.station_name
    rev = "A"
    dt = cm_utils.get_astropytime(args.date, args.time, args.format)
    data = [
        [hpn, rev, "hpn", hpn],
        [hpn, rev, "hpn_rev", rev],
        [hpn, rev, "hptype", "station"],
        [hpn, rev, "manufacturer_number", args.sernum],
        [hpn, rev, "start_gpstime", dt.gps],
    ]
    cm_partconnect.update_part(session, data)


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument(
        "station_name", help="Name of station (HH/A/B# for hera, ND# for node)."
    )
    parser.add_argument("-e", "--easting", help="Easting of new station.", default=None)
    parser.add_argument(
        "-n", "--northing", help="Northing of new station", default=None
    )
    parser.add_argument(
        "-z", "--elevation", help="Elevation of new station", default=None
    )
    cm_utils.add_date_time_args(parser)
    parser.add_argument(
        "--station_type_name", help="Station category name", default=None
    )
    parser.add_argument("--sernum", help="Serial number of station.", default=None)
    parser.add_argument("--datum", help="Datum of UTM [WGS84]", default="WGS84")
    parser.add_argument("--tile", help="UTM tile [34J]", default="34J")
    parser.add_argument(
        "--add_new_geo",
        help="Flag to allow update to add a new " "record.  [True]",
        action="store_false",
    )

    args = parser.parse_args()
    args.station_name = args.station_name.upper()
    if args.station_name.startswith(("HH", "HA", "HB")):
        antenna = geo_sysdef.read_antennas()
        if args.station_name not in antenna:
            raise ValueError("{} antenna not found.".format(args.station_name))
        args.easting = antenna[args.station_name]["E"]
        args.northing = antenna[args.station_name]["N"]
        args.elevation = antenna[args.station_name]["elevation"]
        ant_num = int(args.station_name[2:])
        for r, v in geo_sysdef.region.items():
            if ant_num in v:
                args.station_type_name = r
                break
        if args.sernum is None:
            args.sernum = args.station_name
    elif args.station_name.startswith("ND"):
        node = geo_sysdef.read_nodes()
        node_num = int(args.station_name[2:])
        if node_num not in node:
            raise ValueError("{} node not found.".format(args.station_name))
        args.easting = node[node_num]["E"]
        args.northing = node[node_num]["N"]
        args.elevation = node[node_num]["elevation"]
        args.station_type_name = "node"
        if args.sernum is None:
            args.sernum = args.station_name
    else:
        args = query_geo_information(args)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    geo_handle = geo_handling.Handling(session)

    if entry_OK_to_add(session, args.station_name, geo_handle):
        cm_utils.log("add_station", args=args)
        add_entry_to_geo_location(session, args)
        add_entry_to_parts(session, args)
