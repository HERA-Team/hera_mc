#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Methods to load all active data for a given date."""

from . import cm_utils
from . import cm_partconnect as partconn


class ActiveData:
    """
    Object containing the active parts and connections for a given date.

    Parameters
    ----------
    at_date : str, int, float, Time, datetime

    """

    def __init__(self, session=None, at_date="now", at_time=None, float_format=None):
        """
        Initialize ActiveData class attributes for at_date.

        It creates all attributes and sets them to None.  Another attribute
        'pytest_param' is set within to allow for fine-grained unit testing
        without the need for an init argument.  It allows for certain keys to
        be set in the method 'load_connections' to check edge cases.

        Parameters
        ----------
        session : session object or None
            If None, it will start a new session on the database.
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information
        float_format : str
            Format if at_date is a number denoting gps or unix seconds or jd day.
        """
        if session is None:  # pragma: no cover
            from . import mc

            db = mc.connect_to_mc_db(None)
            session = db.sessionmaker()
        self.session = session
        self.at_date = cm_utils.get_astropytime(at_date, at_time, float_format)
        self.reset_all()
        self.pytest_param = False

    def reset_all(self):
        """Reset all active attributes to None."""
        self.parts = None
        self.rosetta = None
        self.connections = None
        self.info = None
        self.apriori = None
        self.geo = None

    def set_active_time(self, at_date, at_time=None, float_format=None):
        """
        Make sure that at_date and self.at_date are synced and supplies gps time.

        This utility function checks that the Class date hasn't changed.  If so,
        then it will reset all of the Attributes.

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date for which to check.  If none, returns self.at_date.gps
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information
        float_format : str
            Format if at_date is a number denoting gps, unix seconds, or jd

        Returns
        -------
        int
            gps seconds of at_date

        """
        if at_date is not None:
            this_date = cm_utils.get_astropytime(at_date, at_time, float_format)
            if abs(this_date.gps - self.at_date.gps) > 1:
                self.at_date = this_date
                self.reset_all()
        return self.at_date.gps

    def load_parts(self, at_date=None, at_time=None, float_format=None):
        """
        Retrieve all active parts for a given at_date.

        Loads the active parts onto the class and sets the class at_date.
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.parts - keyed on part:rev

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information
        float_format : str
            Format if at_date is a number denoting gps, unix seconds or jd

        """
        gps_time = self.set_active_time(at_date, at_time, float_format)
        self.parts = {}
        for prt in self.session.query(partconn.Parts).filter(
            (partconn.Parts.start_gpstime <= gps_time)
            & (
                (partconn.Parts.stop_gpstime > gps_time)
                | (partconn.Parts.stop_gpstime == None)  # noqa
            )
        ):
            key = cm_utils.make_part_key(prt.hpn, prt.hpn_rev)
            self.parts[key] = prt
            self.parts[key].logical_pn = None

    def load_connections(self, at_date=None, at_time=None, float_format=None):
        """
        Retrieve all active connections for a given at_date.

        Loads the active parts onto the class and sets the class at_date.
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.connections - has keys 'up' and 'down', each of which
                                   is a dictionary keyed on part:rev for
                                   upstream_part and downstream_part respectively.

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information
        float_format : str
            Format if at_date is a number denoting gps, unix seconds or jd

        Raises
        ------
        ValueError
            If a duplicate is found.

        """
        gps_time = self.set_active_time(at_date, at_time, float_format)
        self.connections = {"up": {}, "down": {}}
        check_keys = {"up": [], "down": []}
        for cnn in self.session.query(partconn.Connections).filter(
            (partconn.Connections.start_gpstime <= gps_time)
            & (
                (partconn.Connections.stop_gpstime > gps_time)
                | (partconn.Connections.stop_gpstime == None)  # noqa
            )
        ):
            chk = cm_utils.make_part_key(
                cnn.upstream_part, cnn.up_part_rev, cnn.upstream_output_port
            )
            if self.pytest_param:
                check_keys[self.pytest_param].append(chk)
            if chk in check_keys["up"]:
                raise ValueError("Duplicate active port {}".format(chk))
            check_keys["up"].append(chk)
            chk = cm_utils.make_part_key(
                cnn.downstream_part, cnn.down_part_rev, cnn.downstream_input_port
            )
            if chk in check_keys["down"]:
                raise ValueError("Duplicate active port {}".format(chk))
            check_keys["down"].append(chk)
            key = cm_utils.make_part_key(cnn.upstream_part, cnn.up_part_rev)
            self.connections["up"].setdefault(key, {})
            self.connections["up"][key][cnn.upstream_output_port.upper()] = cnn
            key = cm_utils.make_part_key(cnn.downstream_part, cnn.down_part_rev)
            self.connections["down"].setdefault(key, {})
            self.connections["down"][key][cnn.downstream_input_port.upper()] = cnn

    def load_info(self, at_date=None, at_time=None, float_format=None):
        """
        Retrieve all current part infomation (ie. before date).

        Loads the part information up to at_date onto the class and sets the class at_date
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.info - keyed on part:rev

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information
        float_format : str
            Format if at_date is a number denoting gps, unix seconds or jd

        """
        gps_time = self.set_active_time(at_date, at_time, float_format)
        self.info = {}
        for info in self.session.query(partconn.PartInfo).filter(
            (partconn.PartInfo.posting_gpstime <= gps_time)
        ):
            key = cm_utils.make_part_key(info.hpn, info.hpn_rev)
            self.info.setdefault(key, [])
            self.info[key].append(info)

    def load_rosetta(self, at_date=None, at_time=None, float_format=None):
        """
        Retrieve the current 'part rosetta' mappings.

        Note that the dictionary keys don't include revision numbers, which differs from others
        (if this is needed later, it can be added later).  If current parts are loaded, it adds the
        'syspn' to the part object (which does use the full hpn:rev key).

        Writes class dictionary:
            self.rosetta - keyed on part

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information
        float_format : str
            Format if at_date is a number denoting gps, unix seconds or jd

        Raises
        ------
        ValueError
            If a duplicate logical part name is found.

        """
        gps_time = self.set_active_time(at_date, at_time, float_format)
        self.rosetta = {}
        fnd_syspn = []
        for rose in self.session.query(partconn.PartRosetta).filter(
            (partconn.PartRosetta.start_gpstime <= gps_time)
            & (
                (partconn.PartRosetta.stop_gpstime > gps_time)
                | (partconn.PartRosetta.stop_gpstime == None)  # noqa
            )
        ):
            if rose.syspn in fnd_syspn:
                raise ValueError(
                    "System part number {} already found.".format(rose.syspn)
                )
            fnd_syspn.append(rose.syspn)
            self.rosetta[rose.hpn] = rose
        if self.parts is not None:
            for key, part in self.parts.items():
                try:
                    self.parts[key].syspn = self.rosetta[part.hpn].syspn
                except KeyError:
                    continue

    def load_apriori(self, at_date=None, at_time=None, float_format=None, rev="A"):
        """
        Retrieve all active apriori status for a given at_date.

        Loads the active apriori data onto the class and sets the class at_date.
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.apriori - keyed on part:rev

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information
        float_format : str
            Format if at_date is a number denoting gps, unix seconds or jd
        rev : str
            Revision of antenna-station (always A)

        """
        gps_time = self.set_active_time(at_date, at_time, float_format)
        self.apriori = {}
        apriori_keys = []
        for astat in self.session.query(partconn.AprioriAntenna).filter(
            (partconn.AprioriAntenna.start_gpstime <= gps_time)
            & (
                (partconn.AprioriAntenna.stop_gpstime > gps_time)
                | (partconn.AprioriAntenna.stop_gpstime == None)  # noqa
            )
        ):
            key = cm_utils.make_part_key(astat.antenna, rev)
            if key in apriori_keys:
                raise ValueError("{} already has an active apriori state.".format(key))
            apriori_keys.append(key)
            self.apriori[key] = astat

    def load_geo(self, at_date=None, at_time=None, float_format=None):
        """
        Retrieve all current geo_location data (ie. before date).

        Loads the geo data at_date onto the class and sets the class at_date.
        If at_date is None, the existing at_date on the object will be used.

        Writes class dictionary:
                self.geo - keyed on part

        Parameters
        ----------
        at_date : anything interpretable by cm_utils.get_astropytime
            Date at which to initialize.
        at_time : anything interpretable by cm_utils.get_astropytime
            Time at which to initialize, ignored if at_date is a float or contains time information
        float_format : str
            Format if at_date is a number denoting gps, unix seconds or jd

        """
        from . import geo_location

        gps_time = self.set_active_time(at_date, at_time, float_format)
        self.geo = {}
        for ageo in self.session.query(geo_location.GeoLocation).filter(
            geo_location.GeoLocation.created_gpstime <= gps_time
        ):
            key = cm_utils.make_part_key(ageo.station_name, None)
            self.geo[key] = ageo

    def get_hptype(self, hptype):
        """
        Return a list of all active parts of type hptype.

        Note that this assumes that self.load_parts() has been run and will error
        otherwise.  This is to keep the 'at_date' clearer.

        Parameters
        ----------
        hptype : str
            Valid HERA part type name (e.g. node, antenna, fem, ...)

        Returns
        -------
        list
            Contains all part number keys (hpn:rev) of that type.
        """
        hptype_list = []
        for key, partclass in self.parts.items():
            if partclass.hptype == hptype:
                hptype_list.append(key)
        return hptype_list

    def revs(self, hpn, exact_match=False):
        """
        Return a list of active revisions for the provided hpn list.

        The returned list is the concatentated set of revisions found for the provided list.

        The purpose is to find out what active revisions are present in the database.
        E.g., to check for all active revisions for all PAMs, call with hpn='PAM'.
        To check for revisions for a particular one, call with 'PAM123'.
        To guarantee only one part one should also set exact_match=True.

        Parameters
        ----------
        hpn : str or list
            HERA part number or list.  Checks equality or startswith, depending on below.
        exact_match : bool
            Flag to look for exact matches to part numbers or not.

        Returns
        -------
        list
            List of revision Namespaces for supplied hpn.
            Can show with cm_revisions.show_revisions

        """
        from argparse import Namespace

        hpn = [x.upper() for x in cm_utils.listify(hpn)]
        rev_dict = {}
        for hloop in hpn:
            rev_dict[hloop] = {}
            for part in self.parts.values():
                phup = part.hpn.upper()
                use_this_one = (
                    (phup == hloop) if exact_match else phup.startswith(hloop)
                )
                if use_this_one:
                    prup = part.hpn_rev.upper()
                    rev_dict[hloop].setdefault(
                        prup,
                        Namespace(
                            hpn=hloop,
                            rev=prup,
                            number=0,
                            started=part.start_gpstime,
                            ended=part.stop_gpstime,
                        ),
                    )
                    rev_dict[hloop][prup].number += 1
                    if part.start_gpstime < rev_dict[hloop][prup].started:
                        rev_dict[hloop][prup].started = part.start_gpstime
                    if rev_dict[hloop][prup].ended is not None:
                        if (
                            part.stop_gpstime is None
                            or part.stop_gpstime > rev_dict[hloop][prup].ended
                        ):
                            rev_dict[hloop][prup].ended = part.stop_gpstime
        hpn_rev = []
        for hloop in sorted(rev_dict.keys()):
            for rev in sorted(rev_dict[hloop].keys()):
                hpn_rev.append(rev_dict[hloop][rev])
        return hpn_rev
