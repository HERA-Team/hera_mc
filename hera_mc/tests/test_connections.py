# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`.

"""

from __future__ import absolute_import, division, print_function

import unittest
from astropy.time import Time, TimeDelta
from contextlib import contextmanager
import six
import sys

from .. import cm_partconn, mc, cm_handling, cm_utils, cm_health
from . import TestHERAMC


# define a context manager for checking stdout
# from https://stackoverflow.com/questions/4219717/how-to-assert-output-with-nosetest-unittest-in-python
@contextmanager
def captured_output():
    new_out, new_err = six.StringIO(), six.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class TestConnections(TestHERAMC):

    def setUp(self):
        super(TestConnections, self).setUp()
        self.test_hpn = ['test_part1', 'test_part2']
        self.test_rev = 'Q'
        self.test_mfg = 'XYZ'
        self.test_hptype = 'vapor'
        self.test_time = Time('2017-07-01 01:00:00', scale='utc').gps
        self.query_time = Time('2017-08-01 01:00:00', scale='utc')

        for tp in self.test_hpn:
            part = cm_partconn.Parts()
            part.hpn = tp
            part.hpn_rev = self.test_rev
            part.hptype = self.test_hptype
            part.manufacture_number = self.test_mfg
            part.start_gpstime = self.test_time
            self.test_session.add(part)
        self.test_session.commit()

        # Add test connection
        connection = cm_partconn.Connections()
        connection.upstream_part = self.test_hpn[0]
        connection.up_part_rev = self.test_rev
        connection.downstream_part = self.test_hpn[1]
        connection.down_part_rev = self.test_rev
        connection.upstream_output_port = 'up_and_out'
        connection.downstream_input_port = 'down_and_in'
        connection.start_gpstime = self.test_time
        self.test_session.add(connection)
        self.test_session.commit()

        self.h = cm_handling.Handling(self.test_session)

    def test_update_new(self):
        u = 'new_test_part_up'
        d = 'new_test_part_down'
        r = 'A'
        a = 'up_and_out'
        b = 'down_and_in'
        g = self.test_time
        for tp in [u, d]:
            part = cm_partconn.Parts()
            part.hpn = tp
            part.hpn_rev = r
            part.hptype = self.test_hptype
            part.manufacture_number = self.test_mfg
            part.start_gpstime = self.test_time
            self.test_session.add(part)
        self.test_session.commit()
        data = [[u, r, d, r, a, b, g, 'upstream_part', u],
                [u, r, d, r, a, b, g, 'up_part_rev', r],
                [u, r, d, r, a, b, g, 'downstream_part', d],
                [u, r, d, r, a, b, g, 'down_part_rev', r],
                [u, r, d, r, a, b, g, 'upstream_output_port', a],
                [u, r, d, r, a, b, g, 'downstream_input_port', b],
                [u, r, d, r, a, b, g, 'start_gpstime', g]]
        cm_partconn.update_connection(self.test_session, data, add_new_connection=True)
        located = self.h.get_part_connection_dossier([u], r, a, 'now', True)
        prkey = list(located.keys())[0]
        self.assertTrue(str(located[prkey]).startswith('NEW_TEST_PART_UP:A'))
        ckey = located[prkey].keys_down[0]
        self.assertTrue(located[prkey].down[ckey].upstream_part == u)
        with captured_output() as (out, err):
            self.h.show_connections(located)
        self.assertTrue('new_test_part_up:A | up_and_out  | down_and_in | new_test_part_down:A' in out.getvalue().strip())
        with captured_output() as (out, err):
            self.h.show_connections(located, verbosity=1)
        self.assertTrue('new_test_part_up:A | new_test_part_down:A' in out.getvalue().strip())
        with captured_output() as (out, err):
            self.h.show_connections(located, verbosity=2)
        self.assertTrue('new_test_part_up:A | up_and_out  | down_and_in | new_test_part_down:A' in out.getvalue().strip())

    def test_get_dossier(self):
        x = self.h.get_part_connection_dossier('test_part1', 'active', 'all', at_date='now', exact_match=True)
        y = list(x.keys())[0]
        self.assertEqual(y, 'test_part1:Q')
        with captured_output() as (out, err):
            self.h.show_connections(x)
        self.assertTrue('test_part1:Q | up_and_out  | down_and_in | test_part2:Q' in out.getvalue().strip())
        x = self.h.get_part_connection_dossier('test_part2', 'active', 'all', at_date='now', exact_match=True)
        y = list(x.keys())[0]
        self.assertEqual(y, 'test_part2:Q')
        with captured_output() as (out, err):
            self.h.show_connections(x)
        self.assertTrue('test_part1:Q | up_and_out  | down_and_in | test_part2:Q' in out.getvalue().strip())
        old_time = Time('2014-08-01 01:00:00', scale='utc')
        x = self.h.get_part_connection_dossier('test_part1', 'active', 'all', at_date=old_time, exact_match=True)
        self.assertTrue(len(x) == 0)
        x = self.h.get_part_connection_dossier('test_part2', 'active', 'all', at_date=old_time, exact_match=True)
        self.assertTrue(len(x) == 0)
        z = {}
        z['tst'] = cm_handling.PartConnectionDossierEntry('test_part1', 'active', 'all')
        with captured_output() as (out, err):
            self.h.show_connections(z)
        self.assertTrue('Q' not in out.getvalue().strip())

    def test_get_specific_connection(self):
        c = cm_partconn.Connections()
        c.upstream_part = self.test_hpn[0]
        c.up_part_rev = self.test_rev
        c.downstream_part = self.test_hpn[1]
        c.down_part_rev = self.test_rev
        c.upstream_output_port = 'up_and_out'
        c.downstream_input_port = 'down_and_in'
        sc = self.h.get_specific_connection(c)
        self.assertTrue(len(sc) == 1)

        c.up_part_rev = 'S'
        sc = self.h.get_specific_connection(c)
        self.assertTrue(len(sc) == 0)

        c.up_part_rev = self.test_rev
        c.down_part_rev = 'S'
        sc = self.h.get_specific_connection(c)
        self.assertTrue(len(sc) == 0)

        c.down_part_rev = self.test_rev
        c.upstream_output_port = 'guk'
        sc = self.h.get_specific_connection(c)
        self.assertTrue(len(sc) == 0)

        c.upstream_output_port = 'up_and_out'
        c.downstream_input_port = 'guk'
        sc = self.h.get_specific_connection(c)
        self.assertTrue(len(sc) == 0)

        at_date = Time('2017-05-01 01:00:00', scale='utc')
        sc = self.h.get_specific_connection(c, at_date)
        self.assertTrue(len(sc) == 0)

    def test_check_for_overlap(self):
        x = cm_health.check_for_overlap([[1, 2], [3, 4]])
        self.assertFalse(x)
        x = cm_health.check_for_overlap([[3, 4], [1, 2]])
        self.assertFalse(x)
        x = cm_health.check_for_overlap([[1, 10], [2, 8]])
        self.assertTrue(x)
        x = cm_health.check_for_overlap([[2, 8], [1, 10]])
        self.assertTrue(x)
        x = cm_health.check_for_overlap([[1, 5], [3, 8]])
        self.assertTrue(x)
        x = cm_health.check_for_overlap([[3, 8], [1, 5]])
        self.assertTrue(x)
        x = cm_health.check_for_overlap([[1, 8], [8, 10]])
        self.assertFalse(x)
        x = cm_health.check_for_overlap([[8, 10], [1, 8]])
        self.assertFalse(x)

    def test_physical_connections(self):
        x = self.h.get_physical_connections()
        y = list(x.keys())
        self.assertTrue('PAM75999:A' in y)
        x = self.h.get_physical_connections('2016/01/01')
        self.assertFalse(len(x))

    def test_duplicate_connections(self):
        connection = cm_partconn.Connections()
        healthy = cm_health.Connections(self.test_session)
        # Specific connections
        duplicates = healthy.check_for_existing_connection(['a', 'b', 'c', 'd', 'e', 'f'], self.query_time)
        self.assertFalse(duplicates)
        cnnctn = [self.test_hpn[0], self.test_rev, 'up_and_out', self.test_hpn[1], self.test_rev, 'down_and_in']
        duplicates = healthy.check_for_existing_connection(cnnctn, self.query_time, display_results=True)
        self.assertTrue(duplicates)
        # Add test connection
        duplicates = healthy.check_for_existing_connection(cnnctn, Time('2015-07-01 01:00:00', scale='utc').gps, display_results=True)
        self.assertFalse(duplicates)
        # Duplicated connections
        duplicates = healthy.check_for_duplicate_connections(display_results=True)
        self.assertTrue(len(duplicates) == 0)
        # Add test duplicate connection
        connection.upstream_part = self.test_hpn[0]
        connection.up_part_rev = self.test_rev
        connection.downstream_part = self.test_hpn[1]
        connection.down_part_rev = self.test_rev
        connection.upstream_output_port = 'up_and_out'
        connection.downstream_input_port = 'down_and_in'
        connection.start_gpstime = self.test_time + 10
        self.test_session.add(connection)
        self.test_session.commit()
        healthy.conndict = None
        duplicates = healthy.check_for_duplicate_connections(display_results=True)
        self.assertTrue(len(duplicates) == 1)


if __name__ == '__main__':
    unittest.main()
