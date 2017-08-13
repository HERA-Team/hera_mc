# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Returns cm revisions

"""

from __future__ import absolute_import, print_function

from tabulate import tabulate
from hera_mc import cm_utils, part_connect
import warnings

def get_revisions_of_type(rev_type, hpn, at_date=None, session=None):
    """
    Returns list of revisions of queried type.
    Allowed types are:  LAST, FULL[Y_CONNECTED], ALL, PARTICULAR

    Parameters:
    ------------
    rev_type:  string for revision type
    hpn:  string for hera part number
    session:  db session
    """

    rq = rev_type.upper()
    if rq[:4] == 'LAST':
        return get_last_revision(hpn, session)
    
    if rq[0:4] == 'FULL':   #FULLY_CONNECTED'
        if at_date is None:
            raise Exception('To find FULLY_CONNECTED revisions, you must supply an astropyTime')
        else:
            return get_contemporary_revision(hpn, at_date, session)

    if rq[0] == 'ALL':
        return get_all_revisions(hpn, session)
    
    return get_particular_revision(rq, hpn, session)

def check_revisions(hpn, session=None):
    """
    Checks hpn for parts that overlap in time.  Should be none.
    """

    overlap = []
    revisions = get_all_revisions(hpn, session)
    for k1, r1 in revisions.iteritems():
        for k2, r2 in revisions.iteritems():
            if k1 == k2:
                continue
            first_one = k1 if r1['started']<=r2['started'] else k2
            second_one = k1 if r1['started']>r2['started'] else k2
            if revisions[first_one]['ended'] is None:
                revisions[first_one]['ended'] = cm_utils._get_astropytime('>')
            if revisions[second_one]['started']>revisions[first_one]['ended']:
                overlap.append([k1,k2])

    if len(overlap)>0:
        for ol in overlap:
            warnings.warn('Warning:  {} and {} are overlapping revisions of part {}'.format(ol[0],ol[1]))

def show_revisions(hpn, session=None):
    """
    Show revisions for hera part number

    Parameters:
    -------------
    hpn:  string of hera part number
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
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
    """
    Returns list of latest revision

    Parameters:
    -------------
    hpn:  string of hera part number
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    latest_end = cm_utils._get_astropytime('<')
    no_end = []
    for rev in revisions.keys():
        end_date = revisions[rev]['ended']
        if end_date is None:
            latest_end = cm_utils._get_astropytime('>')
            num_no_end.append(rev, revisions[rev]['started'], revisions[rev]['ended'])
        elif end_date > latest_end:
            latest_rev = rev
            latest_end = end_date
    if len(no_end) > 0:
        if len(no_end) > 1:
            warnings.warn("Warning:  {} has multiple open revisions.  Returning all open.".format(hpn))
        return no_end
    else:
        return [[latest_rev, revisions[latest_rev]['started'], revisions[latest_rev]['ended']]]


def get_all_revisions(hpn, session=None):
    """
    Returns list of all revisions

    Parameters:
    -------------
    hpn:  string of hera part number
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    sort_rev = sorted(revisions.keys())
    all_rev = []
    for rev in sort_rev:
        start_date = revisions[rev]['started']
        end_date = revisions[rev]['ended']
        all_rev.append([rev, start_date, end_date])
    return all_rev


def get_particular_revision(rq, hpn, session=None):
    """
    Returns info on particular revision

    Parameters:
    -------------
    rq:  revision number to find
    hpn:  string of hera part number
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    sort_rev = sorted(revisions.keys())
    this_rev = None
    if rq in sort_rev:
        start_date = revisions[rq]['started']
        end_date = revisions[rq]['ended']
        this_rev = [[rq, start_date, end_date]]
    return this_rev


def get_contemporary_revision(hpn, at_date, session=None):
    """
    Returns list of contemporary revisions

    Parameters:
    -------------
    hpn:  string of hera part number
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    sort_rev = sorted(revisions.keys())
    return_contemporary = None
    for rev in sort_rev:
        started = revisions[rev]['started']
        ended = revisions[rev]['ended']
        if cm_utils._is_active(at_date, started, ended):
            return_contemporary = [[rev, started, ended]]
            break
    return return_contemporary
