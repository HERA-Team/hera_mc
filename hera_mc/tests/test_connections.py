# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`.

I don't think there's really much to do here besides just test insertion of a
record.

"""

from __future__ import absolute_import, division, print_function

import unittest

from astropy.time import Time, TimeDelta

from hera_mc import part_connect, mc
from hera_mc.tests import TestHERAMC


class TestConnections(TestHERAMC):

    def setUp(self):
        super(TestConnections, self).setUp()

        # Add test parts
        self.test_part1 = 'test_part1'
        self.test_part2 = 'test_part2'
        self.test_rev = 'Q'
        self.test_time = Time('2017-07-01 01:00:00', scale='utc').gps
        part = part_connect.Parts()
        part.hpn = self.test_part1
        part.hpn_rev = self.test_rev
        part.hptype = 'vapor'
        part.manufacture_number = 'XYZ'
        part.start_gpstime = self.test_time
        self.test_session.add(part)
        part.hpn = self.test_part2
        self.test_session.add(part)

        # Add test connection
        connection = part_connection.Connections()
        connection.upstream_part=self.test_part1
        connection.up_part_rev = self.test_rev
        connection.downstream_part = self.test_part2
        connection.down_part_rev = self.test_rev
        connection.upstream_output_port = 'up_and_out'
        connection.downstream_input_port = 'down_and_in'
        connection.start_gpstime = self.test_time

        self.test_session.commit()

    def test_get_connection(self):
        h = cm_handling.Handling(self.test_session)
        located = h.get_connection_dossier(self.test_part1, self.test_rev, 'up_and_out', 'now', True)
        self.assertTrue(located[located.keys()[0]].upstream_part == self.test_part1)

    def test_update_new(self):
        u = 'new_test_part_up'
        d = 'new_test_part_down'
        r = 'A'
        a = 'up_and_out'
        b = 'down_and_in'
        g = self.test_time
        data = [[u,r,d,r,a,b,g,'upstream_part',u],
                [u,r,d,r,a,b,g,'up_part_rev',r],
                [u,r,d,r,a,b,g,'downstream_part',d],
                [u,r,d,r,a,b,g,'down_part_rev',r],
                [u,r,d,r,a,b,g,'upstream_output_port',a],
                [u,r,d,r,a,b,g,'downstream_input_port',b],
                [u,r,d,r,a,b,g,'start_gpstime',g]]
        part_connect.update(self.test_session, data, add_new_part=True)
        h = cm_handling.Handling(self.test_session)
        located = h.get_connection_dossier(u, r, a, 'now', True)
        self.assertTrue(located[located.keys()[0]].upstream_part == u)


if __name__ == '__main__':
    unittest.main()
