# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function
import six
from argparse import Namespace
from hera_mc import cm_utils


class Sysdef:
    """
    This class defines the system architecture for the telescope array.  The intent is to
    have all of the specific defining parameters here in one place.  If a new system is required,
    this may be extended by defining the parameters here.

    The two-part "meta" assumption is that:
        a) polarized ports start with one of the polarization characters ('e' or 'n')
        b) non polarized ports don't start with either character.
    """
    opposite_direction = {'up': 'down', 'down': 'up'}
    port_def = {}
    port_def['parts_hera'] = {
        'station': {'up': [[None]], 'down': [['ground']], 'position': 0},
        'antenna': {'up': [['ground']], 'down': [['focus']], 'position': 1},
        'feed': {'up': [['input']], 'down': [['terminals']], 'position': 2},
        'front-end': {'up': [['input']], 'down': [['e'], ['n']], 'position': 3},
        'node-bulkhead': {'up': [['e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7', 'e8', 'e9', 'e10', 'e11', 'e12'],
                                 ['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7', 'n8', 'n9', 'n10', 'n11', 'n12']],
                          'down': [['e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7', 'e8', 'e9', 'e10', 'e11', 'e12'],
                                   ['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7', 'n8', 'n9', 'n10', 'n11', 'n12']],
                          'position': 4},
        'post-amp': {'up': [['e'], ['n']], 'down': [['e'], ['n']], 'position': 5},
        'snap': {'up': [['e2', 'e6', 'e10'], ['n0', 'n4', 'n8']], 'down': [['rack']], 'position': 6},
        'node': {'up': [['loc0', 'loc1', 'loc2', 'loc3']], 'down': [[None]], 'position': 7}
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
        'snap': {'up': [['e2', 'e6', 'e10'], ['n0', 'n4', 'n8']], 'down': [['rack']], 'position': 4},
        'node': {'up': [['loc0', 'loc1', 'loc2', 'loc3']], 'down': [[None]], 'position': 5}
    }
    port_def['parts_test'] = {
        'vapor': {'up': [[None]], 'down': [[None]], 'position': 0}
    }
    checking_order = ['parts_hera', 'parts_rfi', 'parts_paper', 'parts_test']

    def __init__(self, input_dict=None):
        if input_dict is not None:
            self.pind = input_dict['pind']
            self.this_hookup_type = input_dict['this_hookup_type']
            self.corr_index = input_dict['corr_index']
            self.all_pols = input_dict['all_pols']
            self.redirect_part_types = input_dict['redirect_part_types']
            self.single_pol_labeled_parts = input_dict['single_pol_labeled_parts']
            self.full_connection_path = input_dict['full_connection_path']
        else:
            self.pind = {}
            self.this_hookup_type = None

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
            self.single_pol_labeled_parts['parts_paper'] = ['cable-post-amp(in)', 'cable-post-amp(out)', 'cable-receiverator']

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
        Initializes the system dict to v0.  Note that v0 is set by the calling
        function.

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
        Convert this object to a dict (so it can be written to json)

        Returns
        -------
        dict
            Dictionary version of object.
        """
        return {'pind': self.pind, 'this_hookup_type': self.this_hookup_type,
                'corr_index': self.corr_index, 'all_pols': self.all_pols,
                'redirect_part_types': self.redirect_part_types,
                'single_pol_labeled_parts': self.single_pol_labeled_parts,
                'full_connection_path': self.full_connection_path}

    def handle_redirect_part_types(self, part, at_date='now', session=None):
        """
        This handles the "special cases" by feeding a new part list back to hookup.

        Parameters
        ----------
        part : Part object
            Part object of current part.

        Returns
        -------
        list
            List of redirected part numbers.
        """
        hpn_list = []
        if part.part_type.lower() == 'node':
            print("CMSD160:  redirect not yet handled.")
            from hera_mc import cm_hookup
            # rptc = cm_handling.Handling(session)
            # conn = rptc.get_part_connection_dossier(part.hpn, part.rev, port='all', at_date=at_date, exact_match=True)
            conn = {}
            redirect_list = []
            for _k in conn.keys():
                _pk = cm_utils.split_part_key(_k)[0]
                if _pk.upper() == part.hpn.upper():
                    redirect_list.append(_k)
            for _r in redirect_list:
                for _x in conn[_r].keys_up:
                    if _x.upper().startswith('SNP'):
                        hpn_list.append(cm_utils.split_connection_key(_x)[0])
        return hpn_list

    def find_hookup_type(self, part_type, hookup_type):
        """
        Returns the relevant hookup_type.  This is almost a complete trivial method, but
        it does serve a function for supplying a different hookup_type if needed.

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
        Given the current part and pol (which is either 'all', 'e', or 'n')
        this figures out which pols to do.  Basically, given the part and query it
        figures out whether to return ['e*'], ['n*'], or ['e*', 'n*']

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
        self.this_hookup_type = hookup_type
        if hookup_type is None:
            self.this_hookup_type = self.find_hookup_type(part.hptype, None)
        for i, _p in enumerate([x.lower() for x in self.all_pols[self.this_hookup_type]]):
            self.pind[_p] = i

        all_pols_upper = [x.upper() for x in self.all_pols[self.this_hookup_type]]
        pol = cm_utils.to_upper(pol)
        port_check_list = all_pols_upper + ['ALL']
        if pol not in port_check_list:
            raise ValueError("Invalid port query {}.  Should be in {}".format(pol, port_check_list))

        # These are for single pol parts that have their polarization as the last letter of the part name
        # This is only for parts_paper parts at this time.  Not a good idea going forward.
        if part.hptype in self.single_pol_labeled_parts[self.this_hookup_type]:
            en_part_pol = part.hpn[-1].lower()
            if pol == 'all' or en_part_pol == pol:
                self.pol = [en_part_pol]
            else:
                self.pol = None
            return

        self.pol = all_pols_upper if pol == 'ALL' else pol

    def get_ports(self, pol, part_type):
        """
        This will return a list of appropriate current ports for a given part-type,
        direction, and pol request.  The up and down lists are made equal length

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
            for port_list in self.port_def[self.this_hookup_type][part_type][dir]:
                for port in port_list:
                    if port is None:
                        port_dict[dir].append(None)
                    elif port[0].lower() not in self.all_pols[self.this_hookup_type] or pol.lower() == 'all':
                        port_dict[dir].append(port.upper())
                    elif port[0].lower() == pol[0].lower():
                        port_dict[dir].append(port.upper())
        return port_dict
