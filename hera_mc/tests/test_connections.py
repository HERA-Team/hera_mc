# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`.

"""

from __future__ import absolute_import, division, print_function

import unittest

from astropy.time import Time, TimeDelta

from hera_mc import part_connect, mc, cm_handling, cm_utils
from hera_mc.tests import TestHERAMC


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
        data = [[u,r,d,r,a,b,g,'upstream_part',u],
                [u,r,d,r,a,b,g,'up_part_rev',r],
                [u,r,d,r,a,b,g,'downstream_part',d],
                [u,r,d,r,a,b,g,'down_part_rev',r],
                [u,r,d,r,a,b,g,'upstream_output_port',a],
                [u,r,d,r,a,b,g,'downstream_input_port',b],
                [u,r,d,r,a,b,g,'start_gpstime',g]]
        part_connect.update_connection(self.test_session, data, add_new_connection=True)
        located = self.h.get_connection_dossier(u, r, a, 'now', True)
        self.assertTrue(located['connections'][located['connections'].keys()[0]].upstream_part == u)

    def test_is_in_connections(self):
        checking = self.h.is_in_connections(self.test_hpn[0], self.test_rev, False)
        self.assertTrue(checking)

    def test_return_is_in_connections(self):
        at_date = Time('2017-07-01 01:00:00', scale='utc')
        checking = self.h.is_in_connections(self.test_hpn[0], self.test_rev, at_date)
        print(checking)
        self.assertTrue(checking[0].upstream_part == self.test_hpn[0])

if __name__ == '__main__':
    unittest.main()
