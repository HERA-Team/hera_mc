# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Defines the system architecture for the telescope array."""

from __future__ import absolute_import, division, print_function
import six
from hera_mc import cm_utils

hera_zone_prefixes = ['HH', 'HA', 'HB']
all_port_types = ['sigpath', 'physical']


class Sysdef:
    """
    Defines the system architecture for the telescope array.

    The intent is to have all of the specific defining parameters here in one place.
    If a new system is required, this may be extended by defining the parameters here.

    This only defines the signal path ports.

    The two-part "meta" assumption is that:
        a) polarized ports start with one of the polarization characters ('e' or 'n')
        b) non polarized ports don't start with either character.

    Attributes
    ----------
    This section needs to be filled out.

    """

    opposite_direction = {'up': 'down', 'down': 'up'}
    port_def = {}
    port_def['parts_hera'] = {
        'station': {'up': [[None]], 'down': [['ground']], 'position': 0},
        'antenna': {'up': [['ground']], 'down': [['focus']], 'position': 1},
        'feed': {'up': [['input']], 'down': [['terminals']], 'position': 2},
        'front-end': {'up': [['input']], 'down': [['e'], ['n']], 'position': 3},
        'node-bulkhead': {'up': [['e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7',
                                  'e8', 'e9', 'e10', 'e11', 'e12'],
                                 ['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7',
                                  'n8', 'n9', 'n10', 'n11', 'n12']],
                          'down': [['e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7',
                                    'e8', 'e9', 'e10', 'e11', 'e12'],
                                   ['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7',
                                    'n8', 'n9', 'n10', 'n11', 'n12']],
                          'position': 4},
        'post-amp': {'up': [['e'], ['n']], 'down': [['e'], ['n']], 'position': 5},
        'snap': {'up': [['e2', 'e6', 'e10'], ['n0', 'n4', 'n8']],
                 'down': [['rack']], 'position': 6},
        'node': {'up': [['loc0', 'loc1', 'loc2', 'loc3']], 'down': [[None]], 'position': 7}
    }
    port_def['node_hera'] = {
        'node': {'up': [['loc0', 'loc1', 'loc2', 'loc3']], 'down': [[None]], 'position': 2},
        'node-control-module': {'up': [['mnt1', 'mnt2']], 'down': [['rack']], 'position': 1},
        'snap': {'up': [[None]], 'down': [['rack']], 'position': 0},
        'white-rabbit': {'up': [[None]], 'down': [['mnt']], 'position': 0},
        'arduino': {'up': [[None]], 'down': [['mnt']], 'position': 0}
    }
    port_def['parts_paper'] = {
        'station': {'up': [[None]], 'down': [['ground']], 'position': 0},
        'antenna': {'up': [['ground']], 'down': [['focus']], 'position': 1},
        'feed': {'up': [['input']], 'down': [['terminals']], 'position': 2},
        'front-end': {'up': [['input']], 'down': [['e'], ['n']], 'position': 3},
        'cable-feed75': {'up': [['ea'], ['na']], 'down': [['eb'], ['nb']], 'position': 4},
        'cable-post-amp(in)': {'up': [['a']], 'down': [['b']], 'position': 5},
        'post-amp': {'up': [['ea'], ['na']], 'down': [['eb'], ['nb']], 'position': 6},
        'cable-post-amp(out)': {'up': [['a']], 'down': [['b']], 'position': 7},
        'cable-receiverator': {'up': [['a']], 'down': [['b']], 'position': 8},
        'cable-container': {'up': [['a']], 'down': [['b']], 'position': 9},
        'f-engine': {'up': [['input']], 'down': [[None]], 'position': 10}
    }
    port_def['parts_rfi'] = {
        'station': {'up': [[None]], 'down': [['ground']], 'position': 0},
        'antenna': {'up': [['ground']], 'down': [['focus']], 'position': 1},
        'feed': {'up': [['input']], 'down': [['terminals']], 'position': 2},
        'temp-cable': {'up': [['ea'], ['na']], 'down': [['eb'], ['nb']], 'position': 3},
        'snap': {'up': [['e2', 'e6', 'e10'], ['n0', 'n4', 'n8']],
                 'down': [['rack']], 'position': 4},
        'node': {'up': [['loc0', 'loc1', 'loc2', 'loc3']], 'down': [[None]], 'position': 5}
    }
    port_def['parts_test'] = {
        'vapor': {'up': [[None]], 'down': [[None]], 'position': 0}
    }
    checking_order = ['parts_hera', 'node_hera', 'parts_rfi', 'parts_paper', 'parts_test']

    def __init__(self, hookup_type=None, input_dict=None):
        if input_dict is not None:
            self.hookup_type = input_dict['hookup_type']
            self.corr_index = input_dict['corr_index']
            self.all_pols = input_dict['all_pols']
            self.redirect_part_types = input_dict['redirect_part_types']
            self.single_pol_labeled_parts = input_dict['single_pol_labeled_parts']
            self.full_connection_path = input_dict['full_connection_path']
        else:
            self.hookup_type = hookup_type

            # Initialize the dictionaries
            self.corr_index = self.dict_init(None)
            self.all_pols = self.dict_init([])
            self.redirect_part_types = self.dict_init([])
            self.single_pol_labeled_parts = self.dict_init([])

            # Redefine dictionary as needed
            #    Define which component corresponds to the correlator input.
            self.corr_index['parts_hera'] = 6
            self.corr_index['parts_paper'] = 10
            self.corr_index['parts_rfi'] = 4
            #    Define polarization designations (should be one character)
            self.all_pols['parts_hera'] = ['e', 'n']
            self.all_pols['parts_paper'] = ['e', 'n']
            self.all_pols['parts_rfi'] = ['e', 'n']
            #    Define "special" parts for systems.  These require additional checking/processing
            for hutype in self.port_def.keys():
                self.redirect_part_types[hutype] = []
                self.single_pol_labeled_parts[hutype] = []
            self.redirect_part_types['parts_hera'] = ['node']
            self.redirect_part_types['node_hera'] = ['node-control-module']
            self.single_pol_labeled_parts['parts_paper'] = [
                'cable-post-amp(in)', 'cable-post-amp(out)', 'cable-receiverator']

            # This generates the full_connection_path dictionary from port_def
            self.full_connection_path = {}
            for _x in self.port_def.keys():
                ordered_path = {}
                for k, v in six.iteritems(self.port_def[_x]):
                    ordered_path[v['position']] = k
                sorted_keys = sorted(list(ordered_path.keys()))
                self.full_connection_path[_x] = []
                for k in sorted_keys:
                    self.full_connection_path[_x].append(ordered_path[k])

    def dict_init(self, v0):
        """
        Initialize the system dict to v0.

        Note that v0 is set by the calling function.

        Parameters
        ----------
        v0 : str
            Initialization parameter as defined in the calling function.

        Returns
        -------
        dict
            Initialized dictionary.

        """
        y = {}
        for x in self.checking_order:
            y[x] = v0
        return y

    def _to_dict(self):
        """
        Convert this object to a dict (so it can be written to json).

        Returns
        -------
        dict
            Dictionary version of object.

        """
        return {'hookup_type': self.hookup_type,
                'corr_index': self.corr_index, 'all_pols': self.all_pols,
                'redirect_part_types': self.redirect_part_types,
                'single_pol_labeled_parts': self.single_pol_labeled_parts,
                'full_connection_path': self.full_connection_path}

    def get_all_ports(self, hookup_types):
        """
        Get all ports for hookup_types.

        Parameters
        ----------
        hookup_type : list of str
            Strings specifying which types of hookup to use, should be in operational_hookup_types.

        Returns
        -------
        list of str
            List of all ports in hookup_types.
        """
        all_ports = []
        for hut in hookup_types:
            for key in self.port_def[hut].keys():
                for dir in ['up', 'down']:
                    for ports in self.port_def[hut][key][dir]:
                        for port in ports:
                            if port is not None:
                                all_ports.append(port)
        return all_ports

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
        if self.hookup_type == 'parts_hera':
            if part.hptype.lower() == 'node':
                for conn in active.connections['down'][cm_utils.make_part_key(
                        part.hpn, part.hpn_rev)].values():
                    if conn.upstream_part.startswith('SNP'):
                        hpn_list.append(conn.upstream_part)
        if self.hookup_type == 'node_hera':
            if part.hptype.lower() == 'node-control-module':
                print("CM_SYSDEF222:  Need to make this work.")
        return hpn_list

    def find_hookup_type(self, part_type, hookup_type):
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

        Returns
        -------
        str
            String for the hooukp_type
        """
        if hookup_type in self.port_def.keys():
            return hookup_type
        if hookup_type is None:
            for hookup_type in self.checking_order:
                if part_type in self.port_def[hookup_type].keys():
                    return hookup_type
        raise ValueError("hookup_type {} is not found.".format(hookup_type))

    def setup(self, part, pol='all', hookup_type=None):
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
        if pol not in all_pols + ['ALL']:
            raise ValueError("Invalid port query {}.".format(pol))
        use_pols = all_pols if pol == 'ALL' else [pol]

        port_up = self.port_def[self.hookup_type][part.hptype]['up']
        port_dn = self.port_def[self.hookup_type][part.hptype]['down']
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
                        self.ppkeys.append('{}<{}'.format(_pol, _port))
                else:
                    self.ppkeys.append('{}<{}'.format(_pol, _port))

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
        for dir in ['up', 'down']:
            port_dict[dir] = []
            try:
                oports = self.port_def[self.hookup_type][part_type]
            except KeyError:
                return {}
            for port_list in oports[dir]:
                for port in port_list:
                    if port is None:
                        port_dict[dir].append(None)
                    elif (port[0].lower() not in self.all_pols[self.hookup_type]
                          or pol.lower() == 'all'):
                        port_dict[dir].append(port.upper())
                    elif port[0].lower() == pol[0].lower():
                        port_dict[dir].append(port.upper())
        return port_dict

    def node(self, node_nums):
        """
        Get the antennas associated with a set of nodes.

        Given a list of node_nums, returnes the associated antennas as per the
        data file 'nodes.txt'

        Parameters
        ----------
        node_nums : list
            Integers of the desired node numbers.

        Returns
        -------
        list
            Strings of the antenna hpns within those nodes.

        """
        from . import geo_sysdef
        node = geo_sysdef.read_nodes()
        ants = []
        for nd in node_nums:
            for ant in node[int(nd)]['ants']:
                if ant in geo_sysdef.region['heraringa']:
                    prefix = 'HA'
                elif ant in geo_sysdef.region['heraringb']:
                    prefix = 'HB'
                else:
                    prefix = 'HH'
                ants.append("{}{}".format(prefix, ant))
        return ants
