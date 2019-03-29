# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This module defines all of the system parameters for hookup.  It tries to
contain all of the ad hoc messy part of walking through a signal chain to
this one file.
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
    'station': {'position': 0},
    'antenna': {'position': 1},
    'feed': {'position': 2},
    'front-end': {'position': 3},
    'cable-feed75': {'position': 4},
    'cable-post-amp(in)': {'position': 5},
    'post-amp': {'position': 6},
    'cable-post-amp(out)': {'position': 7},
    'cable-receiverator': {'position': 8},
    'cable-container': {'position': 9},
    'f-engine': {'position': 10}
}
port_def['parts_rfi'] = {
    'station': {'position': 0},
    'antenna': {'position': 1},
    'feed': {'position': 2},
    'temp-cable': {'position': 3},
    'snap': {'position': 4},
    'node': {'position': 5}
}
port_def['parts_test'] = {
    'vapor': {'position': 0}
}

full_connection_path = {}
for _x in port_def.keys():
    ordered_path = {}
    for k, v in six.iteritems(port_def[_x]):
        ordered_path[v['position']] = k
    sorted_keys = sorted(list(ordered_path.keys()))
    full_connection_path[_x] = []
    for k in sorted_keys:
        full_connection_path[_x].append(ordered_path[k])

checking_order = ['parts_hera', 'parts_rfi', 'parts_paper', 'parts_test']

corr_index = {'parts_hera': 6, 'parts_paper': 10, 'parts_rfi': 4}
all_pols = ['e', 'n']
redirect_part_types = ['node']


def handle_redirect_part_types(part):
    print("Redirected parts require that you determine the set of parts externally and re-run.")
    print("\t\tFor this part type:  'parts.py conn -p {}'".format(part.hpn))
    print("\t\tThen re-run hookup with a csv list of parts.")


def get_port_pols_to_do(part, port_query):
    """
    Given the current part and port_query (which is either 'all', 'e', or 'n')
    this figures out which pols to do.  Basically, given 'pol' and part it
    figures out whether to return ['e'], ['n'], ['e', 'n'], etc

    Parameter:
    -----------
    part:  current part dossier
    port_query:  the ports that were requested ('e' or 'n' or 'all')
    """

    all_pols_lo = [x.lower() for x in all_pols]
    port_query = port_query.lower()
    if port_query.startswith('pol'):  # This is a legacy
        port_query = 'all'
    port_check_list = all_pols_lo + ['all']
    if port_query not in port_check_list:
        print("Invalid port query {}.  Should be in {}".format(port_query, port_check_list))
        return None

    # These are parts that have their polarization as the last letter of the part name
    # This is only for legacy PAPER parts.
    legacy_single_pol_EN_parts = ['RI', 'RO', 'CR']
    if part.hpn[:2].upper() in legacy_single_pol_EN_parts:
        en_part_pol = part.hpn[-1].lower()
        if port_query == 'all' or en_part_pol == port_query.lower():
            return [en_part_pol]
        else:
            return None

    pol_cat = {'other': []}
    for p in all_pols_lo:
        pol_cat[p] = []
    nport = {'in': len(part.connections.input_ports), 'out': len(part.connections.output_ports)}
    check_ports = part.connections.input_ports if nport['in'] > nport['out'] else part.connections.output_ports
    tot_polarized_ports = 0
    for p in check_ports:
        if p[0] == '@':
            continue
        if p[0].lower() in all_pols_lo:
            pol_cat[p[0]].append(p.lower())
            tot_polarized_ports += 1
        else:
            pol_cat['other'].append(p.lower())

    if tot_polarized_ports == 0:
        if port_query == 'all':
            return all_pols_lo
        else:
            return port_query

    if port_query == 'all':
        allports = []
        for p in all_pols_lo:
            for x in pol_cat[p]:
                allports.append(x)
        return allports

    return pol_cat[port_query]


def next_connection(options, rg):
    """
    This checks the options and returns the next part.
    """

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
        all_pols_lo = [x.lower() for x in all_pols]
        p = None
        if next_port.lower() in ['a', 'b']:  # This or part of the PAPER legacy
            p = next_part[-1].lower()
        elif next_port[0].lower() in all_pols_lo:
            p = next_port[0].lower()
        if p == rg.pol:
            return opc
