#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to write out antenna locations for use in cal files.
"""
import pandas as pd
from hera_mc import mc, geo_handling, cm_utils
import datetime

parser = mc.get_mc_argument_parser()
parser.add_argument('--file', help="file name to save antenna locations to",
                    default='hera_ant_locs_' + datetime.date.today().strftime("%m_%d_%Y") + '.csv')
parser.add_argument('--cm_csv_path', help="path to cm csv files",
                    default=None)
args = parser.parse_args()
filename = args.file
db = mc.connect_to_mc_db(args)
session = db.sessionmaker()

cm_version = cm_utils.get_cm_version(mc_config_path=args.mc_config_path,
                                     cm_csv_path=args.cm_csv_path)

h = geo_handling.Handling(session)
locations = h.get_all_fully_connected_ever()

cofa_loc = h.cofa()
locations.append({'station_name': cofa_loc.station_name,
                  'station_type': cofa_loc.station_type_name,
                  'tile': cofa_loc.tile,
                  'datum': cofa_loc.datum,
                  'easting': cofa_loc.easting,
                  'northing': cofa_loc.northing,
                  'longitude': cofa_loc.lon,
                  'latitude': cofa_loc.lat,
                  'elevation': cofa_loc.elevation,
                  'antenna_number': -1,
                  'correlator_input_x': None,
                  'correlator_input_y': None,
                  'start_date': cofa_loc.created_date,
                  'stop_date': None})
df = pd.DataFrame(locations)
df = df[['station_name', 'station_type', 'datum', 'tile', 'easting', 'northing',
         'longitude', 'latitude', 'elevation', 'antenna_number',
         'correlator_input_x', 'correlator_input_y', 'start_date', 'stop_date']]
df = df.rename(columns({'station_name': 'antenna_name'}))
df['cm_version'] = cm_version
df.to_csv(filename, index=False)
