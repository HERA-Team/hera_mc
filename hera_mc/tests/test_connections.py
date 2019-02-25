# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`.

"""

from __future__ import absolute_import, division, print_function

import unittest
from astropy.time import Time, TimeDelta

from .. import part_connect, mc, cm_handling, cm_utils, cm_health
from . import TestHERAMC


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
            part = part_connect.Parts()
            part.hpn = tp
            part.hpn_rev = self.test_rev
            part.hptype = self.test_hptype
            part.manufacture_number = self.test_mfg
            part.start_gpstime = self.test_time
            self.test_session.add(part)
        self.test_session.commit()

        # Add test connection
        connection = part_connect.Connections()
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
            part = part_connect.Parts()
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
        part_connect.update_connection(self.test_session, data, add_new_connection=True)
        located = self.h.get_part_connection_dossier([u], r, a, 'now', True)
        prkey = list(located.keys())[0]
        print(located[prkey])
        ckey = located[prkey].keys_down[0]
        self.assertTrue(located[prkey].down[ckey].upstream_part == u)
        self.h.show_connections(located)
        self.h.show_connections(located, verbosity=1)
        self.h.show_connections(located, verbosity=2)

    def test_get_dossier(self):
        x = self.h.get_part_connection_dossier('test_part1', 'active', 'all', at_date='now', exact_match=True)
        y = list(x.keys())[0]
        self.assertEqual(y, 'test_part1:Q')
        self.h.show_connections(x)
        x = self.h.get_part_connection_dossier('test_part2', 'active', 'all', at_date='now', exact_match=True)
        y = list(x.keys())[0]
        self.assertEqual(y, 'test_part2:Q')
        self.h.show_connections(x)
        old_time = Time('2014-08-01 01:00:00', scale='utc')
        x = self.h.get_part_connection_dossier('test_part1', 'active', 'all', at_date=old_time, exact_match=True)
        self.assertTrue(len(x) == 0)
        x = self.h.get_part_connection_dossier('test_part2', 'active', 'all', at_date=old_time, exact_match=True)
        self.assertTrue(len(x) == 0)
        z = {}
        z['tst'] = cm_handling.PartConnectionDossierEntry('test_part1', 'active', 'all', at_date='now')
        self.h.show_connections(z)

    def test_get_specific_connection(self):
        c = part_connect.Connections()
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
        self.assertTrue('SNPA000222:A' in y)
        x = self.h.get_physical_connections('2016/01/01')
        self.assertFalse(len(x))

    def test_duplicate_connections(self):
        connection = part_connect.Connections()
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
