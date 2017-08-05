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

from hera_mc import part_connect, mc, cm_utils, cm_handling
from hera_mc.tests import TestHERAMC


class TestParts(TestHERAMC):

    def setUp(self):
        super(TestParts, self).setUp()

        self.test_part = 'test_part'
        self.test_rev = 'Q'
        self.part = part_connect.Parts()
        self.part.hpn = self.test_part
        self.part.hpn_rev = self.test_rev
        self.part.hptype = 'vapor'
        self.part.manufacture_number = 'XYZ'
        self.part.start_gpstime = Time('2017-07-01 01:00:00', scale='utc').gps
        self.h = cm_handling.Handling(self.test_session)

    def test_get_part(self):
        self.test_session.add(self.part)
        self.test_session.commit()
        located = self.h.get_part_dossier(self.test_part, self.test_rev, 'now', True)
        if len(located.keys()) == 1:
            self.assertTrue(located[located.keys()[0]]['part'].hpn_rev == self.test_rev)
        else:
            self.assertFalse("Part Number should be unique.")

    def test_update_new(self):
        ntp = 'new_test_part'
        data = [[ntp, 'X', 'hpn', ntp],
                [ntp, 'X', 'hpn_rev', 'X'],
                [ntp, 'X', 'hptype', 'vapor_part'],
                [ntp, 'X', 'start_gpstime', 1172530000]]
        part_connect.update_part(self.test_session, data, add_new_part=True)
        located = self.h.get_part_dossier(ntp, 'X', 'now', True)
        if len(located.keys()) == 1:
            self.assertTrue(located[located.keys()[0]]['part'].hpn == ntp)
        else:
            self.assertFalse("Part Number should be unique.")

    def test_update_update(self):
        self.test_session.add(self.part)
        self.test_session.commit()
        data = [[self.test_part, self.test_rev, 'hpn_rev', 'Z']]
        part_connect.update_part(self.test_session, data, add_new_part=False)
        located = self.h.get_part_dossier(self.test_part, 'Z', Time('2017-07-01 01:00:00', scale='utc'), True)
        print(located)
        for k in located.keys():
            print("  **   ", k)
        if len(located.keys()) == 1:
            self.assertTrue(located[located.keys()[0]]['part'].hpn == self.test_part)
        else:
            self.assertFalse()

    def test_add_new_parts(self):
        data = [['part_X', 'X', 'hptype_X', 'mfg_X']]
        p = part_connect.Parts()
        part_connect.add_new_parts(self.test_session, p, data, Time('2017-07-01 01:00:00', scale='utc'), True)
        located = self.h.get_part_dossier('part_X', 'X', Time('2017-07-01 01:00:00'), True)
        print(located)
        for k in located.keys():
            print("  **   ", k)
        if len(located.keys()) == 1:
            self.assertTrue(located[located.keys()[0]]['part'].hpn == 'part_X')
        else:
            self.assertFalse()

    # def test_get_part_revisions(self):
    #    revision = part_connect.__get_part_revisions('test_part', session=self.test_session)
    #    self.assertTrue(revision['Q']['hpn'] == 'test_part')

    def test_datetime(self):
        dt = cm_utils._get_astropytime('2017-01-01', 0.0)
        gps_direct = int(Time('2017-01-01 00:00:00', scale='utc').gps)
        self.assertTrue(int(dt.gps) == gps_direct)


if __name__ == '__main__':
    unittest.main()
