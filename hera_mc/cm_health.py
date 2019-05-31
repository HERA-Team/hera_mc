# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Functions to handle various cm table "health" checks.

"""

from __future__ import absolute_import, division, print_function

import warnings
from . import mc, cm_utils, cm_revisions, cm_sysdef, cm_partconnect
import six


def check_for_overlap(interval):
    """
    intervals:  gps_time intervals to test for overlap
                format [[span_1_low, span_1_high], [span_2_low, span_2_high]]
                if the high values are None, they get set to the max value + 100 sec
    """
    maxx = max([x for x in interval[0] + interval[1] if x is not None]) + 100
    for i, ival in enumerate(interval):
        ival[1] = maxx if ival[1] is None else ival[1]
    return interval[0][1] > interval[1][0] and interval[1][1] > interval[0][0]


class Connections:
    def __init__(self, session=None):
        if session is None:  # pragma: no cover
            db = mc.connect_to_mc_db(None)
            self.session = db.sessionmaker()
        else:
            self.session = session
        self.conndict = None
        self.sysdef = cm_sysdef.Sysdef()

    def ingest_conndb(self):
        """
        conndict - dictionary - conndict[k] = [conn_1, conn_2...]
            Dictionary of connections keyed as:
            upstream_part:rev:output_port:downstream_part:rev:input_port
            with the items being connection classes.
        multiple - set - {key1, ...}
            Set of conndict keys with more than one pair, so there is
            the potential of conflicting times.
        num_connections:
            Integer of the total number of connections in database.
        """
        self.conndict = {'up': {}, 'dn': {}}
        self.multiples = {'up': set(), 'dn': set()}
        self.num_connections = 0
        conn = {}
        for conn_entry in self.session.query(cm_partconnect.Connections).all():
            self.num_connections += 1
            conn['up'] = [conn_entry.upstream_part, conn_entry.up_part_rev, conn_entry.upstream_output_port]
            conn['dn'] = [conn_entry.downstream_part, conn_entry.down_part_rev, conn_entry.downstream_input_port]
            for dir in ['up', 'dn']:
                connection = [x.lower() for x in conn[dir]]
                k = ':'.join(connection)
                if k in self.conndict[dir].keys():
                    self.multiples[dir].add(k)  # only add to multiples if there is more than one.
                self.conndict[dir].setdefault(k, []).append(conn_entry)

    def check_for_duplicate_connections(self):
        """
        Checks all of the self.multiple keys to see if any of them overlap in time.
        If they do, it is a conflicting duplicate connection.

        Returns the duplicated connections.
        """
        self.ingest_conndb()
        all_pols = set()
        for ptty in self.sysdef.checking_order:
            for pol in self.sysdef.all_pols[ptty]:
                all_pols.add(pol.lower())

        duplicates = {'up': {}, 'dn': {}}
        kdir = {'up': {'Apart': 'upstream_part', 'Arev': 'up_part_rev', 'Aport': 'upstream_output_port',
                       'Bpart': 'downstream_part', 'Brev': 'down_part_rev', 'Bport': 'downstream_input_port'},
                'dn': {'Apart': 'downstream_part', 'Arev': 'down_part_rev', 'Aport': 'downstream_input_port',
                       'Bpart': 'upstream_part', 'Brev': 'up_part_rev', 'Bport': 'upstream_output_port'}}
        shown_dup = 0
        for dir in ['up', 'dn']:
            for k in self.multiples[dir]:
                for i in range(len(self.conndict[dir][k])):
                    for j in range(i):
                        intervals = [[self.conndict[dir][k][i].start_gpstime, self.conndict[dir][k][i].stop_gpstime],
                                     [self.conndict[dir][k][j].start_gpstime, self.conndict[dir][k][j].stop_gpstime]]
                        if check_for_overlap(intervals):
                            duplicates[dir].setdefault(k, []).append([self.conndict[dir][k][i], self.conndict[dir][k][j]])
            if len(duplicates[dir]):
                for k, duplist in six.iteritems(duplicates[dir]):
                    for dup in duplist:
                        Aport_p = k.split(':')[2][0]
                        Bport_p1 = getattr(dup[0], kdir[dir]['Bport'])[0].lower()
                        Bport_p2 = getattr(dup[1], kdir[dir]['Bport'])[0].lower()
                        show_it = True
                        if Aport_p not in all_pols:
                            Bport_pols = set()
                            if Bport_p1 in all_pols:
                                Bport_pols.add(Bport_p1)
                            if Bport_p2.lower() in all_pols:
                                Bport_pols.add(Bport_p2)
                            if len(Bport_pols) > 1:
                                show_it = False
                        if show_it:
                            shown_dup += 1
                            i1 = [dup[0].start_gpstime, dup[0].stop_gpstime]
                            i2 = [dup[1].start_gpstime, dup[1].stop_gpstime]
                            print('\t{}    {:35s}  &&  {:35s}  {:25s} {:25s}'.format(dir, str(dup[0]), str(dup[1]), str(i1), str(i2)))
        if shown_dup:
            print("{} duplications found.".format(shown_dup))
        else:
            print('No duplications found.')
        print('{} connections checked.'.format(self.num_connections))
        return duplicates

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
        self.ingest_conndb()
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
