# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Some table info for configuration management."""

from . import cm_partconnect, geo_location

# Locates the table and specifies the required order of deletion (inverse for creation.)
cm_tables = {
    "part_info": [cm_partconnect.PartInfo, 0],
    "apriori_antenna": [cm_partconnect.AprioriAntenna, 1],
    "part_rosetta": [cm_partconnect.PartRosetta, 2],
    "connections": [cm_partconnect.Connections, 3],
    "parts": [cm_partconnect.Parts, 4],
    "geo_location": [geo_location.GeoLocation, 5],
    "station_type": [geo_location.StationType, 6],
}
data_prefix = "initialization_data_"


def order_the_tables(unordered_tables=None):
    """
    Ensure that the tables are loaded into the database in the proper order.

    Tables must be loaded into the database in the proper order to satisfy
    ForeignKey constraints.

    Parameters
    ----------
    unordered_tables : list or None
        list of unordered_tables or None.  Default is None, which gets all cm tables.

    Returns
    -------
    list
        list of ordered tables

    """
    if unordered_tables is None:
        unordered_tables = list(cm_tables.keys())
    ordered_tables = []
    for i in range(len(cm_tables.keys())):
        ordered_tables.append("NULL")
    for table in unordered_tables:
        try:
            ordered_tables[cm_tables[table][1]] = table
        except KeyError:
            print(table, "not found")
    while "NULL" in ordered_tables:
        ordered_tables.remove("NULL")
    return ordered_tables
