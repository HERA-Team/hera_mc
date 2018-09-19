#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""script to control power of node elements (snaps, fem, pam)

"""
from __future__ import absolute_import, division, print_function

import sys
from astropy.time import Time

from hera_mc import mc, cm_utils, node

valid_part_names = list(node.power_command_part_dict.keys())

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.description = """Power on or off node elements (snaps, fem, pam)"""
    parser.add_argument('nodes', help="list of nodes to command "
                        "(integers, comma-separated, no spaces) or 'active'")
    parser.add_argument('parts', help="list of parts to command "
                        "(comma-separated, no spaces) or 'all'."
                        " Valid part names are: " + ' ,'.join(valid_part_names) + ".")
    parser.add_argument('command', help="command: 'on' or 'off'.")
    parser.add_argument('--address', help="address for node server", default=None)
    parser.add_argument('--dryrun', help="just print the list of NodePowerCommand "
                        "objects, do not issue the power commands or log them "
                        "to the database' [False]", action='store_true')
    parser.add_argument('--testing', help="Testing: do not use anything that "
                        "requires connection to nodes (implies dryrun)' [False]",
                        action='store_true')

    args = parser.parse_args()
    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    if args.nodes.lower() == 'active':
        from hera_mc import node
        node_list = node.get_node_list(nodeServerAddress=args.address)
    else:
        node_list = cm_utils.listify(args.nodes)
        node_list = [int(node) for node in node_list]

    parts_list = cm_utils.listify(args.parts)

    for nodeID in node_list:
        command_list = session.node_power_command(nodeID, parts_list, args.command,
                                                  nodeServerAddress=args.address,
                                                  dryrun=args.dryrun,
                                                  testing=args.testing)
        if args.testing or args.dryrun:
            for cmd in command_list:
                print(cmd)
        session.commit()
