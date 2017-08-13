# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Returns cm revisions

"""

from __future__ import absolute_import, print_function

from tabulate import tabulate
from hera_mc import cm_utils, part_connect
import warnings
from argparse import Namespace


def get_revisions_of_type(rev_type, hpn, at_date=None, session=None):
    """
    Returns namespace of revisions (hpn, rev, started, ended) of queried type.
    Allowed types are:  
        ACTIVE:  revisions that are not stopped at_date
        LAST:  the last connected revision (could be active or not) 
        FULL[Y_CONNECTED]:  revision that is part of a fully connected signal path at_date
        ALL:  all revisions
        PARTICULAR:  check for a particular version

    Parameters:
    ------------
    rev_type:  string for revision type
    hpn:  string for hera part number
    at_date:  astropy.Time to check for
    session:  db session
    """

    rq = rev_type.upper()
    if rq == 'LAST':
        return get_last_revision(hpn, session)

    if rq == 'ACTIVE':
        if at_date is None:
            raise Exception('To find ACTIVE revisions, you must supply an astropy.Time')
        else:
            return get_active_revision(hpn, at_date, session)

    if rq[0:4] == 'FULL':  # FULLY_CONNECTED'
        if at_date is None:
            raise Exception('To find FULLY_CONNECTED revisions, you must supply an astropy.Time')
        else:
            return get_full_revision(hpn, at_date, session)

    if rq == 'ALL':
        return get_all_revisions(hpn, session)

    return get_particular_revision(rq, hpn, session)


def check_revisions(hpn, session=None):
    """
    Checks hpn for parts that overlap in time.  Should be none.
    """

    overlap = []
    revisions = get_all_revisions(hpn, session)
    for i, r1 in enumerate(revisions):
        for j, r2 in enumerate(revisions):
            if i >= j:
                continue
            first_one = i if r1.started <= r2.started else j
            second_one = i if r1.started > r2.started else j
            if revisions[first_one].ended is None:
                revisions[first_one].ended = cm_utils._get_astropytime('>')
            if revisions[second_one].started > revisions[first_one].ended:
                overlap.append([r1, r2])
    if len(overlap) > 0:
        overlapping_revs_in_single_list = []
        for ol in overlap:
            overlapping_revs_in_single_list.append(ol[0])
            overlapping_revs_in_single_list.append(ol[1])
            print('\n\tWarning!!!  {} and {} are overlapping revisions of part {}\n\n'.format(
                ol[0].rev, ol[1].rev, hpn))
        show_revisions(overlapping_revs_in_single_list, session)


def show_revisions(rev_list):
    """
    Show revisions for provided revision list

    Parameters:
    -------------
    rev_list:  list as provided by one of the other methods
    """

    headers = ['HPN', 'Revision', 'Start', 'Stop']
    table_data = []
    for r in rev_list:
        table_data.append([r.hpn, r.rev, r.started, r.ended])
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
            no_end.append(Namespace(hpn=hpn, rev=rev, started=revisions[rev]['started'],
                                    ended=revisions[rev]['ended']))
        elif end_date > latest_end:
            latest_rev = rev
            latest_end = end_date
    if len(no_end) > 0:
        if len(no_end) > 1:
            s = "Warning:  {} has multiple open revisions.  Returning all open.".format(hpn)
            warnings.warn(s)
        return no_end
    else:
        return [Namespace(hpn=hpn, rev=latest_rev, started=revisions[latest_rev]['started'],
                          ended=revisions[latest_rev]['ended'])]


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
        started = revisions[rev]['started']
        ended = revisions[rev]['ended']
        all_rev.append(Namespace(hpn=hpn, rev=rev, started=started, ended=ended))
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
        this_rev = [Namespace(hpn=hpn, rev=rq, started=start_date, ended=end_date)]
    return this_rev


def get_active_revision(hpn, at_date, session=None):
    """
    Returns list of active revisions at_date

    Parameters:
    -------------
    hpn:  string of hera part number
    at_date:  date to check if fully connected
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    sort_rev = sorted(revisions.keys())
    return_active = []
    for rev in sort_rev:
        started = revisions[rev]['started']
        ended = revisions[rev]['ended']
        if cm_utils._is_active(at_date, started, ended):
            return_active.append(Namespace(hpn=hpn, rev=rev, started=started, ended=ended))
    if len(return_active) > 1:
        s = '{} has multiple active revisions at {}'.format(hpn, str(at_date))
        warning.warn(s)

    return return_active


def get_full_revision(hpn, at_date, session=None):
    """
    Returns list of fully connected revisions of part at_date

    Parameters:
    -------------
    hpn:  string of hera part number
    at_date:  date to check if fully connected
    session:  db session
    """
    from hera_mc import cm_hookup
    revisions = part_connect.get_part_revisions(hpn, session)
    rev = get_active_revision(hpn, at_date, session)
    if len(rev) > 1:
        s = "Multiple active revisions of {}".format(hpn)
        raise Exception(s)
    print("CM_REVISIONS[217]:  Need to remove state_args from here when change over")
    state_args = {'show_levels':False}
    hookup = cm_hookup.Hookup(session)
    hu = hookup.get_hookup(rev[0].hpn, rev[0].rev, 'all', at_date, state_args, True)
    #print(hu['hookup'][hu['hookup'].keys()[0]])
    if 'station' in hu['columns'] and 'f_engine' in hu['columns']:
        print('FULLLLLL')
