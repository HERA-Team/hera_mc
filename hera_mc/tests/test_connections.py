# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`.

I don't think there's really much to do here besides just test insertion of a
record.

"""

from __future__ import absolute_import, division, print_function

from astropy.time import Time, TimeDelta

from hera_mc import part_connect, mc
from hera_mc.tests import TestHERAMC


class TestConnections(TestHERAMC):

    def setUp(self):
        super(TestGeo, self).setUp()

        part = part_connect.Parts()
        part.hpn = 'happy_thing'
        part.hpn_rev = 'A'
        part.manufacture_date = 'Oct 26, 2011'
        part.hptype = 'vapor'
        part.start_gpstime = Time('2016-01-10 01:15:23', scale='utc').gps
        self.test_session.add(part)
        self.test_session.commit()

    def test_commit_part(self):
        part = part_connect.Parts()
        part.hpn = 'happy_thing'
        part.hpn_rev = 'A'
        part.manufacture_date = 'Oct 26, 2011'
        part.hptype = 'vapor'
        part.start_gpstime = Time('2016-01-10 01:15:23', scale='utc').gps
        self.test_session.add(part)
        self.test_session.commit()
        self.assertTrue
