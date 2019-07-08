# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This module defines all of the system parameters for hookup.  It tries to
contain all of the ad hoc messy part of walking through a signal chain to
this one file.

The two-part "meta" assumption is that:
    a) polarized ports start with one of the polarization characters ('e' or 'n')
    b) non polarized ports don't start with either character.
"""

from __future__ import absolute_import, division, print_function
import six
from argparse import Namespace


class Sysdef:
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

    # Various dictionaries needed for next_connection below
    _D = Namespace(port={'up': 'out', 'down': 'in'},
                   this={'up': 'down', 'down': 'up'},
                   next={'up': 'up', 'down': 'down'},
                   arrow={'up': -1, 'down': 1})

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
        y = {}
        for x in self.checking_order:
            y[x] = v0
        return y

    def _to_dict(self):
        """
        Convert this object to a dict (so it can be written to json)
        """
        return {'pind': self.pind, 'this_hookup_type': self.this_hookup_type,
                'corr_index': self.corr_index, 'all_pols': self.all_pols,
                'redirect_part_types': self.redirect_part_types,
                'single_pol_labeled_parts': self.single_pol_labeled_parts,
                'full_connection_path': self.full_connection_path}

    def handle_redirect_part_types(self, part, at_date='now', session=None):
        """
        This handles the "special cases" by feeding a new part list back to hookup.
        """
        hpn_list = []
        if part.part_type.lower() == 'node':
            from hera_mc import cm_handling, cm_utils
            rptc = cm_handling.Handling(session)
            conn = rptc.get_part_connection_dossier(part.hpn, part.rev, port='all', at_date=at_date, exact_match=True)
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
        if hookup_type in self.port_def.keys():
            return hookup_type
        if hookup_type is None:
            for hookup_type in self.checking_order:
                if part_type in self.port_def[hookup_type].keys():
                    return hookup_type
        raise ValueError("hookup_type {} is not found.".format(hookup_type))

    def setup(self, part, port_query='all', hookup_type=None):
        """
        Given the current part and port_query (which is either 'all', 'e', or 'n')
        this figures out which pols to do.  Basically, given the part and query it
        figures out whether to return ['e*'], ['n*'], or ['e*', 'n*']

        Parameter:
        -----------
        part:  current part dossier
        port_query:  the ports that were requested ('e' or 'n' or 'all')
        hookup_type:  if not None, will use specified hookup_type
                      otherwise it will look through in order
        """
        self.this_hookup_type = hookup_type
        if hookup_type is None:
            self.this_hookup_type = self.find_hookup_type(part.part_type, None)
        for i, _p in enumerate([x.lower() for x in self.all_pols[self.this_hookup_type]]):
            self.pind[_p] = i

        all_pols_lo = [x.lower() for x in self.all_pols[self.this_hookup_type]]
        port_query = port_query.lower()
        port_check_list = all_pols_lo + ['all']
        if port_query not in port_check_list:
            raise ValueError("Invalid port query {}.  Should be in {}".format(port_query, port_check_list))

        # These are for single pol parts that have their polarization as the last letter of the part name
        # This is only for parts_paper parts at this time.  Not a good idea going forward.
        if part.part_type in self.single_pol_labeled_parts[self.this_hookup_type]:
            en_part_pol = part.hpn[-1].lower()
            if port_query == 'all' or en_part_pol == port_query:
                self.pol = [en_part_pol]
            else:
                self.pol = None
            return

        # Sort out all of the ports into a 'pol_catalog'.
        pol_catalog = {}
        for dir in ['up', 'down']:
            pol_catalog[dir] = {'e': [], 'n': [], 'a': [], 'o': []}
        connected_ports = {'up': part.connections.input_ports, 'down': part.connections.output_ports}
        for dir in ['up', 'down']:
            for cp in connected_ports[dir]:
                cp = cp.lower()
                cp_poldes = 'o' if cp[0] not in all_pols_lo else cp[0]
                if cp_poldes in all_pols_lo:
                    pol_catalog[dir]['a'].append(cp)  # p = e + n
                pol_catalog[dir][cp_poldes].append(cp)
        up = pol_catalog['up'][port_query[0]]
        dn = pol_catalog['down'][port_query[0]]

        if (len(up) + len(dn)) == 0:  # The part handles both polarizations
            self.pol = all_pols_lo if port_query == 'all' else port_query
        else:
            self.pol = up if len(up) > len(dn) else dn

    def next_connection(self, connection_options, current, A, B):
        """
        This checks the options and returns the next connection.
        """

        # This sets up the parameters to check for the next part/port
        this_part_info = self.port_def[self.this_hookup_type][A.part_type]
        next_part_position = this_part_info['position'] + self._D.arrow[current.direction]
        if next_part_position < 0 or next_part_position > len(self.full_connection_path[self.this_hookup_type]) - 1:
            return None
        next_part_type = self.full_connection_path[self.this_hookup_type][next_part_position]
        next_part_info = self.port_def[self.this_hookup_type][next_part_type]
        if len(next_part_info[self._D.this[current.direction]]) == 1:
            allowed_next_ports = next_part_info[self._D.this[current.direction]][0]
        elif len(next_part_info[self._D.this[current.direction]]) == 2:
            allowed_next_ports = next_part_info[self._D.this[current.direction]][self.pind[current.pol]]
        options = []
        # prefix is defined to handle the single_pol_labeled_parts
        prefix_this = A.hpn[-1].lower() if A.part_type in self.single_pol_labeled_parts[self.this_hookup_type] else ''
        for i, opc in enumerate(connection_options):
            if B[i].part_type != next_part_type:
                continue
            prefix_next = B[i].hpn[-1].lower() if next_part_type in self.single_pol_labeled_parts[self.this_hookup_type] else ''
            this_port = prefix_this
            this_port += getattr(opc, '{}stream_{}put_port'.format(self._D.this[current.direction], self._D.port[self._D.this[current.direction]]))
            next_port = prefix_next
            next_port += getattr(opc, '{}stream_{}put_port'.format(self._D.next[current.direction], self._D.port[self._D.next[current.direction]]))
            if next_port[0] == '@':
                continue
            if len(connection_options) == 1 and next_port in allowed_next_ports:
                return opc
            this = Namespace(part=A.hpn, port=this_port, type=A.part_type, prefix=prefix_this)
            next = Namespace(part=B[i].hpn, port=next_port, type=B[i].part_type, prefix=prefix_next)
            options.append(Namespace(this=this, next=next, option=opc, pol=current.pol))

        # This runs through the Namespace to find the actual part/port
        #    First pass is to check for the specific port-sets that pass
        for opt in options:
            check_next_port = opt.next.port.strip(opt.next.prefix)
            if current.port == opt.this.port and check_next_port in allowed_next_ports:
                return opt.option
        #    Second pass checks for matching the leading polarization character.
        for opt in options:
            check_next_port = opt.next.port.strip(opt.next.prefix)
            if current.pol[0] == opt.this.port[0] and check_next_port in allowed_next_ports:
                return opt.option
