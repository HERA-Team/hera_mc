# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Keep track of geo-located stations.

Top modules are generally called by external (to CM) scripts.
Bottom part is the class that does the work.
"""

import copy
import warnings
from sqlalchemy import func
from pyuvdata import utils as uvutils
from numpy import radians

from . import mc, cm_partconnect, cm_utils, geo_location, cm_sysdef
from .data import DATA_PATH


def cofa(session=None):
    """
    Return location class of current COFA.

    Parameters
    ----------
    session:  db session to use

    """
    h = Handling(session)
    located = h.cofa()
    h.close()
    return located


def get_location(
    location_names, query_date="now", query_time=None, float_format=None, session=None
):
    """
    Get a GeoLocation object with lon/lat attributes for a location name.

    This is the wrapper for other modules outside cm to call.

    Parameters
    ----------
    location_names : list of str
        location names, either a station (geo_location key) or an antenna
    query_date :  Anything that `get_astropytime` can translate.
        Date for query.
    query_time : Anything that `get_astropytime` can translate.
        Time for query.
    float_format : str or None
        Format if query_date is unix or gps.
    session : Session object
        Session to use.

    Returns
    -------
    list of GeoLocation objects
        objects corresponding to location_names, wtih lon/lat attributes added.

    """
    query_date = cm_utils.get_astropytime(query_date, query_time, float_format)
    h = Handling(session)
    located = h.get_location(location_names, query_date)
    h.close()
    return located


def show_it_now(fignm=None):  # pragma: no cover
    """
    Show plot.

    Used in scripts to actually make plot (as opposed to within python). Seems to be needed...

    Parameters
    ----------
    fignm:  string/int for figure

    """
    import matplotlib.pyplot as plt

    if fignm is not None:
        plt.figure(fignm)
    plt.show()


class Handling:
    """
    Class to allow various manipulations of geo_locations and their properties etc.

    Parameters
    ----------
    session : Session object
        session on current database. If session is None, a new session
        on the default database is created and used.

    """

    coord = {"E": "easting", "N": "northing", "Z": "elevation"}
    hera_zone = [34, "J"]
    lat_corr = {"J": 10000000}

    def __init__(self, session=None, testing=False):
        if session is None:  # pragma: no cover
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session

        self.get_station_types()
        self.testing = testing
        self.axes_set = False
        self.fp_out = None
        self.graph = False
        self.station_types_plotted = False

    def close(self):
        """Close the session."""
        self.session.close()

    def cofa(self):
        """
        Get the current center of array.

        Returns
        -------
        GeoLocation object
            GeoLocation object for the center of the array.
        """
        current_cofa = self.station_types["cofa"]["Stations"]
        located = self.get_location(current_cofa, "now")
        if len(located) > 1:  # pragma: no cover
            s = "{} has multiple cofa values.".format(str(current_cofa))
            warnings.warn(s)

        return located

    def get_station_types(self):
        """
        Add a dictionary of sub-arrays (station_types) to the object.

        [station_type_name]{'Prefix', 'Description':'...', 'plot_marker':'...', 'stations':[]}
        """
        self.station_types = {}
        for sta in self.session.query(geo_location.StationType):
            self.station_types[sta.station_type_name.lower()] = {
                "Prefix": sta.prefix.upper(),
                "Description": sta.description,
                "Marker": sta.plot_marker,
                "Stations": set(),
            }
        for loc in self.session.query(geo_location.GeoLocation):
            self.station_types[loc.station_type_name]["Stations"].add(loc.station_name)
            expected_prefix = self.station_types[loc.station_type_name][
                "Prefix"
            ].upper()
            actual_prefix = loc.station_name[: len(expected_prefix)].upper()
            if expected_prefix != actual_prefix:  # pragma: no cover
                s = "Prefixes don't match: expected {} but got {} for {}".format(
                    expected_prefix, actual_prefix, loc.station_name
                )
                warnings.warn(s)

    def set_graph(self, graph_it):
        """
        Set the graph attribute.

        Parameters
        ----------
        graph_it : bool
            Flag indicating whether a graph should be made.

        """
        self.graph = graph_it

    def start_file(self, fname):
        """
        Open file for writing.

        Parameters
        ----------
        fname :  str
            File name to write to.

        """
        import os.path as op

        self.file_type = fname.split(".")[-1]
        write_header = False
        if op.isfile(fname):  # pragma: no cover
            print("{} exists so appending to it".format(fname))
        else:
            write_header = True
            print("Writing to new {}".format(fname))
        if not self.testing:  # pragma: no cover
            self.fp_out = open(fname, "a")
            if write_header:
                self.fp_out.write("{}\n".format(self._loc_line("header")))

    def is_in_database(self, station_name, db_name="geo_location"):
        """
        Check to see if a station_name is in the specified database table.

        Parameters
        ----------
        station_name :  str
            Name of station.
        db_name :  str
            Name of database table

        Returns
        -------
        bool
            True if station_name is present in specified table, False otherwise.

        """
        if db_name == "geo_location":
            station = self.session.query(geo_location.GeoLocation).filter(
                func.upper(geo_location.GeoLocation.station_name)
                == station_name.upper()
            )
        elif db_name == "connections":
            station = self.session.query(cm_partconnect.Connections).filter(
                func.upper(cm_partconnect.Connections.upstream_part)
                == station_name.upper()
            )
        else:
            raise ValueError("db not found.")
        if station.count() > 0:
            station_present = True
        else:
            station_present = False
        return station_present

    def find_antenna_at_station(
        self, station, query_date, query_time=None, float_format=None
    ):
        """
        Get antenna details for a station.

        Parameters
        ----------
        station :  str
            station name
        query_date :  Anything that `get_astropytime` can translate.
            Date for query.
        query_time : Anything that `get_astropytime` can translate.
            Time for query.
        float_format : str or None
            Format if query_date is unix or gps.

        Returns
        -------
        tuple of str
            (antenna_name, antenna_revision) for the antenna
            that was active at the date query_date, or None if no antenna was active
            at the station. Raises a warning if the database lists multiple active
            connections at the station at query_date.

        """
        query_date = cm_utils.get_astropytime(query_date, query_time, float_format)
        connected_antenna = self.session.query(cm_partconnect.Connections).filter(
            (func.upper(cm_partconnect.Connections.upstream_part) == station.upper())
            & (cm_partconnect.Connections.start_gpstime <= query_date.gps)
        )
        antenna_connected = []
        for conn in connected_antenna:
            if conn.stop_gpstime is None or query_date.gps <= conn.stop_gpstime:
                antenna_connected.append(copy.copy(conn))
        if len(antenna_connected) == 0:
            return None, None
        elif len(antenna_connected) > 1:
            warning_string = "More than one active connection for {}".format(
                antenna_connected[0].upstream_part
            )
            warnings.warn(warning_string)
            return None, None
        return antenna_connected[0].downstream_part, antenna_connected[0].down_part_rev

    def find_station_of_antenna(
        self, antenna, query_date, query_time=None, float_format=None
    ):
        """
        Get station for an antenna.

        Parameters
        ----------
        antenna : float, int, str
            antenna number as float, int, or string. If needed, it prepends the 'A'
        query_date :  Anything that `get_astropytime` can translate.
            Date for query.
        query_time : Anything that `get_astropytime` can translate.
            Time for query.
        float_format : str or None
            Format if query_date is unix or gps.

        Returns
        -------
        str
            station the antenna is connected to at query date.

        """
        query_date = cm_utils.get_astropytime(query_date, query_time, float_format)
        if isinstance(antenna, (int, float)):
            antenna = "A" + str(int(antenna))
        elif antenna[0].upper() != "A":
            antenna = "A" + antenna
        connected_antenna = self.session.query(cm_partconnect.Connections).filter(
            (func.upper(cm_partconnect.Connections.downstream_part) == antenna.upper())
            & (cm_partconnect.Connections.start_gpstime <= query_date.gps)
        )
        ctr = 0
        for conn in connected_antenna:
            if conn.stop_gpstime is None or query_date.gps <= conn.stop_gpstime:
                antenna_connected = copy.copy(conn)
                ctr += 1
        if ctr == 0:
            return None
        elif ctr > 1:
            raise ValueError(
                "More than one active connection between station and antenna"
            )
        return antenna_connected.upstream_part

    def get_location(
        self, to_find_list, query_date, query_time=None, float_format=None
    ):
        """
        Get GeoLocation objects for a list of station_names.

        Parameters
        ----------
        to_find_list :  list of str
            station names to find
        query_date :  Anything that `get_astropytime` can translate.
            Date for query.
        query_time : Anything that `get_astropytime` can translate.
            Time for query.
        float_format : str or None
            Format if query_date is unix or gps.

        Returns
        -------
        list of GeoLocation objects
            GeoLocation objects corresponding to station names.

        """
        import cartopy.crs as ccrs

        latlon_p = ccrs.Geodetic()
        utm_p = ccrs.UTM(self.hera_zone[0])
        lat_corr = self.lat_corr[self.hera_zone[1]]
        locations = []
        self.query_date = cm_utils.get_astropytime(query_date, query_time, float_format)
        for station_name in to_find_list:
            for a in self.session.query(geo_location.GeoLocation).filter(
                (
                    func.upper(geo_location.GeoLocation.station_name)
                    == station_name.upper()
                )
                & (geo_location.GeoLocation.created_gpstime < self.query_date.gps)
            ):
                a.gps2Time()
                a.desc = self.station_types[a.station_type_name]["Description"]
                a.lon, a.lat = latlon_p.transform_point(
                    a.easting, a.northing - lat_corr, utm_p
                )
                a.X, a.Y, a.Z = uvutils.XYZ_from_LatLonAlt(
                    radians(a.lat), radians(a.lon), a.elevation
                )
                locations.append(copy.copy(a))
                if self.fp_out is not None and not self.testing:  # pragma: no cover
                    self.fp_out.write("{}\n".format(self._loc_line(a)))
        return locations

    def _loc_line(self, loc):
        """
        Return a list or str of the given locations, depending if loc is list or not.

        Parameters
        ----------
        loc : geo_location class, list of them, or 'header'
            List of geo_location class (or single)
        fmt : str
            Type of format; either 'csv' or not

        Return
        ------
        list-of-str or str : a single line containing the data
            if loc=='header' it returns the header line
        """
        if loc == "header":
            if self.file_type == "csv":
                return "name,easting,northing,longitude,latitude,elevation,X,Y,Z"
            else:
                return (
                    "name  easting   northing   longitude latitude  elevation"
                    "    X              Y               Z"
                )
        is_list = True
        if not isinstance(loc, list):
            loc = [loc]
            is_list = False
        ret = []
        for a in loc:
            if self.file_type == "csv":
                s = "{},{},{},{},{},{},{},{},{}".format(
                    a.station_name,
                    a.easting,
                    a.northing,
                    a.lon,
                    a.lat,
                    a.elevation,
                    a.X,
                    a.Y,
                    a.Z,
                )
            else:
                s = "{:6s} {:.2f} {:.2f} {:.6f} {:.6f} {:.1f} {:.6f} {:.6f} {:.6f}".format(
                    a.station_name,
                    a.easting,
                    a.northing,
                    a.lon,
                    a.lat,
                    a.elevation,
                    a.X,
                    a.Y,
                    a.Z,
                )
            ret.append(s)
        if not is_list:
            ret = ret[0]
        return ret

    def print_loc_info(self, loc_list):
        """
        Print out location information as returned from get_location.

        Parameters
        ----------
        loc_list : list of str
            List of location_names to print information for.

        """
        if loc_list is None or len(loc_list) == 0:
            print("No locations found.")
            return
        for a in loc_list:
            print("station_name: ", a.station_name)
            print("\teasting: ", a.easting)
            print("\tnorthing: ", a.northing)
            print("\tlon/lat:  ", a.lon, a.lat)
            print("\televation: ", a.elevation)
            print("\tX, Y, Z: {}, {}, {}".format(a.X, a.Y, a.Z))
            print("\tstation description ({}):  {}".format(a.station_type_name, a.desc))
            print("\tcreated:  ", cm_utils.get_time_for_display(a.created_date))

    def parse_station_types_to_check(self, sttc):
        """
        Parse station strings to list of stations.

        Parameters
        ----------
        sttc : str or list of str
            Stations to check, can be a list of stations or "all" or "default".

        Returns
        -------
        list of str
            List of startions.

        """
        self.get_station_types()
        if isinstance(sttc, str):
            if sttc.lower() == "all":
                return list(self.station_types.keys())
            elif sttc.lower() == "default":
                sttc = cm_sysdef.hera_zone_prefixes
            else:
                sttc = [sttc]
        sttypes = set()
        for s in sttc:
            if s.lower() in self.station_types.keys():
                sttypes.add(s.lower())
            else:
                for k, st in self.station_types.items():
                    if s.upper() == st["Prefix"][: len(s)].upper():
                        sttypes.add(k.lower())
        return list(sttypes)

    def get_ants_installed_since(self, query_date, station_types_to_check="all"):
        """
        Get list of antennas installed since query_date.

        Parameters
        ----------
        query_date : astropy Time
            Date to get limit check for installation.
        station_types_to_check : str or list of str
            Stations types to limit check.

        """
        import cartopy.crs as ccrs

        station_types_to_check = self.parse_station_types_to_check(
            station_types_to_check
        )
        dt = query_date.gps
        latlon_p = ccrs.Geodetic()
        utm_p = ccrs.UTM(self.hera_zone[0])
        lat_corr = self.lat_corr[self.hera_zone[1]]
        found_stations = []
        for a in self.session.query(geo_location.GeoLocation).filter(
            geo_location.GeoLocation.created_gpstime >= dt
        ):
            if a.station_type_name.lower() in station_types_to_check:
                a.gps2Time()
                a.desc = self.station_types[a.station_type_name]["Description"]
                a.lon, a.lat = latlon_p.transform_point(
                    a.easting, a.northing - lat_corr, utm_p
                )
                a.X, a.Y, a.Z = uvutils.XYZ_from_LatLonAlt(
                    radians(a.lat), radians(a.lon), a.elevation
                )
                found_stations.append(copy.copy(a))
                if self.fp_out is not None and not self.testing:  # pragma: no cover
                    self.fp_out.write("{}\n".format(self._loc_line(a)))
        return found_stations

    def get_antenna_label(
        self, label_to_show, stn, query_date, query_time=None, float_format=None
    ):
        """
        Get a label for a station.

        Parameters
        ----------
        label_to_show : str
            Specify label type, one of ["name", "num", "ser"]
        stn : GeoLocation object
            station to get label for.
        query_date :  Anything that `get_astropytime` can translate.
            Date for query.
        query_time : Anything that `get_astropytime` can translate.
            Time for query.
        float_format : str or None
            Format if query_date is unix or gps.

        Returns
        -------
        str
            station label

        """
        if label_to_show == "name":
            return stn.station_name
        ant, rev = self.find_antenna_at_station(
            stn.station_name, query_date, query_time, float_format
        )
        if ant is None:
            return None
        if label_to_show == "num":
            return ant.strip("A")
        if label_to_show == "ser":
            p = self.session.query(cm_partconnect.Parts).filter(
                (cm_partconnect.Parts.hpn == ant)
                & (cm_partconnect.Parts.hpn_rev == rev)
            )
            if p.count() == 1:
                return p.first().manufacturer_number.replace("S/N", "")
            else:
                return "-"
        return None

    def plot_stations(self, locations, **kwargs):  # pragma: no cover
        """
        Plot a list of stations.

        Parameters
        ----------
        stations_to_plot_list : list of str
            list containing station_names (note:  NOT antenna_numbers)
        kwargs :  dict
            arguments for marker_color, marker_shape, marker_size, label, xgraph, ygraph

        """
        if not len(locations) or not self.graph or self.testing:
            return
        displaying_label = bool(kwargs["label"])
        if displaying_label:
            label_to_show = kwargs["label"].lower()
        fig_label = "{} vs {} Antenna Positions".format(
            kwargs["xgraph"], kwargs["ygraph"]
        )
        import matplotlib.pyplot as plt

        for a in locations:
            pt = {
                "easting": a.easting,
                "northing": a.northing,
                "elevation": a.elevation,
            }
            x_vals = pt[self.coord[kwargs["xgraph"]]]
            y_vals = pt[self.coord[kwargs["ygraph"]]]
            plt.plot(
                x_vals,
                y_vals,
                color=kwargs["marker_color"],
                label=a.station_name,
                marker=kwargs["marker_shape"],
                markersize=kwargs["marker_size"],
            )
            if displaying_label:
                labeling = self.get_antenna_label(label_to_show, a, self.query_date)
                if labeling:
                    plt.annotate(
                        labeling, xy=(x_vals, y_vals), xytext=(x_vals + 2, y_vals)
                    )
        if not self.axes_set:
            self.axes_set = True
            if kwargs["xgraph"].upper() != "Z" and kwargs["ygraph"].upper() != "Z":
                plt.axis("equal")
            plt.xlabel(kwargs["xgraph"] + " [m]")
            plt.ylabel(kwargs["ygraph"] + " [m]")
            plt.title(fig_label)
        return

    def plot_all_stations(self):
        """Plot all stations."""
        if not self.graph:
            return
        import os.path
        import numpy
        import matplotlib.pyplot as plt

        p = numpy.loadtxt(os.path.join(DATA_PATH, "HERA_350.txt"), usecols=(1, 2, 3))
        if not self.testing:  # pragma: no cover
            plt.plot(p[:, 0], p[:, 1], marker="o", color="0.8", linestyle="none")
        return len(p[:, 0])

    def get_active_stations(
        self,
        station_types_to_use,
        query_date,
        query_time=None,
        float_format=None,
        hookup_type=None,
    ):
        """
        Get active stations.

        Parameters
        ----------
        station_types_to_use : str or list of str
            Stations to use, can be a list of stations or "all" or "default".
        query_date :  Anything that `get_astropytime` can translate.
            Date for query.
        query_time : Anything that `get_astropytime` can translate.
            Time for query, ignored if at_date is a float or contains time information.
        float_format : str or None
            Format if query_date is unix or gps or jd day.
        hookup_type : str
            hookup_type to use

        Returns
        -------
        list of GeoLocation objects
            List of GeoLocation objects for all active stations.

        """
        from . import cm_hookup, cm_revisions

        query_date = cm_utils.get_astropytime(query_date, query_time, float_format)
        hookup = cm_hookup.Hookup(self.session)
        hookup_dict = hookup.get_hookup(
            hookup.hookup_list_to_cache, at_date=query_date, hookup_type=hookup_type
        )
        self.station_types_to_use = self.parse_station_types_to_check(
            station_types_to_use
        )
        active_stations = []
        for st in self.station_types_to_use:
            for loc in self.station_types[st]["Stations"]:
                if cm_revisions.get_full_revision(loc, hookup_dict):
                    active_stations.append(loc)
        if len(active_stations):
            print("{}.....".format(12 * "."))
            print("{:12s}  {:3d}".format("active", len(active_stations)))
        return self.get_location(active_stations, query_date)

    def plot_station_types(
        self,
        station_types_to_use,
        query_date,
        query_time=None,
        float_format=None,
        **kwargs
    ):
        """
        Plot the various sub-array types.

        Parameters
        ----------
        station_types_to_use : str or list of str
            station_types or prefixes to plot.
        query_date :  Anything that `get_astropytime` can translate.
            Date for query.
        query_time : Anything that `get_astropytime` can translate.
            Time for query, ignored if at_date is a float or contains time information.
        float_format : str or None
            Format if query_date is unix or gps or jd day.
        kwargs :  dict
            matplotlib arguments for marker_color, marker_shape, marker_size, label, xgraph, ygraph

        """
        if self.station_types_plotted:
            return
        self.station_types_plotted = True
        self.axes_set = False
        station_types_to_use = self.parse_station_types_to_check(station_types_to_use)
        total_plotted = 0
        for st in sorted(station_types_to_use):
            kwargs["marker_color"] = self.station_types[st]["Marker"][0]
            kwargs["marker_shape"] = self.station_types[st]["Marker"][1]
            kwargs["marker_size"] = 5
            stations_to_plot = self.get_location(
                self.station_types[st]["Stations"], query_date, query_time, float_format
            )
            self.plot_stations(stations_to_plot, **kwargs)
            if len(stations_to_plot):
                print("{:12s}  {:3d}".format(st, len(stations_to_plot)))
                total_plotted += len(stations_to_plot)
        print("{:12s}  ---".format(" "))
        print("{:12s}  {:3d}".format("Total", total_plotted))
