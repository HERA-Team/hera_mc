# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Functions to handle various cm revision queries and checks.

"""

from __future__ import absolute_import, print_function

from tabulate import tabulate
from hera_mc import cm_utils, part_connect
import warnings
from argparse import Namespace


class RevisionError(Exception):
    def __init__(self, hpn):
        # Call the base class constructor with the parameters it needs
        message = "Multiple revisions found on {}".format(hpn)
        super(RevisionError, self).__init__(message)


class NoTimeError(Exception):
    def __init__(self, RevType):
        # Call the base class constructor with the parameters it needs
        message = "To find {} revisions you must supply an astropy.Time".format(RevType)
        super(NoTimeError, self).__init__(message)


def get_revisions_of_type(hpn, rev_type, at_date=None, session=None):
    """
    Returns namespace of revisions (hpn, rev, started, ended, [hukey], [pkey]) of queried type
    where the [hukey], [pkey] are included for fully_connected queries.
    Allowed types are:
        [AC]TIVE:  revisions that are not stopped at_date
        [LA]ST:  the last connected revision (could be active or not)
        [FU]LLY_CONNECTED:  revision that is part of a fully connected signal path at_date
        [AL]L:  all revisions
        particular:  check for a particular revision

    Parameters:
    ------------
    hpn:  string for hera part number
    rev_type:  string for revision type
    at_date:  astropy.Time to check for
    session:  db session, or hookup_dict if FULLY_CONNECTED
    """

    rq = rev_type.upper()[:2]
    if rq == 'LA':  # LAST
        return get_last_revision(hpn, session)

    if rq == 'AC':  # ACTIVE
        if at_date is None:
            raise NoTimeException('ACTIVE')
        else:
            return get_active_revision(hpn, at_date, session)

    if rq == 'AL':  # ALL
        return get_all_revisions(hpn, session)

    if rq == 'FU':  # FULLY_CONNECTED
        if at_date is None:
            raise NoTimeException('ACTIVE')
        else:
            return get_full_revision_keys(hpn, session)

    return get_particular_revision(hpn, rev_type, session)


def get_last_revision(hpn, session=None):
    """
    Returns list of latest revisions as Namespace(hpn,rev,started,ended)

    Parameters:
    -------------
    hpn:  hera part name
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    if len(revisions.keys()) == 0:
        return []
    latest_end = cm_utils.get_astropytime('<')
    no_end = []
    for rev in revisions.keys():
        end_date = revisions[rev]['ended']
        if end_date is None:
            latest_end = cm_utils.get_astropytime('>')
            no_end.append(Namespace(hpn=hpn, rev=rev, started=revisions[rev]['started'],
                                    ended=revisions[rev]['ended']))
        elif end_date > latest_end:
            latest_rev = rev
            latest_end = end_date
    if len(no_end) > 0:
        return no_end
    else:
        return [Namespace(hpn=hpn, rev=latest_rev, started=revisions[latest_rev]['started'],
                          ended=revisions[latest_rev]['ended'])]


def get_all_revisions(hpn, session=None):
    """
    Returns list of all revisions as Namespace(hpn,rev,started,ended)

    Parameters:
    -------------
    hpn:  string of hera part number
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    if len(revisions.keys()) == 0:
        return []
    sort_rev = sorted(revisions.keys())
    all_rev = []
    for rev in sort_rev:
        started = revisions[rev]['started']
        ended = revisions[rev]['ended']
        all_rev.append(Namespace(hpn=hpn, rev=rev, started=started, ended=ended))
    return all_rev


def get_particular_revision(hpn, rq, session=None):
    """
    Returns list of a particular revision as Namespace(hpn,rev,started,ended)

    Parameters:
    -------------
    rq:  revision number to find
    hpn:  string of hera part number
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    if len(revisions.keys()) == 0:
        return []
    this_rev = []
    for rev in revisions.keys():
        if rq.upper() == rev.upper():
            start_date = revisions[rev]['started']
            end_date = revisions[rev]['ended']
            this_rev = [Namespace(hpn=hpn, rev=rev, started=start_date, ended=end_date)]
    return this_rev


