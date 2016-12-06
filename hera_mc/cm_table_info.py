# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Some table info for configuration management.

"""

from __future__ import print_function
from hera_mc import part_connect, geo_location

cm_tables = {'part_info':[part_connect.PartInfo,0],
             'connections':[part_connect.Connections,1],
             'parts_paper':[part_connect.Parts,2],
             'geo_location':[geo_location.GeoLocation,3],
             'station_meta':[geo_location.StationMeta,4]}
base_data_prefix = 'initialization_base_data_'
data_prefix = 'initialization_data_'

