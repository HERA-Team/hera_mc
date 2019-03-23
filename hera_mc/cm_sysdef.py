# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
This module defines all of the system parameters for hookup.  It tries to
contain all of the ad hoc messy part of walking through a signal chain to
this one file.
"""

from __future__ import absolute_import, division, print_function
from . import cm_utils


checking_order = ["parts_hera", "parts_rfi", "parts_paper", "parts_test"]
full_connection_path = {"parts_paper": ["station", "antenna", "feed", "front-end",
                                        "cable-feed75", "cable-post-amp(in)",
                                        "post-amp", "cable-post-amp(out)",
                                        "cable-receiverator", "cable-container",
                                        "f-engine"],
                        "parts_hera": ["station", "antenna", "feed", "front-end",
                                       "cable-rfof", "post-amp", "snap", "node"],
                        "parts_rfi": ["station", "antenna", "feed", "temp-cable",
                                      "snap", "node"],
                        "parts_test": ["vapor"]
                        }
corr_index = {"parts_hera": 5, "parts_paper": 9, "parts_rfi": 3}
all_pols = ["e", "n"]
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
    that = {'up': 'up', 'down': 'down'}
    for opc in options:
        this_part = getattr(opc, '{}stream_part'.format(this[rg.direction]))
        this_port = getattr(opc, '{}stream_{}put_port'.format(this[rg.direction], port[this[rg.direction]]))
        next_part = getattr(opc, '{}stream_part'.format(that[rg.direction]))
        next_port = getattr(opc, '{}stream_{}put_port'.format(that[rg.direction], port[that[rg.direction]]))
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
