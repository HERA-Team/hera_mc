# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Methods for handling locating correlator and various system aspects."""

from sqlalchemy import func, and_, or_
import numpy as np

from . import mc, cm_partconnect, cm_utils, cm_sysdef, cm_hookup
from . import geo_handling


class SystemInfo:
    """
    Object containing system information, a convenience for the system info methods below.

    Parameters
    ----------
    stn : None or geo_handling object.  If None, it initializes a class with empty lists.
        Otherwise, it initializes based on the geo_handling object class.
        Anything else will generate an error.

    """

    sys_info = [
        "station_name",
        "station_type_name",
        "tile",
        "datum",
        "easting",
        "northing",
        "lon",
        "lat",
        "elevation",
        "antenna_number",
        "correlator_input",
        "snap_serial",
        "start_date",
        "stop_date",
        "epoch",
    ]

    def __init__(self, stn=None):
        if stn is None:
            for s in self.sys_info:
                setattr(self, s, [])
        else:
            for s in self.sys_info:
                setattr(self, s, None)
                try:
                    a = getattr(stn, s)
                except AttributeError:
                    continue
                setattr(self, s, a)

    def update_arrays(self, stn):
        """
        Will update the object based on the supplied station information.

        Parameters
        ----------
        stn : geo_handling object or None
            Contains the init station information.  If None, it will initial a blank object.
        """
        if stn is None:
            return
        for s in self.sys_info:
            try:
                arr = getattr(self, s)
            except AttributeError:  # pragma: no cover
                continue
            arr.append(getattr(stn, s))


