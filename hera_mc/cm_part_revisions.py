# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Returns cm revisions

"""

from __future__ import absolute_import, print_function

from tabulate import tabulate

from hera_mc import cm_utils, part_connect


def get_revisions_of_type(rev_query, hpn, session=None):
    rq = rev_query.upper()
    if rq == 'LAST':
        rq = get_last_revision(hpn, session)
    elif rq == 'ACTIVE':
        rq = get_contemporary_revision(hpn, session)
    elif rq == 'ALL':
        rq = get_all_revisions(hpn, session)
    else:
        rq = get_particular_revision(rq, hpn, session)
    return rq


def show_revisions(hpn, session=None):
    revisions = part_connect.__get_part_revisions(session, hpn)
    sort_rev = sorted(revisions.keys())
    headers = ['HPN', 'Revision', 'Start', 'Stop']
    table_data = []
    for rev in sort_rev:
        started = revisions[rev]['started']
        ended = revisions[rev]['ended']
        table_data.append([hpn, rev, started, ended])
    print(tabulate(table_data, headers=headers, tablefmt='simple'))
    print('\n')


def get_last_revision(hpn, session=None):
    revisions = part_connect.__get_part_revisions(session, hpn)
    sort_rev = sorted(revisions.keys())
    start_date = revisions[sort_rev[-1]]['started']
    end_date = revisions[sort_rev[-1]]['ended']
    return [[sort_rev[-1], start_date, end_date]]


def get_all_revisions(hpn, session=None):
    revisions = part_connect.__get_part_revisions(session, hpn)
    sort_rev = sorted(revisions.keys())
    all_rev = []
    for rev in sort_rev:
        start_date = revisions[rev]['started']
        end_date = revisions[rev]['ended']
        all_rev.append([rev, start_date, end_date])
    return all_rev


def get_particular_revision(rq, hpn, session=None):
    revisions = part_connect.__get_part_revisions(session, hpn)
    sort_rev = sorted(revisions.keys())
    this_rev = None
    if rq in sort_rev:
        start_date = revisions[rq]['started']
        end_date = revisions[rq]['ended']
        this_rev = [[rq, start_date, end_date]]
    return this_rev


def get_contemporary_revision(hpn, session=None):
    current = cm_utils._get_datetime(args.date,args.time)
    revisions = part_connect.__get_part_revisions(session, hpn)
    sort_rev = sorted(revisions.keys())
    return_contemporary = None
    for rev in sort_rev:
        started = revisions[rev]['started']
        ended = revisions[rev]['ended']
        if cm_utils._is_active(current, started, ended):
            return_contemporary = [[rev, started, ended]]
            break
    return return_contemporary
