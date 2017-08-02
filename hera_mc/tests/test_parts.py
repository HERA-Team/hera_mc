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


class TestParts(TestHERAMC):

    def setUp(self):
        super(TestParts, self).setUp()

        self.test_part = 'test_part'
        self.test_rev = 'Q'
        part = part_connect.Parts()
        part.hpn = self.test_part
        part.hpn_rev = self.test_rev
        part.hptype = 'vapor'
        part.manufacture_number = 'XYZ'
        part.start_gpstime = Time('2017-07-01 01:00:00', scale='utc').gps
        self.test_session.add(part)
        self.test_session.commit()
        self.h = cm_handling.Handling(self.test_session)

    def test_get_part(self):
        located = self.h.get_part_dossier(self.test_part, self.test_rev, 'now', True)
        if len(located.keys() == 1):
            self.assertTrue(located[located.keys()[0]].hpn_rev == self.test_rev)
        else:
            self.assertFalse("Part Number should be unique.")

    def test_update_new(self):
        ntp = 'new_test_part'
        data = [[ntp, 'hpn', ntp],
                [ntp, 'hpn_rev', 'X'],
                [ntp, 'hptype', 'vapor_part'],
                [ntp, 'start_gpstime', 1172530000]]
        part_connect.update(self.test_session, data, add_new_part=True)
        located = self.h.get_part_dossier(ntp, 'X', 'now', True)
        if len(located.keys() == 1):
            self.assertTrue(located[located.keys()[0]].hpn == ntp)
        else:
            self.assertFalse("Part Number should be unique.")

    def test_update_update(self):
        data = [[self.test_part, 'hpn_rev', 'Z']]
        part_connect.update(self.test_session, data, add_new_part=False)
        located = self.h.get_part_dossier(self.test_part, 'Z', 'now', True)
        if len(located.keys() == 1):
            self.assertTrue(located[located.keys()[0]].hpn == ntp)
        else:
            self.assertFalse("Part Number should be unique.")

    def test_add_new_parts(self):
        data = [['part_X','X','hptype_X','mfg_X']]
        p = part_connect.Parts()
        part_connect.test_add_new_parts(self.test_session, p, data, Time('2017-07-01 01:00:00', scale='utc'), True)
        located = self.h.get_part_dossier('part_X', 'X', 'now', True)
        if len(located.keys() == 1):
            self.assertTrue(located[located.keys()[0]].hpn == 'part_X')
        else:
            self.assertFalse("Part Number should be unique.")