class Handling:
    """
    Class to allow various manipulations of correlator inputs etc.

    Parameters
    ----------
    session : object
        session on current database. If session is None, a new session
        on the default database is created and used.

    """

    def __init__(self, session=None):
        if session is None:  # pragma: no cover
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.geo = geo_handling.Handling(self.session)
        self.H = None
        self.sysdef = cm_sysdef.Sysdef()
        self.apriori_status_set = None

    def close(self):  # pragma: no cover
        """Close the session."""
        self.session.close()

    def cofa(self):
        """
        Return the geographic information for the center-of-array.

        Returns
        -------
        object
            Geo object for the center-of-array (cofa)

        """
        cofa = self.geo.cofa()
        return cofa

    def get_connected_stations(
        self, at_date, at_time=None, float_format=None, hookup_type=None
    ):
        """
        Return a list of class SystemInfo of all of the stations connected at_date.

        Each location is returned class SystemInfo.  Attributes are:
            'station_name': name of station (string, e.g. 'HH27')
            'station_type_name': type of station (type 'herahexe', etc)
            'tile': UTM tile name (string, e.g. '34J'
            'datum': UTM datum (string, e.g. 'WGS84')
            'easting': station UTM easting (float)
            'northing': station UTM northing (float)
            'lon': station longitude (float)
            'lat': station latitude (float)
            'elevation': station elevation (float)
            'antenna_number': antenna number (integer)
            'correlator_input': correlator input for x (East) pol and y (North) pol
                (string tuple-pair)
            'timing': start and stop gps seconds for both pols

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information.
        float_format : str
            Format if at_date is a number denoting gps or unix seconds or jd day.
        hookup_type : str
            Type of hookup to use (current observing system is 'parts_hera').
            If 'None' it will determine which system it thinks it is based on
            the part-type.  The order in which it checks is specified in cm_sysdef.
            Only change if you know you want a different system (like 'parts_paper').

        Returns
        -------
        list
            List of stations connected.

        """
        at_date = cm_utils.get_astropytime(at_date, at_time, float_format)
        hookup_obj = cm_hookup.Hookup(self.session)
        hud = hookup_obj.get_hookup(
            hpn=cm_sysdef.hera_zone_prefixes,
            pol="all",
            at_date=at_date,
            exact_match=False,
            use_cache=False,
            hookup_type=hookup_type,
        )
        station_conn = []
        found_keys = list(hud.keys())
        found_stations = [x.split(":")[0] for x in found_keys]
        station_geo = self.geo.get_location(found_stations, at_date)
        for i, key in enumerate(found_keys):
            stn, rev = cm_utils.split_part_key(key)
            ant_num = int(stn[2:])
            station_info = SystemInfo(station_geo[i])
            station_info.antenna_number = ant_num
            current_hookup = hud[key].hookup
            corr = {}
            snap_serial_number = {}
            hutype = {}
            station_info.timing = {}
            for ppkey, hu in current_hookup.items():
                pol = ppkey[0].lower()
                hutype[pol] = hud[key].hookup_type[ppkey]
                cind = self.sysdef.corr_index[hutype[pol]] - 1
                try:
                    snap_port = hu[cind].downstream_input_port
                    node = int(hu[cind + 1].downstream_part[1:])
                    loc = int(hu[cind + 1].downstream_input_port[3:])
                    feng = f"heraNode{node}Snap{loc}"
                    corr[pol] = "{}>{}".format(snap_port, feng)
                    snap_serial_number[pol] = hu[cind].downstream_part
                except (IndexError, ValueError):  # pragma: no cover
                    corr[pol] = "None"
                    snap_serial_number[pol] = "None"
                station_info.timing[pol] = hud[key].timing[ppkey]
            if corr["e"] == "None" and corr["n"] == "None":
                continue
            station_info.correlator_input = (corr["e"], corr["n"])
            station_info.snap_serial = (
                snap_serial_number["e"],
                snap_serial_number["n"],
            )
            station_info.epoch = f"e:{hutype['e']}, n:{hutype['n']}"
            station_conn.append(station_info)
        return station_conn

    def get_cminfo_correlator(self, hookup_type=None):
        """
        Return a dict with info needed by the correlator.

        Note: This method requires pyuvdata

        Parameters
        ----------
        hookup_type : str or None
            Type of hookup to use (current observing system is 'parts_hera').
            If 'None' it will determine which system it thinks it is based on
            the part-type.  The order in which it checks is specified in cm_sysdef.
            Only change if you know you want a different system (like 'parts_paper').
            Default is None.

        Returns
        -------
        dict
            cm info formatted for the correlator.
            Dict keys are:
                'antenna_numbers': Antenna numbers (list of integers)
                'antenna_names': Station names (we use antenna_names because that's
                    what they're called in data files) (list of strings)
                'correlator_inputs': Correlator input strings for x/y (e/n)
                    polarizations (list of 2 element tuples of strings)
                'antenna_positions': Antenna positions in relative ECEF coordinates
                    (list of 3-element vectors of floats)
                'cm_version': CM git hash (string)
                'cofa_lat': latitude of the center-of-array in degrees
                'cofa_lon': longitude of the center-of-array in degrees
                'cofa_alt': altitude of center-of-array in meters
        """
        from pyuvdata import utils as uvutils
        from . import cm_handling

        cm_h = cm_handling.Handling(session=self.session)
        cm_version = cm_h.get_cm_version()
        cofa_loc = self.geo.cofa()[0]
        cofa_xyz = uvutils.XYZ_from_LatLonAlt(
            cofa_loc.lat * np.pi / 180.0,
            cofa_loc.lon * np.pi / 180.0,
            cofa_loc.elevation,
        )
        stations_conn = self.get_connected_stations(
            at_date="now", hookup_type=hookup_type
        )
        stn_arrays = SystemInfo()
        for stn in stations_conn:
            stn_arrays.update_arrays(stn)
        # latitudes, longitudes output by get_connected_stations are in degrees
        # XYZ_from_LatLonAlt wants radians
        ecef_positions = uvutils.XYZ_from_LatLonAlt(
            np.array(stn_arrays.lat) * np.pi / 180.0,
            np.array(stn_arrays.lon) * np.pi / 180.0,
            stn_arrays.elevation,
        )

        rel_ecef_positions = ecef_positions - cofa_xyz
        return {
            "antenna_numbers": stn_arrays.antenna_number,
            # This is actually station names, not antenna names,
            # but antenna_names is what it's called in pyuvdata
            "antenna_names": stn_arrays.station_name,
            # this is a tuple giving the f-engine names for e, n
            "correlator_inputs": stn_arrays.correlator_input,
            # this is a tuple giving the corresponding snap serial numbers for e, n
            "snap_serial_numbers": stn_arrays.snap_serial,
            "antenna_positions": rel_ecef_positions.tolist(),
            "cm_version": cm_version,
            "cofa_lat": cofa_loc.lat,
            "cofa_lon": cofa_loc.lon,
            "cofa_alt": cofa_loc.elevation,
        }

    def get_part_at_station_from_type(
        self,
        stn,
        at_date,
        part_type,
        include_revs=False,
        include_ports=False,
        hookup_type=None,
    ):
        """
        Get the part number at a given station of a given part type.

        E.g. find the 'post-amp' at station 'HH68'.

        Parameters
        ----------
        stn : str, list
            Antenna number of format HHi where i is antenna number (string or list of strings)
        at_date : str
            Date at which connection is true, format 'YYYY-M-D' or 'now'
        part_type : str
            Part type to look for
        include_revs : bool
            Flag whether to include all revisions.  Default is False
        include_ports : bool
            Flag whether to include ports.  Default is False
        hookup_type : str
            Type of hookup to use (current observing system is 'parts_hera').
            If 'None' it will determine which system it thinks it is based on
            the part-type.  The order in which it checks is specified in cm_sysdef.
            Only change if you know you want a different system (like 'parts_paper').
            Default is None.

        Returns
        -------
        dict
            {pol:(location, #)}

        """
        parts = {}
        hookup_obj = cm_hookup.Hookup(self.session)
        if isinstance(stn, str):
            stn = [stn]
        hud = hookup_obj.get_hookup(
            hpn=stn, at_date=at_date, exact_match=True, hookup_type=hookup_type
        )
        for k, hu in hud.items():
            parts[k] = hu.get_part_from_type(
                part_type, include_revs=include_revs, include_ports=include_ports
            )
        return parts

    def publish_summary(
        self,
        hlist=["default"],
        exact_match=False,
        hookup_cols="all",
        sortby="node,station",
    ):
        """
        Publish the hookup on hera.today.

        Parameters
        ----------
        hlist : list
            List of prefixes or stations to use in summary.
            Default is the "default" prefix list in cm_utils.
        exact_match : bool
            Flag for exact_match or included characters.
        hookup_cols : str, list
            List of hookup columns to use, or 'all'.

        Returns
        -------
        str
            Status string.  "OK" or "Not on 'main'"

        """
        import os.path

        if hlist[0].lower() == "default":
            hlist = cm_sysdef.hera_zone_prefixes
        output_file = os.path.expanduser("~/.hera_mc/sys_conn_tmp.html")
        hookup_obj = cm_hookup.Hookup(self.session)
        hookup_dict = hookup_obj.get_hookup(
            hpn=hlist,
            pol="all",
            at_date="now",
            exact_match=exact_match,
            hookup_type=None,
        )
        hookup_obj.show_hookup(
            hookup_dict=hookup_dict,
            cols_to_show=hookup_cols,
            state="full",
            ports=True,
            revs=True,
            sortby=sortby,
            filename=output_file,
            output_format="html",
        )

    def get_apriori_status_for_antenna(
        self, antenna, at_date="now", at_time=None, float_format=None
    ):
        """
        Get the "apriori" status of an antenna station (e.g. HH12) at a date.

        The status enum list may be found by module
        cm_partconnect.get_apriori_antenna_status_enum().

        Parameters
        ----------
        ant : str
            Antenna station designator (e.g. HH12, HA330) it is a single string
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information.
        float_format : str
            Format if at_date is a number denoting gps or unix seconds or jd day.

        Returns
        -------
        str
            The apriori antenna status as a string.  Returns None if not in table.

        """
        ant = antenna.upper()
        at_date = cm_utils.get_astropytime(at_date, at_time, float_format).gps
        cmapa = cm_partconnect.AprioriAntenna
        apa = (
            self.session.query(cmapa)
            .filter(
                or_(
                    and_(
                        func.upper(cmapa.antenna) == ant,
                        cmapa.start_gpstime <= at_date,
                        cmapa.stop_gpstime.is_(None),
                    ),
                    and_(
                        func.upper(cmapa.antenna) == ant,
                        cmapa.start_gpstime <= at_date,
                        cmapa.stop_gpstime > at_date,
                    ),
                )
            )
            .first()
        )
        if apa is not None:
            return apa.status

    def get_apriori_antennas_with_status(
        self, status, at_date="now", at_time=None, float_format=None
    ):
        """
        Get a list of all antennas with the provided status query at_date.

        Parameters
        ----------
        status : str
            Apriori antenna status type (see cm_partconnect.get_apriori_antenna_status_enum())
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information.
        float_format : str
            Format if at_date is a number denoting gps or unix seconds or jd day.

        Returns
        -------
        list of str
            List of the antenna station designators with the specified status.

        """
        at_date = cm_utils.get_astropytime(at_date, at_time, float_format).gps
        ap_ants = []
        cmapa = cm_partconnect.AprioriAntenna
        for apa in self.session.query(cmapa).filter(
            or_(
                and_(
                    cmapa.status == status,
                    cmapa.start_gpstime <= at_date,
                    cmapa.stop_gpstime.is_(None),
                ),
                and_(
                    cmapa.status == status,
                    cmapa.start_gpstime <= at_date,
                    cmapa.stop_gpstime > at_date,
                ),
            )
        ):
            ap_ants.append(apa.antenna)
        return ap_ants

    def get_apriori_antenna_status_set(
        self, at_date="now", at_time=None, float_format=None
    ):
        """
        Get a dictionary with the antennas for each apriori status type.

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information.
        float_format : str
            Format if at_date is a number denoting gps or unix seconds or jd day.

        Returns
        -------
        dict
            dictionary of antennas, keyed on the apriori antenna status value
            containing the antennas with that status value

        """
        ap_stat = {}
        for _status in cm_partconnect.get_apriori_antenna_status_enum():
            ap_stat[_status] = self.get_apriori_antennas_with_status(
                _status, at_date=at_date, at_time=at_time, float_format=float_format
            )
        return ap_stat

    def get_apriori_antenna_status_for_rtp(
        self, status, at_date="now", at_time=None, float_format=None
    ):
        """
        Get a csv-string of all antennas for an apriori status for RTP.

        Parameters
        ----------
        status : str
            Apriori antenna status type (see cm_partconnect.get_apriori_antenna_status_enum())
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information.
        float_format : str
            Format if at_date is a number denoting gps or unix seconds or jd day.

        Returns
        -------
        str
            csv string of antennas of a given apriori status

        """
        return ",".join(
            self.get_apriori_antennas_with_status(
                status=status,
                at_date=at_date,
                at_time=at_time,
                float_format=float_format,
            )
        )


