# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Defines the system architecture for the telescope array."""
import json
import os.path

from . import cm_utils
from .data import DATA_PATH

with open(os.path.join(DATA_PATH, "sysdef.json"), "r") as fp:
    system_info = json.load(fp)
hera_zone_prefixes = system_info["hera_zone_prefixes"]


class Sysdef:
    """
    Defines the system architecture for the telescope array for given architecture.

    The two-part "meta" assumption is that:
        a) polarized ports start with one of the polarization characters ('e' or 'n')
        b) non polarized ports don't start with either character.

    Attributes
    ----------
    This section needs to be filled out.

    """

    opposite_direction = {"up": "down", "down": "up"}
    checking_order = [
        "parts_hera",
        "wr_hera",
        "arduino_hera",
        "parts_rfi",
        "parts_paper",
        "parts_test",
    ]

    def __init__(self, hookup_type=None, input_dict=None):
        self.port_def = system_info["hookup_types"]
        if input_dict is not None:
            self.hookup_type = input_dict["hookup_type"]
            self.corr_index = input_dict["corr_index"]
            self.all_pols = input_dict["all_pols"]
            self.redirect_part_types = input_dict["redirect_part_types"]
            self.single_pol_labeled_parts = input_dict["single_pol_labeled_parts"]
            self.full_connection_path = input_dict["full_connection_path"]
        else:
            self.hookup_type = hookup_type
            self.corr_index = {}
            self.all_pols = {}
            self.redirect_part_types = {}
            self.single_pol_labeled_parts = {}
            self.full_connection_path = {}
            for hutype in self.port_def.keys():
                this_sys = system_info["hookup_parameters"][hutype]
                self.corr_index[hutype] = this_sys["corr_index"]
                self.all_pols[hutype] = this_sys["all_pols"]
                self.redirect_part_types[hutype] = this_sys["redirect_part_types"]
                self.single_pol_labeled_parts[hutype] = this_sys[
                    "single_pol_labeled_parts"
                ]
                ordered_path = {}
                for k, v in self.port_def[hutype].items():
                    ordered_path[v["position"]] = k
                sorted_keys = sorted(ordered_path.keys())
                self.full_connection_path[hutype] = []
                for k in sorted_keys:
                    self.full_connection_path[hutype].append(ordered_path[k])

    def _to_dict(self):
        """
        Convert this object to a dict (so it can be written to json).

        Returns
        -------
        dict
            Dictionary version of object.

        """
        return {
            "hookup_type": self.hookup_type,
            "corr_index": self.corr_index,
            "all_pols": self.all_pols,
            "redirect_part_types": self.redirect_part_types,
            "single_pol_labeled_parts": self.single_pol_labeled_parts,
            "full_connection_path": self.full_connection_path,
        }

    def get_all_ports(self, hookup_types=None):
        """
        Get all ports for hookup_types.

        Parameters
        ----------
        hookup_type : list of str, or None
            Strings specifying which types of hookup to use.  If None, uses current.

        Returns
        -------
        list of str
            List of all ports in hookup_types.
        """
        all_ports = set()
        if hookup_types is None:
            hookup_types = [self.hookup_type]
        for hut in hookup_types:
            for key in self.port_def[hut].keys():
                for direction in ["up", "down"]:
                    for ports in self.port_def[hut][key][direction]:
                        for port in ports:
                            if port is not None:
                                all_ports.add(port)
        return list(all_ports)

    def handle_redirect_part_types(self, part, active):
        """
        Handle the "special cases" by feeding a new part list back to hookup.

        Parameters
        ----------
        part : Part object
            Part object of current part
        active : ActiveData object
            Contains the current data.

        Returns
        -------
        list
            List of redirected parts.

        """
        hpn_list = []
        if self.hookup_type == "parts_hera":
            if part.hptype.lower() == "node":
                try:
                    for conn in active.connections["down"][
                        cm_utils.make_part_key(part.hpn, part.hpn_rev)
                    ].values():
                        if conn.upstream_part.startswith("SNP"):
                            hpn_list.append(conn.upstream_part)
                except KeyError:
                    pass
        return hpn_list

    def find_hookup_type(self, part_type, hookup_type, set_for_class=True):
        """
        Return the relevant hookup_type.

        This is almost a complete trivial method, but it does serve a function
        for supplying a different hookup_type if needed.

        Parameters
        ----------
        part_type : str
            Part_type to check on, if no hookup_type is provided.
        hookup_type : str
            Hookup_type to return, if supplied.
        set_for_class : bool
            If True, set hookup_type as class variable.

        Returns
        -------
        str
            String for the hooukp_type
        """
        if hookup_type in self.port_def.keys():
            if set_for_class:
                self.hookup_type = hookup_type
            return hookup_type
        if hookup_type is None:
            for hookup_type in self.checking_order:
                if part_type in self.port_def[hookup_type].keys():
                    if set_for_class:
                        self.hookup_type = hookup_type
                    return hookup_type
        raise ValueError("hookup_type {} is not found.".format(hookup_type))

    def setup(self, part, pol="all", hookup_type=None):
        """
        Figure out which pols to do (???).

        Given the current part and pol (which is either 'all', 'e', or 'n')
        this figures out which pols to do.  Basically, given the part and query it
        figures out whether to return ['e*'], ['n*'], or ['e*', 'n*']

        This method doesn't return anything, it sets values on self.ppkeys.

        Parameter:
        -----------
        part : dict
            Current part info
        pol : str
            The ports that were requested ('e' or 'n' or 'all').  Default is 'all'
        hookup_type : str, None
            If not None, will use specified hookup_type otherwise it will look through in order.
            Default is None

        """
        self.hookup_type = hookup_type
        if hookup_type is None:
            self.hookup_type = self.find_hookup_type(part.hptype, None)

        all_pols = [x.upper() for x in self.all_pols[self.hookup_type]]
        pol = cm_utils.to_upper(pol)
        if pol not in all_pols + ["ALL"]:
            raise ValueError("Invalid port query {}.".format(pol))
        use_pols = all_pols if pol == "ALL" else [pol]

        try:
            port_up = self.port_def[self.hookup_type][part.hptype]["up"]
            port_dn = self.port_def[self.hookup_type][part.hptype]["down"]
        except KeyError:
            print(
                "Unmatched hookup and part:  {} and {}".format(
                    self.hookup_type, part.hptype
                )
            )
            self.ppkeys = []
            return
        dir2use = port_up if len(port_up) > len(port_dn) else port_dn
        if dir2use[0][0] is None:
            dir2use = port_up

        ppkey_list = []
        for pport_list in dir2use:
            for port in pport_list:
                if cm_utils.port_is_polarized(port, all_pols):
                    if cm_utils.port_is_polarized(port, use_pols):
                        ppkey_list.append(port)
                else:
                    ppkey_list.append(port)
        self.ppkeys = []

        for _pol in use_pols:
            for _port in ppkey_list:
                if cm_utils.port_is_polarized(_port, all_pols):
                    if cm_utils.port_is_polarized(_port, [_pol]):
                        self.ppkeys.append("{}<{}".format(_pol, _port))
                else:
                    self.ppkeys.append("{}<{}".format(_pol, _port))

    def get_ports(self, pol, part_type):
        """
        Get a dict of appropriate current ports given inputs.

        The up and down lists are made equal length

        Parameters
        ----------
        pol : str
            The pol request, either 'e', 'n' (or starts with those letters) or 'all'
        part_type : str
            Part type of current part

        Returns
        -------
        dict
            Dictionary keyed on 'up'/'down' listing appropriate ports

        """
        port_dict = {}
        for direction in ["up", "down"]:
            port_dict[direction] = []
            try:
                oports = self.port_def[self.hookup_type][part_type]
            except KeyError:
                return {}
            for port_list in oports[direction]:
                for port in port_list:
                    if port is None:
                        port_dict[direction].append(None)
                    elif (
                        port[0].lower() not in self.all_pols[self.hookup_type]
                        or pol.lower() == "all"
                    ):
                        port_dict[direction].append(port.upper())
                    elif port[0].lower() == pol[0].lower():
                        port_dict[direction].append(port.upper())
        return port_dict
