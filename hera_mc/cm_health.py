# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Functions to handle various cm table "health" checks.

"""

from __future__ import absolute_import, division, print_function

import warnings
from . import mc, cm_utils
from . import part_connect as PC
from . import cm_revisions


def check_for_overlap(intervals):
    noends = []
    xxx = [x for x in intervals[0] + intervals[1] if x is not None]
    for i, ival in enumerate(intervals):
        if ival[1] is None:
            noends.append(i)
    for i in noends:
        intervals[i][1] = max(xxx) + 100

    if intervals[1][0] <= intervals[0][0]:
        if intervals[1][1] > intervals[0][0]:
            return True
    elif intervals[1][0] <= intervals[0][1]:
        return True
    return False


class Connections:
    def __init__(self, session=None):
        if session is None:  # pragma: no cover
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.conndict = None

    def ensure_conndict(self):
        """
        If not already set, writes the class variables:
        conndict - dictionary - conndict[k] = [[start, stop], []...]
            Dictionary of connections keyed as:
            upstream_part:rev:output_port:downstream_part:rev:input_port
            with the items being the start/stop times of that connection.
            So all entries will have at least one pair.
        multiple - set - {key1, ...}
            Set of connections keys with more than one pair, so there is
            the potential ensure_conndict conflicting times.
        num_connections:
            Integer of the total number of connections in database.
        """
        if self.conndict is not None:
            return
        self.conndict = {}
        self.multiples = set()
        self.num_connections = 0
        for conn in self.session.query(PC.Connections).all():
            self.num_connections += 1
            connection = [conn.upstream_part, conn.up_part_rev, conn.upstream_output_port,
                          conn.downstream_part, conn.down_part_rev, conn.downstream_input_port]
            connection = [x.lower() for x in connection]
            k = ':'.join(connection)
            if k in self.conndict.keys():
                self.multiples.add(k)  # only add to multiples if there is more than one.
            self.conndict.setdefault(k, []).append(conn)

    def check_for_duplicate_connections(self):
        """
        Checks all of the self.multiple keys to see if any of them overlap in time.
        If they do, it is a conflicting duplicate connection.

        Returns the number of duplicates found.
        """
        self.ensure_conndict()
        self.duplicates = []
        for k in self.multiples:
            for i in range(len(self.conndict[k])):
                for j in range(i):
                    intervals = [[self.conndict[k][i].start_gpstime, self.conndict[k][i].stop_gpstime],
                                 [self.conndict[k][j].start_gpstime, self.conndict[k][j].stop_gpstime]]
                    if check_for_overlap(intervals):
                        self.duplicates.append([k, i, j])
        if len(self.duplicates):
            s = 's'
            if len(self.duplicates) == 1:
                s = ''
            print('{} duplicate{} found.'.format(len(self.duplicates), s))
            for dup in self.duplicates:
                dc = self.conndict[dup[0]]
                i0 = [dc[dup[1]].start_gpstime, dc[dup[1]].stop_gpstime]
                i1 = [dc[dup[2]].start_gpstime, dc[dup[2]].stop_gpstime]
                print('\t{}  --->  {} {}'.format(dc[0], i0, i1))
        else:
            print('No duplications found.')
        print('{} connections checked.'.format(self.num_connections))
        return len(self.duplicates)

    def check_for_existing_connection(self, connection, at_date='now'):
        """
        Checks whether the provided connection is already set up for the at_date provided.

        Parameters:
        ------------
        connection:  connection list [upstream, rev, output_port, downstream, rev, input_port]
        at_date:  date for the connection to be made
        """

        at_date = cm_utils.get_astropytime(at_date)
        connection = [x.lower() for x in connection]
        k = ':'.join(connection)
        self.ensure_conndict()
        if k not in self.conndict.keys():
            return False
        for conn in self.conndict[k]:
            t0 = conn.start_gpstime
            t1 = conn.stop_gpstime
            if cm_utils.is_active(at_date, t0, t1):
                print('Connection {} is already made for {}  ({} - {})'.format(k, at_date, t0, t1))
                return True
        return False


def check_part_for_overlapping_revisions(hpn, session=None):
    """
    Checks hpn for parts that overlap in time.  They are allowed, but
    may also signal unwanted behavior.

    Returns list of overlapping part revisions

    Parameters:
    ------------
    hpn:  hera part name
    """

    overlap = []
    revisions = cm_revisions.get_all_revisions(hpn, session)
    for i in range(len(revisions)):
        for j in range(i):
            intervals = [[revisions[i].started, cm_utils.get_stopdate(revisions[i].ended)],
                         [revisions[j].started, cm_utils.get_stopdate(revisions[j].ended)]]
            if check_for_overlap(intervals):
                overlap.append([revisions[i], revisions[j]])

    if len(overlap) > 0:
        overlapping_revs_in_single_list = []
        for ol in overlap:
            overlapping_revs_in_single_list.append(ol[0])
            overlapping_revs_in_single_list.append(ol[1])
            s = '{} and {} are overlapping revisions of part {}'.format(
                ol[0].rev, ol[1].rev, hpn)
            warnings.warn(s)
        cm_revisions.show_revisions(overlapping_revs_in_single_list)
    return overlap