def node_antennas(source="file", session=None):
    """
    Get the antennas associated with nodes.

    If source (as string) is 'file' it will use the 'nodes.txt' file of designed nodes.
    If source (as string) is 'hookup', it will find them via the current hookup.
    if source is a hookup instance, it will use that instance.

    Parameters
    ----------
    source : str or hookup instance
        Source of node antennas - either 'file' or 'hookup' or a hookup

    Returns
    -------
    dict
        Antennas per node key.
    """
    ants_per_node = {}
    if isinstance(source, str) and source.lower().startswith("f"):
        from . import geo_sysdef

        node = geo_sysdef.read_nodes()
        for this_node in node.keys():
            node_hpn = "N{:02d}".format(this_node)
            ants_per_node[node_hpn] = []
            for ant in node[this_node]["ants"]:
                if ant in geo_sysdef.region["heraringa"]:
                    prefix = "HA"
                elif ant in geo_sysdef.region["heraringb"]:
                    prefix = "HB"
                else:
                    prefix = "HH"
                ants_per_node[node_hpn].append("{}{}".format(prefix, ant))
    else:
        if isinstance(source, str) and source.lower().startswith("h"):
            source = cm_hookup.Hookup(session=session)
        hu_dict = source.get_hookup(
            cm_sysdef.hera_zone_prefixes, hookup_type="parts_hera"
        )
        for this_ant, vna in hu_dict.items():
            key = vna.hookup["E<ground"][-1].downstream_part
            if key[0] != "N":
                continue
            ants_per_node.setdefault(key, [])
            ants_per_node[key].append(cm_utils.split_part_key(this_ant)[0])
    return ants_per_node


