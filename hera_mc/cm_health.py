# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Functions to handle various cm table "health" checks.

"""

from __future__ import absolute_import, print_function
import warnings
from hera_mc import mc, cm_utils
from hera_mc import part_connect as PC
from hera_mc import cm_revisions


class RevisionError(Exception):
    def __init__(self, hpn):
        # Call the base class constructor with the parameters it needs
        message = "Multiple revisions found on {}".format(hpn)
        super(RevisionError, self).__init__(message)


def check_for_overlap(start_i, stop_i, start_j, stop_j):
    if start_j <= start_i:
        if stop_j > start_i:
            return True
    elif start_j <= stop_i:
            return True
    return False


class Connections:
    def __init__(self, session=None):
        if session is None:
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
            the potential for conflicting times.
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
            self.conndict.setdefault(k, []).append([cm_utils.get_astropytime(conn.start_gpstime),
                                                    cm_utils.get_stopdate(conn.stop_gpstime)])

    def check_for_duplicate_connections(self):
        """
        Checks all of the self.multiple keys to see if any of them overlap in time.
        If they do, it is a conflicting duplicate connection.
        Writes a class variable:
        duplicates - list - [[key, i, j], ...]
            List which keeps triplets of duplication information as the key and the
            indices of the conflicting times.

        Returns the number of duplicates found.
        """
        self.ensure_conndict()
        if len(self.multiples) == 0:
            print("No duplications found.")
            return 0
        self.duplicates = []
        for k in self.multiples:
            for i in range(len(self.conndict[k])):
                for j in range(i):
                    start_i = self.conndict[k][i][0]
                    stop_i = self.conndict[k][i][1]
                    start_j = self.conndict[k][j][0]
                    stop_j = self.conndict[k][j][1]
                    if check_for_overlap(start_i, stop_i, start_j, stop_j):
                        self.duplicates.append([k, i, j])
        if len(self.duplicates):
            print('{} duplications found.'.format(len(self.duplicates)))
            for d in self.duplicates:
                start_i = self.conndict[d[0]][d[1]][0]
                stop_i = self.conndict[d[0]][d[1]][1]
                start_j = self.conndict[d[0]][d[2]][0]
                stop_j = self.conndict[d[0]][d[2]][1]
                print('\t{} <1>{}-{}  <2>{}-{}'.format(k, start_i, stop_i, start_j, stop_j))
        else:
            print('No duplications found.')
        print('Out of {} connections checked.'.format(self.num_connections))
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
        for t in self.conndict[k]:
            if cm_utils.is_active(at_date, t[0], t[1]):
                print('Connection {} is already made for {}  ({} - {})'.format(k, at_date, t[0], t[1]))
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
            start_i = revisions[i].started
            stop_i = cm_utils.get_stopdate(revisions[i].ended)
            start_j = revisions[j].started
            stop_j = cm_utils.get_stopdate(revisions[j].ended)
            if check_for_overlap(start_i, stop_i, start_j, stop_j):
                self.overlap.append([revisions[i], revisions[j]])

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
