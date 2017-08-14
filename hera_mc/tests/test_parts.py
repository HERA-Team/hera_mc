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

from hera_mc import part_connect, mc, cm_utils, cm_handling, cm_revisions
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
        self.part.start = Time('2017-07-01 01:00:00', scale='utc')
        self.part.start_gpstime = self.part.start.gps
        self.h = cm_handling.Handling(self.test_session)
        self.test_session.add(self.part)
        self.test_session.commit()

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
        data = [[self.test_part, self.test_rev, 'hpn_rev', 'Z']]
        part_connect.update_part(self.test_session, data, add_new_part=False)
        located = self.h.get_part_dossier(self.test_part, 'Z', Time('2017-07-01 01:00:00', scale='utc'), True)
        if len(located.keys()) == 1:
            self.assertTrue(located[located.keys()[0]]['part'].hpn_rev == 'Z')
        else:
            self.assertFalse()

    def test_add_new_parts(self):
        data = [['part_X', 'X', 'hptype_X', 'mfg_X']]
        p = part_connect.Parts()
        part_connect.add_new_parts(self.test_session, p, data, Time('2017-07-01 01:00:00', scale='utc'), True)
        located = self.h.get_part_dossier('part_X', 'X', Time('2017-07-01 01:00:00'), True)
        if len(located.keys()) == 1:
            self.assertTrue(located[located.keys()[0]]['part'].hpn == 'part_X')
        else:
            self.assertFalse()

    def test_get_revisions_of_type(self):
        at_date =  self.part.start
        full_req = ['vapor']
        rev_types = ['LAST','ACTIVE','ALL', self.test_rev]#, 'FULL']
        for rq in rev_types:
            print(rq)
            revision = cm_revisions.get_revisions_of_type(self.test_part, rq, at_date, full_req, self.test_session)
            self.assertTrue(revision[0].rev == self.test_rev)


    def test_check_overlapping(self):
        c = cm_revisions.check_part_for_overlapping_revisions(self.test_part, self.test_session)
        self.assertTrue(len(c) == 0)


    def test_check_rev(self):
        full_req = ['vapor']
        rev_types = ['LAST', 'ACTIVE']#, 'FULL']
        for r in rev_types:
            print(r)
            c = cm_revisions.check_rev(self.test_part, self.test_rev, r, self.part.start, full_req, self.test_session)
            self.assertTrue(c)


    def test_datetime(self):
        dt = cm_utils._get_astropytime('2017-01-01', 0.0)
        gps_direct = int(Time('2017-01-01 00:00:00', scale='utc').gps)
        self.assertTrue(int(dt.gps) == gps_direct)


if __name__ == '__main__':
    unittest.main()
