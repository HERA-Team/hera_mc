#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Utility scripts to display dossier information.

Actions 'parts', 'connections', and 'notes' differ only by defining a different set of columns,
which may be overridden by instead using the args.columns parameter (see cm_dossier.PartEntry
for allowed columns.)

"""
from __future__ import absolute_import, division, print_function

from hera_mc import mc, cm_handling, cm_utils

all_views = {'p': 'parts', 'c': 'connections', 'n': 'notes', 'r': 'revisions'}

parser = mc.get_mc_argument_parser()
parser.add_argument('view', nargs='?', help="Views are:  {}.  Need first letter only.\
                    ".format(', '.join(all_views.values())), default='parts')
# set values for 'action' to use
parser.add_argument('-p', '--hpn', help="Part number or portion thereof, csv list.")
parser.add_argument('-r', '--revision', help="Revision for hpn, or None for active.", default=None)
parser.add_argument('-e', '--exact-match', help="Force exact matches on part numbers, not beginning N char. [False]",
                    dest='exact_match', action='store_true')
parser.add_argument('--columns', help="Custom columns as csv list.  Use '--list-all-columns' for options.", default=None)
parser.add_argument('--list-all-columns', dest='list_columns', help="Show a list of all available columns", action='store_true')
parser.add_argument('--hide-sigpath', dest='sigpath', help="Hide signal path ports", action='store_false')
parser.add_argument('--hide-phys', dest='phys', help="Hide physical ports", action='store_false')
parser.add_argument('--ports', help="Include only these ports, csv list", default=None)
cm_utils.add_verbosity_args(parser)
cm_utils.add_date_time_args(parser)
parser.add_argument('--notes-start-date', dest='notes_start_date', help="<For notes> start_date for notes [<]",
                    default='<')
parser.add_argument('--notes-start-time', dest='notes_start_time', help="<For notes> start_time for notes",
                    default=0.0)
args = parser.parse_args()

args.verbosity = cm_utils.parse_verbosity(args.verbosity)
view = all_views[args.view[0].lower()] if not args.list_all_columns else 'all-columns'
args.hpn = cm_utils.listify(args.hpn)
date_query = cm_utils.get_astropytime(args.date, args.time)
notes_start_date = cm_utils.get_astropytime(args.notes_start_date, args.notes_start_time)

# Start session
db = mc.connect_to_mc_db(args)
session = db.sessionmaker()

if view == 'all-columns':
    from hera_mc import cm_dossier
    blank = cm_dossier.PartEntry(None, None)
    for col in blank.col_hdr.keys():
        print('\t{:30s}\t{}'.format(col, blank.col_hdr[col]))
elif view == 'revisions':
    for hpn in args.hpn:
        rev_ret = cm_handling.cmrev.get_revisions_of_type(hpn, args.revision, date_query, session)
        cm_handling.cmrev.show_revisions(rev_ret)
else:
    handling = cm_handling.Handling(session)
    if view == 'parts':
        if args.verbosity == 1:
            columns = ['hpn', 'hpn_rev', 'hptype', 'input_ports', 'output_ports']
        elif args.verbosity == 2:
            columns = ['hpn', 'hpn_rev', 'hptype', 'manufacturer_number', 'start_gpstime', 'stop_gpstime',
                       'input_ports', 'output_ports', 'geo']
        else:
            columns = ['hpn', 'hpn_rev', 'hptype', 'manufacturer_number', 'start_gpstime', 'stop_gpstime',
                       'input_ports', 'output_ports', 'geo', 'comment']
    elif view == 'connections':
        if args.verbosity == 1:
            columns = ['up.upstream_part', 'up.upstream_output_port', 'up.downstream_input_port',
                       'hpn',
                       'down.upstream_output_port', 'down.downstream_input_port', 'down.downstream_part']
        elif args.verbosity == 2:
            columns = ['up.upstream_part', 'up.up_part_rev', 'up.upstream_output_port', 'up.downstream_input_port',
                       'hpn', 'hpn_rev',
                       'down.upstream_output_port', 'down.downstream_input_port', 'down.downstream_part', 'down.down_part_rev']
        else:
            columns = ['up.start_gpstime', 'up.stop_gpstime', 'up.upstream_part', 'up.up_part_rev',
                       'up.upstream_output_port', 'up.downstream_input_port',
                       'hpn', 'hpn_rev',
                       'down.upstream_output_port', 'down.downstream_input_port', 'down.downstream_part', 'down.down_part_rev',
                       'down.start_gpstime', 'down.stop_gpstime']
    elif view == 'notes':
        if args.verbosity == 1:
            columns = ['hpn', 'posting_gpstime', 'comment']
        elif args.verbosity == 2:
            columns = ['hpn', 'posting_gpstime', 'comment']
        else:
            columns = ['hpn', 'posting_gpstime', 'reference', 'comment']

    if args.columns is not None:
        columns = args.columns
    if args.ports is not None:
        ports = args.ports.split(',')
    else:
        ports = []
        if args.sigpath:
            ports.append('sigpath')
        if args.phys:
            ports.append('physical')
        ports = ','.join(ports)

    dossier = handling.get_dossier(hpn=args.hpn, rev=args.revision, at_date=date_query,
                                   notes_start_date=notes_start_date, exact_match=args.exact_match)
    print(handling.show_dossier(dossier, columns, ports=ports))