def get_active_revision(hpn, at_date, session=None):
    """
    Returns list of active revisions as Namespace(hpn,rev,started,ended)

    Parameters:
    -------------
    hpn:  string of hera part number
    at_date:  date to check if fully connected
    session:  db session
    """

    revisions = part_connect.get_part_revisions(hpn, session)
    if len(revisions.keys()) == 0:
        return []
    return_active = []
    for rev in sorted(revisions.keys()):
        started = revisions[rev]['started']
        ended = revisions[rev]['ended']
        if cm_utils.is_active(at_date, started, ended):
            return_active.append(Namespace(hpn=hpn, rev=rev, started=started, ended=ended))

    return return_active


def get_full_revision(hpn, hookup_dict):
    """
    Returns list of fully connected keys as a tuple with the first polarization found.
    If either pol is fully connected, it is returned.
    The hpn type must match the hookup_dict keys part type

    Parameters:
    -------------
    hpn:  string of hera part number (must match hookup_dict keys part type)
    hookup_dict:  hookup dictionary to check for full connection
    """
    return_full_keys = []
    found_this_hpn = False
    for hukey in hookup_dict['hookup'].keys():
        hpn_hu, rev_hu = cm_utils.split_part_key(hukey)
        if hpn_hu.lower() == hpn.lower():
            if len(hookup_dict['fully_connected'].keys()):
                for pkey in hookup_dict['fully_connected'][hukey].keys():
                    if hookup_dict['fully_connected'][hukey][pkey]:
                        tsrt = hookup_dict['timing'][hukey][pkey][0]
                        tend = hookup_dict['timing'][hukey][pkey][1]
                        return_full_keys.append(Namespace(hpn=hpn, rev=rev_hu,
                                                          started=tsrt, ended=tend,
                                                          hukey=hukey, pkey=pkey))
                        found_this_hpn = True
                        break
        if found_this_hpn:
            break

    return return_full_keys


def check_rev(hpn, rev, chk, at_date, session=None):
    """
    Check whether a revision exists.

    Return True or False

    Parameters:
    ------------
    hpn:  hera part name
    rev:  revision to check
    chk:  revision type to check against (ACTIVE/PARTICULAR)
    at_date:  date at which to check
    session:  database session
    """
    print("CM_REVISIONS[85]:  This is not debugged.")
    rev_chk = get_revisions_of_type(hpn, chk, at_date, session)
    if len(rev_chk) == 0 or rev != rev_chk[0].rev:
        return False
    else:
        return True


def check_part_for_overlapping_revisions(hpn, session=None):
    """
    Checks hpn for parts that overlap in time.  Should be none.

    Returns list of overlapping part revisions

    Parameters:
    ------------
    hpn:  hera part name
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
                revisions[first_one].ended = cm_utils.get_astropytime('>')
            if revisions[second_one].started > revisions[first_one].ended:
                overlap.append([r1, r2])
    if len(overlap) > 0:
        overlapping_revs_in_single_list = []
        for ol in overlap:
            overlapping_revs_in_single_list.append(ol[0])
            overlapping_revs_in_single_list.append(ol[1])
            s = '{} and {} are overlapping revisions of part {}'.format(
                ol[0].rev, ol[1].rev, hpn)
            warnings.warn(s)
        show_revisions(overlapping_revs_in_single_list)
    return overlap


def show_revisions(rev_list):
    """
    Show revisions for provided revision list

    Parameters:
    -------------
    rev_list:  list as provided by one of the other methods
    """

    if len(rev_list) == 0:
        print("No revisions found.")
    else:
        headers = ['HPN', 'Revision', 'Start', 'Stop']
        table_data = []
        for r in rev_list:
            table_data.append([r.hpn, r.rev, r.started, r.ended])
        print(tabulate(table_data, headers=headers, tablefmt='simple'))
        print('\n')
