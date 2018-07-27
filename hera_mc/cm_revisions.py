# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Functions to handle various cm revision queries and checks.

"""

from __future__ import absolute_import, print_function

import six
import warnings
from tabulate import tabulate
from argparse import Namespace

from hera_mc import cm_utils, part_connect


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
        [ACT]IVE:  revisions that are not stopped at_date
        [LAS]T:  the last connected revision (could be active or not)
        [FUL]LY_CONNECTED:  revision that is part of a fully connected signal path in hookup_dict/session
        [ALL]:  all revisions
        particular:  check for a particular revision

    Parameters:
    ------------
    hpn:  string for hera part number
    rev_type:  string for revision type
    at_date:  astropy.Time to check for
    session:  db session, or hookup_dict if FULLY_CONNECTED
    """

    rq = rev_type.upper()[:3]
    if rq == 'LAS':  # LAST
        return get_last_revision(hpn, session)

    if rq == 'ACT':  # ACTIVE
        if at_date is None:
            raise NoTimeException('ACTIVE')
        else:
            return get_active_revision(hpn, at_date, session)

    if rq == 'ALL':  # ALL
        return get_all_revisions(hpn, session)

    if rq == 'FUL':  # FULLY_CONNECTED
        return get_full_revision(hpn, session)

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
    Returns Namespace list of fully connected parts
    If either pol is fully connected, it is returned.
    The hpn type must match the hookup_dict keys part type

    Parameters:
    -------------
    hpn:  string of hera part number (must match hookup_dict keys part type)
    hookup_dict:  hookup dictionary to check for full connection
    """
    from hera_mc import cm_hookup
    if not isinstance(hookup_dict, dict):
        H = cm_hookup.Hookup()
        hookup_dict = H.get_hookup(H.hookup_list_to_cache)
    return_full_keys = []
    for k, h in six.iteritems(hookup_dict):
        hpn_hu, rev_hu = cm_utils.split_part_key(k)
        if hpn_hu.lower() == hpn.lower():
            for pol, is_connected in six.iteritems(h.fully_connected):
                if is_connected:
                    tsrt = h.timing[pol][0]
                    tend = h.timing[pol][1]
                    return_full_keys.append(Namespace(hpn=hpn, rev=rev_hu,
                                                      started=tsrt, ended=tend,
                                                      hukey=k, pol=pol))
    return return_full_keys


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