def _get_dict_elements(npk, hu, ele_a, ele_b):
    """Return the appropriate hookup elements for node_info."""
    e_ret = {ele_a.lower(): "", ele_b.lower(): ""}
    try:
        e_hookup = hu[npk].hookup["@<middle"]
    except KeyError:
        return e_ret
    for element in e_hookup:
        if element.upstream_part.startswith(ele_a.upper()):
            e_ret[ele_a.lower()] = element.upstream_part
            e_ret[ele_b.lower()] = element.downstream_part
            break
        elif element.upstream_part.startswith(ele_b.upper()):
            e_ret[ele_b.lower()] = element.upstream_part
    return e_ret


def _find_ant_node(pnsearch, na_dict):
    found_node = None
    for node, antennas in na_dict.items():
        for ant in antennas:
            antint = cm_utils.peel_key(ant, "NPR")[0]
            if pnsearch == antint:
                if found_node is not None:
                    raise ValueError(
                        "Antenna {} already listed in node {}".format(
                            pnsearch, found_node
                        )
                    )
                else:
                    found_node = node
    return found_node


def which_node(ant_num, session=None):
    """
    Find node for antenna.

    Parameters
    ----------
    ant_num : int or list of int or csv-list or hyphen-range str
        Antenna numbers, as int

    Returns
    -------
    dict
        Contains antenna and node
    """
    na_from_file = node_antennas("file", session=session)
    na_from_hookup = node_antennas("hookup", session=session)
    ant_num = cm_utils.listify(ant_num)
    ant_node = {}
    for pn in ant_num:
        pnint = cm_utils.peel_key(str(pn), "NPR")[0]
        ant_node[pnint] = [_find_ant_node(pnint, na_from_file)]
        ant_node[pnint].append(_find_ant_node(pnint, na_from_hookup))
    return ant_node


