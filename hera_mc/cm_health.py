# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Functions to handle various cm table health checks.

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


class Connections:
    def __init__(self, session=None):
        if session is None:
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.conndict = None

    def get_conndict(self, session=None):
        self.conndict = {}
        self.multiples = []
        self.num_connections = 0
        for conn in self.session.query(PC.Connections).all():
            self.num_connections += 1
            connection = [conn.upstream_part, conn.up_part_rev, conn.upstream_output_port,
                          conn.downstream_part, conn.down_part_rev, conn.downstream_input_port]
            connection = [x.lower() for x in connection]
            k = ':'.join(connection)
            if k in self.conndict.keys():
                self.conndict[k].append([conn.start_gpstime, conn.stop_gpstime])
                if k not in self.multiples:
                    self.multiples.append(k)
            else:
                self.conndict[k] = [[conn.start_gpstime, conn.stop_gpstime]]

    def check_for_duplicate_connections(self):
        if self.conndict is None:
            self.get_conndict()
        if len(self.multiples) == 0:
            print("No duplications found.")
            return 0
        duplicates = []
        for k in self.multiples:
            for i, t in enumerate(self.conndict[k]):
                for j in range(i):
                    start_i = cm_utils.get_astropytime(self.conndict[k][i][0])
                    stop_i = cm_utils.get_stopdate(self.conndict[k][i][1])
                    start_j = cm_utils.get_astropytime(self.conndict[k][j][0])
                    stop_j = cm_utils.get_stopdate(self.conndict[k][j][1])
                    print("CM_H:  ", k)
                    if start_j <= start_i:
                        if stop_j > start_i:
                            duplicates.append([k, i, j])
                    else:
                        if start_j <= stop_i:
                            duplicates.append([k, i, j])
        if len(duplicates):
            print('{} duplications found.'.format(len(duplicates)))
            for d in duplicates:
                k = d[0]
                start_i = cm_utils.get_astropytime(self.conndict[k][i][0])
                stop_i = cm_utils.get_astropytime(self.conndict[k][i][1])
                start_j = cm_utils.get_astropytime(self.conndict[k][j][0])
                stop_j = cm_utils.get_astropytime(self.conndict[k][j][1])
                print('\t{} <1>{}-{}  <2>{}-{}'.format(k, start_i, stop_i, start_j, stop_j))
        else:
            print('No duplications found.')
        print('Out of {} connections checked.'.format(self.num_connections))
        return len(duplicates)

    def check_for_existing_connection(self, connection, at_date='now'):
        at_date = cm_utils.get_astropytime(at_date)
        connection = [x.lower() for x in connection]
        k = ':'.join(connection)
        if self.conndict is None:
            self.get_conndict()
        if k not in self.conndict.keys():
            return False
        for t in self.conndict[k]:
            start_t = cm_utils.get_astropytime(t[0])
            stop_t = cm_utils.get_astropytime(t[1])
            if cm_utils.is_active(at_date, start_t, stop_t):
                print('Duplicate found for connection {} at {}:  {} - {}'.format(k, at_date, start_t, stop_t))
                return True
        return False


def check_part_for_overlapping_revisions(hpn, session=None):
    """
    Checks hpn for parts that overlap in time.  Should be none.

    Returns list of overlapping part revisions

    Parameters:
    ------------
    hpn:  hera part name
    """

    overlap = []
    revisions = cm_revisions.get_all_revisions(hpn, session)
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
        cm_revisions.show_revisions(overlapping_revs_in_single_list)
    return overlap
