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

port_def = {}
port_def['parts_hera'] = {
    'station': {'up': [[None]], 'down': [['ground']], 'position': 0},
    'antenna': {'up': [['ground']], 'down': [['focus']], 'position': 1},
    'feed': {'up': [['input']], 'down': [['terminals']], 'position': 2},
    'front-end': {'up': [['input']], 'down': [['e'], ['n']], 'position': 3},
    'cable-rfof': {'up': [['ea'], ['na']], 'down': [['eb'], ['nb']], 'position': 4},
    'post-amp': {'up': [['ea'], ['na']], 'down': [['eb'], ['nb']], 'position': 5},
    'snap': {'up': [['e2', 'e6', 'e10'], ['n0', 'n4', 'n8']], 'down': [['rack']], 'position': 6},
    'node': {'up': [['loc1', 'loc2', 'loc3', 'loc4']], 'down': [[None]], 'position': 7}
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
    'node': {'up': [['loc1', 'loc2', 'loc3', 'loc4']], 'down': [[None]], 'position': 5}
}
port_def['parts_test'] = {
    'vapor': {'up': [[None]], 'down': [[None]], 'position': 0}
}


def sys_init(husys, v0):
    y = {}
    for x in husys:
        y[x] = v0
    return y


checking_order = ['parts_hera', 'parts_rfi', 'parts_paper', 'parts_test']
# Initialize the dictionaries
corr_index = sys_init(checking_order, None)
all_pols = sys_init(checking_order, [])
redirect_part_types = sys_init(checking_order, [])
single_pol_labeled_parts = sys_init(checking_order, [])

# Redefine dictionary as needed
corr_index['parts_hera'] = 6
corr_index['parts_paper'] = 10
corr_index['parts_rfi'] = 4
# polarizations should be one character
all_pols['parts_hera'] = ['e', 'n']
all_pols['parts_paper'] = ['e', 'n']
all_pols['parts_rfi'] = ['e', 'n']
redirect_part_types['parts_hera'] = ['node']
single_pol_labeled_parts['parts_paper'] = ['cable-post-amp(in)', 'cable-post-amp(out)', 'cable-receiverator']


this_hookup_type = None

full_connection_path = {}
for _x in port_def.keys():
    ordered_path = {}
    for k, v in six.iteritems(port_def[_x]):
        ordered_path[v['position']] = k
    sorted_keys = sorted(list(ordered_path.keys()))
    full_connection_path[_x] = []
    for k in sorted_keys:
        full_connection_path[_x].append(ordered_path[k])


def handle_redirect_part_types(part):
    print("{} parts requires that you determine connections externally.".format(part.part_type))
    print("\t\tFor this part type:  'parts.py conn -p {}'".format(part.hpn))
    print("\t\tThen re-run hookup with a csv list of appropriate parts.")


def find_hookup_type(part_type, hookup_type):
    if hookup_type in port_def.keys():
        return hookup_type
    if hookup_type is None:
        for hookup_type in checking_order:
            if part_type in port_def[hookup_type].keys():
                return hookup_type
    raise ValueError("hookup_type {} is not found.".format(hookup_type))


def setup(part, port_query='all', hookup_type=None):
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
    if hookup_type is None:
        raise ValueError("Need hookup_type.")
    global this_hookup_type
    this_hookup_type = hookup_type

    all_pols_lo = [x.lower() for x in all_pols[this_hookup_type]]
    port_query = port_query.lower()
    port_check_list = all_pols_lo + ['all']
    if port_query not in port_check_list:
        raise ValueError("Invalid port query {}.  Should be in {}".format(port_query, port_check_list))

    # These are for single pol parts that have their polarization as the last letter of the part name
    # This is only for parts_paper parts at this time.
    # Not a good idea going forward.
    if part.part_type in single_pol_labeled_parts[this_hookup_type]:
        en_part_pol = part.hpn[-1].lower()
        if port_query == 'all' or en_part_pol == port_query:
            return [en_part_pol], 'parts_paper'
        else:
            return None

    # Sort out all of the ports into 'pol_catalog' and add up all of the "polarized" ports
    # It also makes a version of consolidated port_def ports
    # This is currently over-elaborate, but trying to improve then will slim back down
    pol_catalog = {}
    consolidated_ports = {'up': [], 'down': []}
    for dir in ['up', 'down']:
        pol_catalog[dir] = {'e': [], 'n': [], 'a': [], 'o': []}
        for _c in port_def[this_hookup_type][part.part_type][dir]:
            consolidated_ports[dir] += _c
    connected_ports = {'up': part.connections.input_ports, 'down': part.connections.output_ports}
    tot_polarized_ports = 0
    for dir in ['up', 'down']:
        for cp in connected_ports[dir]:
            cp = cp.lower()
            if cp not in consolidated_ports[dir]:
                continue
            cp_poldes = 'o' if cp[0] not in all_pols_lo else cp[0]
            if cp_poldes in all_pols_lo:
                pol_catalog[dir]['a'].append(cp)  # p = e + n
                tot_polarized_ports += 1
            pol_catalog[dir][cp_poldes].append(cp)
    print("CHSD165:  ", pol_catalog)

    if tot_polarized_ports == 0:  # The part handles both polarizations
        if port_query == 'all':
            return all_pols_lo
        else:
            return port_query

    up = pol_catalog['up'][port_query[0]]
    dn = pol_catalog['down'][port_query[0]]
    return up if len(up) > len(dn) else dn


def next_connection(options, rg):
    """
    This checks the options and returns the next part.
    """
    global this_hookup_type
    port = {'up': 'out', 'down': 'in'}
    this = {'up': 'down', 'down': 'up'}
    next = {'up': 'up', 'down': 'down'}
    for opc in options:
        this_part = getattr(opc, '{}stream_part'.format(this[rg.direction]))
        this_port = getattr(opc, '{}stream_{}put_port'.format(this[rg.direction], port[this[rg.direction]]))
        next_part = getattr(opc, '{}stream_part'.format(next[rg.direction]))
        next_port = getattr(opc, '{}stream_{}put_port'.format(next[rg.direction], port[next[rg.direction]]))
        if next_port[0] == '@':
            continue
        if len(options) == 1:  # Assume the only option is correct
            return opc
        if this_port.lower() == rg.port.lower():
            return opc
        if len(rg.port) > 1 and rg.port[1].isdigit():
            continue
        all_pols_lo = [x.lower() for x in all_pols[this_hookup_type]]
        p = None
        if next_port.lower() in ['a', 'b']:  # This or part of the PAPER legacy
            p = next_part[-1].lower()
        elif next_port[0].lower() in all_pols_lo:
            p = next_port[0].lower()
        if p == rg.pol:
            return opc