def print_which_node(ant_node):
    """
    Print formatted 'which_node' print string.

    Parameter
    ---------
    ant_node : dict
        Dictionary returned from method 'which_node'.
    """
    print(formatted__which_node__string(ant_node))


def formatted__which_node__string(ant_node):
    """
    Return formatted 'which_node' print string.

    Parameter
    ---------
    ant_node : dict
        Dictionary returned from method 'which_node'.

    Returns
    -------
    str
        Formatted print string.
    """
    print_str = ""
    for ant, node in ant_node.items():
        if node[0] is not None:
            if node[1] is None:
                print_str += "Antenna {}:  Not installed ({})\n".format(ant, node[0])
            elif node[1] == node[0]:
                print_str += "Antenna {}:  {}\n".format(ant, node[0])
            else:
                print_str += "Warning:  Antenna {}\n\tSpecified for {}\n".format(
                    ant, node[0]
                )
                print_str += "\tInstalled in {}".format(node[1])
        else:
            print_str += "Warning:  Antenna {} not specified for a node.\n".format(ant)
            if node[1] is not None:
                print_str += "\tBut shown as installed in {}\n".format(node[1])
    return print_str


def node_info(node_num="active", session=None):
    """
    Generate information per node.

    Parameters
    ----------
    node_num : list of int or str (can be mixed), or str
        Node numbers, as int or hera part number.
        If 'active', use list of active nodes.
        if 'all', use list of all.

    Returns
    -------
    dict
        Contains node and node component information
    """
    hu = cm_hookup.Hookup(session)
    na_from_file = node_antennas("file", session=session)
    na_from_hookup = node_antennas(hu, session=session)

    if node_num == "active":
        node_num = sorted(na_from_hookup)
    elif node_num == "all":
        node_num = sorted(na_from_file)
    info = {"nodes": []}
    for node in node_num:
        # Set up
        if isinstance(node, int):
            node = "N{:02d}".format(node)
        npk = cm_utils.make_part_key(node, "A")
        info["nodes"].append(node)
        info[node] = {}
        # Get antenna info
        info[node]["ants-file"] = na_from_file[node] if node in na_from_file else []
        info[node]["ants-hookup"] = (
            na_from_hookup[node] if node in na_from_hookup else []
        )

        # Get hookup info
        snaps = hu.get_hookup(node, hookup_type="parts_hera")
        wr = hu.get_hookup(node, hookup_type="wr_hera")
        rd = hu.get_hookup(node, hookup_type="arduino_hera")

        # Find snaps
        info[node]["snaps"] = ["", "", "", ""]
        for snp in snaps.keys():
            loc = int(snaps[snp].hookup["E<e2"][-1].downstream_input_port[-1])
            info[node]["snaps"][loc] = cm_utils.split_part_key(snp)[0]
        # Find white rabbit, arduino and node control module
        wr_ret = _get_dict_elements(npk, wr, "wr", "ncm")
        info[node]["wr"] = wr_ret["wr"]
        rd_ret = _get_dict_elements(npk, rd, "rd", "ncm")
        info[node]["arduino"] = rd_ret["rd"]
        info[node]["ncm"] = ""
        if (
            len(wr_ret["ncm"]) and len(rd_ret["ncm"]) and wr_ret["ncm"] != rd_ret["ncm"]
        ):  # pragma: no cover
            raise ValueError(
                "NCMs don't match for node {}:  {} vs {}".format(
                    node, wr_ret["ncm"], rd_ret["ncm"]
                )
            )
        elif len(wr_ret["ncm"]):
            info[node]["ncm"] = wr_ret["ncm"]
        elif len(rd_ret["ncm"]):  # pragma: no cover
            info[node]["ncm"] = rd_ret["ncm"]

        # Get notes
        notes = hu.get_notes(snaps, state="all", return_dict=True)
        for snp in info[node]["snaps"]:
            spk = cm_utils.make_part_key(snp, "A")
            try:
                snnt = notes[spk][spk]
                info[snp] = [f"{snnt[x]['note']}|{x}" for x in snnt.keys()]
            except KeyError:
                info[snp] = []
        notes = hu.get_notes(wr, state="all", return_dict=True)
        wpk = cm_utils.make_part_key(info[node]["wr"], "A")
        try:
            wrnt = notes[npk][wpk]
            info[info[node]["wr"]] = [f"{wrnt[x]['note']}|{x}" for x in wrnt.keys()]
        except KeyError:
            info[info[node]["wr"]] = []
        notes = hu.get_notes(rd, state="all", return_dict=True)
        apk = cm_utils.make_part_key(info[node]["arduino"], "A")
        try:
            rdnt = notes[npk][apk]
            info[info[node]["arduino"]] = [
                f"{rdnt[x]['note']}|{x}" for x in rdnt.keys()
            ]
        except KeyError:
            info[info[node]["arduino"]] = []
        if "" in info.keys():
            del info[""]
    return info


