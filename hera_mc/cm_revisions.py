# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Functions to handle various cm revision queries and checks.

LAST, ACTIVE, ALL, <specific> are handled (typically) via get_revisions_of_type.
FULL revisions are called directly (get_full_revision)
"""

from argparse import Namespace

from . import cm_utils, cm_partconnect


revision_categories = ["last", "active", "all", "full", "none"]


def get_revisions_of_type(
    hpn, rev_type, at_date="now", at_time=None, float_format=None, session=None
):
    """
    Return namespace of revisions of rev_query.

    Namespace is: (hpn, rev, rev_query, started, ended, [hukey], [pkey])

    Parameters
    ----------
    hpn : str
        HERA part number
    rev_type : str
        Revision type/value.  One of LAST, ACTIVE, ALL, <specific>
    at_date : anything understandable to cm_utils.get_astropytime
        Relevant date to check for.
    at_time : anything understandable to cm_utils.get_astropytime
        Relevant time to check for, ignored if at_date is a float or contains time information.
    float_format : str or None
        Format if at_date is a number denoting gps or unix seconds or jd day.
    session : object
        Database session to use.  If None, it will start a new session, then close.

    Returns
    -------
    Namespace
        (hpn, rev, rev_query, started, ended, [hukey], [pkey])

    """
    rq = rev_type.upper()
    if rq.startswith("LAST"):
        return get_last_revision(hpn, session)

    if rq.startswith("ACTIVE"):
        return get_active_revision(hpn, at_date, at_time, float_format, session)

    if rq.startswith("ALL") or rq.startswith("NONE"):
        return get_all_revisions(hpn, session)

    if rq.startswith("FULL"):
        raise ValueError("FULL revisions called with get_full_revision directly")

    return get_specific_revision(hpn, rev_type, session)


def get_last_revision(hpn, session=None):
    """
    Return list of latest revisions as Namespace(hpn,rev,erv_query,started,ended).

    Parameters
    ----------
    hpn : str
        HERA part number
    session : object
        Database session to use.  If None, it will start a new session, then close.

    Returns
    -------
    Namespace
        (hpn, rev, rev_query, started, ended, [hukey], [pkey])

    """
    revisions = cm_partconnect.get_part_revisions(hpn, session)
    if len(revisions.keys()) == 0:
        return []
    latest_end = cm_utils.get_astropytime("<")
    noend_rev = []
    latest_rev = []
    for rev in revisions.keys():
        end_date = revisions[rev]["ended"]
        if end_date is None:
            noend_rev.append(rev)
            latest_end = cm_utils.get_astropytime(">")
        elif end_date > latest_end:
            latest_rev = [rev]
            latest_end = end_date
    if len(noend_rev):
        latest_rev = noend_rev

    last_rev = []
    for rev in latest_rev:
        started = revisions[rev]["started"]
        ended = revisions[rev]["ended"]
        last_rev.append(
            Namespace(hpn=hpn, rev=rev, rev_query="LAST", started=started, ended=ended)
        )
    return last_rev


def get_all_revisions(hpn, session=None):
    """
    Return list of all revisions as Namespace(hpn, rev, started, ended).

    Parameters
    ----------
    hpn : str
        HERA part number
    session : object
        Database session to use.  If None, it will start a new session, then close.

    Returns
    -------
    Namespace
        (hpn, rev, rev_query, started, ended, [hukey], [pkey])

    """
    revisions = cm_partconnect.get_part_revisions(hpn, session)
    if len(revisions.keys()) == 0:
        return []
    sort_rev = sorted(revisions.keys())
    all_rev = []
    for rev in sort_rev:
        started = revisions[rev]["started"]
        ended = revisions[rev]["ended"]
        all_rev.append(
            Namespace(hpn=hpn, rev=rev, rev_query="ALL", started=started, ended=ended)
        )
    return all_rev


def get_specific_revision(hpn, rq, session=None):
    """
    Return list of a particular revision as Namespace(hpn,rev,started,ended).

    Parameters
    ----------
    hpn : str
        HERA part number
    rq : str
        Specific revision
    session : object
        Database session to use.  If None, it will start a new session, then close.

    Returns
    -------
    Namespace
        (hpn, rev, rev_query, started, ended, [hukey], [pkey])

    """
    revisions = cm_partconnect.get_part_revisions(hpn, session)
    if len(revisions.keys()) == 0:
        return []
    this_rev = []
    for rev in revisions.keys():
        if rq.upper() == rev.upper():
            start_date = revisions[rev]["started"]
            end_date = revisions[rev]["ended"]
            this_rev = [
                Namespace(
                    hpn=hpn, rev=rev, rev_query=rq, started=start_date, ended=end_date
                )
            ]
    return this_rev


def get_active_revision(hpn, at_date, at_time=None, float_format=None, session=None):
    """
    Return list of active revisions as Namespace(hpn,rev,started,ended).

    Parameters
    ----------
    hpn : str
        HERA part number
    at_date : anything understandable to cm_utils.get_astropytime
        Relevant date to check for.
    at_time : anything understandable to cm_utils.get_astropytime
        Relevant time to check for, ignored if at_date is a float or contains time information.
    float_format : str or None
        Format if at_date is a number denoting gps or unix seconds or jd day.
    session : object
        Database session to use.  If None, it will start a new session, then close.

    Returns
    -------
    Namespace
        (hpn, rev, rev_query, started, ended, [hukey], [pkey])

    """
    revisions = cm_partconnect.get_part_revisions(hpn, session)
    if len(revisions.keys()) == 0:
        return []
    active_date = cm_utils.get_astropytime(at_date, at_time, float_format)
    return_active = []
    for rev in sorted(revisions.keys()):
        started = revisions[rev]["started"]
        ended = revisions[rev]["ended"]
        if cm_utils.is_active(active_date, started, ended):
            return_active.append(
                Namespace(
                    hpn=hpn, rev=rev, rev_query="ACTIVE", started=started, ended=ended
                )
            )

    return return_active


def get_full_revision(hpn, hookup_dict):
    """
    Return Namespace list of fully connected parts.

    If either pol is fully connected, it is returned.
    The hpn type must match the hookup_dict keys part type

    Parameters
    ----------
    hpn : str
        HERA part number (must match hookup_dict keys part type)
    hookup_dict : dict
        Hookup dictionary containing the queried hookup data set

    Returns
    -------
    list
        List containing the relevant Namepace entries

    """
    return_full_keys = []
    for k, h in hookup_dict.items():
        hpn_hu, rev_hu = cm_utils.split_part_key(k)
        if hpn_hu.lower() == hpn.lower():
            for pol, is_connected in h.fully_connected.items():
                if is_connected:
                    tsrt = h.timing[pol][0]
                    tend = h.timing[pol][1]
                    return_full_keys.append(
                        Namespace(
                            hpn=hpn,
                            rev=rev_hu,
                            rev_query="FULL",
                            started=tsrt,
                            ended=tend,
                            hukey=k,
                            pol=pol,
                        )
                    )
    return return_full_keys


revision_columns = {
    "HPN": {"attr": "hpn", "default": "", "is_time": False},
    "Revision": {"attr": "rev", "default": "", "is_time": False},
    "Number": {"attr": "number", "default": 0, "is_time": False},
    "Start": {"attr": "started", "default": "", "is_time": True},
    "Stop": {"attr": "ended", "default": "", "is_time": True},
}
ordered_columns = ["HPN", "Revision", "Number", "Start", "Stop"]


def show_revisions(rev_list, columns="all"):
    """
    Show revisions for provided revision list.

    Parameters
    ----------
    rev_list : list
        List of revision Namespaces provided by one of the other methods
    columns : list or str
        Columns to include.  If 'all', include all present.  Can be a csv string list.

    """
    from tabulate import tabulate

    if len(rev_list) == 0:
        return "No revisions found."

    # Get attributes present and set defaults as needed
    for col in ordered_columns:
        revision_columns[col]["present"] = False
    for r in rev_list:
        for col in ordered_columns:
            try:
                getattr(r, revision_columns[col]["attr"])
                revision_columns[col]["present"] = True
            except AttributeError:
                setattr(
                    r, revision_columns[col]["attr"], revision_columns[col]["default"]
                )
    # Get columns to display
    if isinstance(columns, str):
        if columns == "all":
            columns = ordered_columns
        elif columns == "present":
            columns = []
            for col in ordered_columns:
                if revision_columns[col]["present"]:
                    columns.append(col)
        else:
            columns = columns.split(",")
    # Make table
    table_data = []
    for r in rev_list:
        row = []
        for col in columns:
            rev_attr = getattr(r, revision_columns[col]["attr"])
            if revision_columns[col]["is_time"]:
                rev_attr = cm_utils.get_time_for_display(rev_attr)
            row.append(rev_attr)
        table_data.append(row)

    return tabulate(table_data, headers=columns, tablefmt="simple")
