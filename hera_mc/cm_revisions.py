# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Returns cm revisions

"""

from __future__ import absolute_import, print_function

from tabulate import tabulate

from hera_mc import cm_utils, part_connect

def __get_part_revisions(hpn, session=None):
    """
    Retrieves revision numbers for a given part (exact match).
    """
    if hpn is None:
        return None
    close_session_when_done = False
    if session is None:
        db = mc.connect_mc_db()
        session = db.sessionmaker()
        close_session_when_done = True

    revisions = {}
    for parts_rec in session.query(Parts).filter(Parts.hpn == hpn):
        parts_rec.gps2Time()
        revisions[parts_rec.hpn_rev] = {}
        revisions[parts_rec.hpn_rev]['hpn'] = hpn  # Just carry this along
        revisions[parts_rec.hpn_rev]['started'] = parts_rec.start_date
        revisions[parts_rec.hpn_rev]['ended'] = parts_rec.stop_date
    if close_session_when_done:
        session.close()

    return revisions

def get_revisions_of_type(rev_type, hpn, session=None):
    rq = rev_type.upper()
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
    revisions = __get_part_revisions(hpn, session)
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
    revisions = __get_part_revisions(hpn, session)
    latest_end = cm_utils._get_datetime('<')
    num_no_end = 0
    for rev in revisions.keys():
        end_date = revisions[rev]['ended']
        if end_date is None:
            latest_rev = rev
            latest_end = cm_utils.__get_datetime('>')
            num_no_end+=1
        elif end_date > latest_end:
            latest_rev = rev
            latest_end = end_date
    if num_no_end > 1:
        print("Warning:  {} has multiple open revisions.  Return None".format(hpn))
        return_rev = None
    else:
        return_rev = [[latest_rev, revisions[rev]['started'], revisions[rev]['ended']]]

    return return_rev


def get_all_revisions(hpn, session=None):
    revisions = __get_part_revisions(hpn, session)
    sort_rev = sorted(revisions.keys())
    all_rev = []
    for rev in sort_rev:
        start_date = revisions[rev]['started']
        end_date = revisions[rev]['ended']
        all_rev.append([rev, start_date, end_date])
    return all_rev


def get_particular_revision(rq, hpn, session=None):
    revisions = __get_part_revisions(hpn, session)
    sort_rev = sorted(revisions.keys())
    this_rev = None
    if rq in sort_rev:
        start_date = revisions[rq]['started']
        end_date = revisions[rq]['ended']
        this_rev = [[rq, start_date, end_date]]
    return this_rev


def get_contemporary_revision(hpn, session=None):
    current = cm_utils._get_datetime(args.date,args.time)
    revisions = __get_part_revisions(hpn, session)
    sort_rev = sorted(revisions.keys())
    return_contemporary = None
    for rev in sort_rev:
        started = revisions[rev]['started']
        ended = revisions[rev]['ended']
        if cm_utils._is_active(current, started, ended):
            return_contemporary = [[rev, started, ended]]
            break
    return return_contemporary