def _get_macip(info, which_dev, which_id):
    """Find the last entry (by timestamp) for e.g. arduino and mac."""
    try:
        notes = info[which_dev]
    except KeyError:
        return "None"
    latest_timestamp = 0
    data = "None"
    for this_note in notes:
        if this_note.strip().lower().startswith(which_id.lower()):
            this_timestamp = int(this_note.split("|")[1])
            if this_timestamp > latest_timestamp:
                latest_timestamp = this_timestamp
                data = this_note.split("|")[0].split("-")[1].strip()
    return data


def _convert_ant_list(alist):
    ants = [int(x.strip("HH").strip("HA").strip("HB")) for x in alist]
    ants = sorted(ants)
    ants = [str(x) for x in ants]
    ants = ",".join(ants)
    return ants


def print_node(info, filename=None, output_format="table"):
    """Print node info as determined in method node_info above."""
    headers = ["Node", "SNAPs", "NCM", "WR", "Arduino"]
    spacer = [5 * "-", 47 * "-", 5 * "-", 17 * "-", 17 * "-"]
    table_data = []
    for node in info["nodes"]:
        is_there = 0
        for hdr in headers[1:]:
            is_there += len(info[node][hdr.lower()])
        if not is_there:
            continue
        # ############# WR
        this_wr = info[node]["wr"]
        wr_mac = _get_macip(info, this_wr, "mac")
        wr_ip = _get_macip(info, this_wr, "ip")
        # ############# RD
        this_rd = info[node]["arduino"]
        rd_mac = _get_macip(info, this_rd, "mac")
        rd_ip = _get_macip(info, this_rd, "ip")
        # ############# SNP and entry
        for i in range(4):
            try:
                this_snp = info[node]["snaps"][i]
            except (IndexError, KeyError):
                this_snp = "None"
            snp_mac = _get_macip(info, this_snp, "mac")
            snp_ip = _get_macip(info, this_snp, "ip")
            snp_entry = f"{this_snp} - {snp_mac}, {snp_ip}"
            if i == 0:
                row = [node, snp_entry, info[node]["ncm"], this_wr, this_rd]
            elif i == 1:
                row = ["", snp_entry, "", wr_mac, rd_mac]
            elif i == 2:
                row = ["", snp_entry, "", wr_ip, rd_ip]
            else:
                row = ["", snp_entry, "", "", ""]
            table_data.append(row)
        ants = _convert_ant_list(info[node]["ants-file"])
        table_data.append(["Ants", ants, "", "", ""])
        ants = _convert_ant_list(info[node]["ants-hookup"])
        table_data.append(["Conn", ants, "", "", ""])
        table_data.append(spacer)
    table = cm_utils.general_table_handler(headers, table_data, output_format)
    if filename is not None:  # pragma: no cover
        with open(filename, "w") as fp:
            print(table, file=fp)
    else:
        print(table)
