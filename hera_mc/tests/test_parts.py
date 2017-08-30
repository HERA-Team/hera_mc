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
        self.test_hptype = 'vapor'
        self.start_time = Time('2017-07-01 01:00:00', scale='utc')
        self.now = cm_utils._get_astropytime('now')
        self.h = cm_handling.Handling(self.test_session)

        # Add a test part
        part = part_connect.Parts()
        part.hpn = self.test_part
        part.hpn_rev = self.test_rev
        part.hptype = self.test_hptype
        part.manufacture_number = 'XYZ'
        part.start_gpstime = self.start_time.gps
        self.test_session.add(part)
        self.test_session.commit()
        # Add part_info
        part_info = part_connect.PartInfo()
        part_info.hpn = self.test_part
        part_info.hpn_rev = self.test_rev
        part_info.posting_gpstime = self.start_time.gps
        part_info.comment = 'TEST'
        self.test_session.add(part_info)
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

    def test_find_part_type(self):
        pt = self.h.get_part_type_for(self.test_part)
        self.assertTrue(pt == self.test_hptype)

    def test_update_update(self):
        data = [[self.test_part, self.test_rev, 'hpn_rev', 'Z']]
        part_connect.update_part(self.test_session, data, add_new_part=False)
        located = self.h.get_part_dossier(self.test_part, 'Z', Time('2017-07-01 01:00:00', scale='utc'), True)
        if len(located.keys()) == 1:
            self.assertTrue(located[located.keys()[0]]['part'].hpn_rev == 'Z')
        else:
            self.assertFalse()

    def test_part_info(self):
        located = self.h.get_part_dossier(self.test_part, self.test_rev, self.start_time, True)
        self.assertTrue(located[located.keys()[0]]['part_info'].comment == 'TEST')

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
        at_date = self.now
        fr = ['f_engine']
        rev_types = ['LAST', 'ACTIVE', 'ALL', 'FULL', 'A']
        for rq in rev_types:
            revision = cm_revisions.get_revisions_of_type('HH0', rq, at_date, fr, self.test_session)
            self.assertTrue(revision[0].rev == 'A')

    def test_check_overlapping(self):
        c = cm_revisions.check_part_for_overlapping_revisions(self.test_part, self.test_session)
        self.assertTrue(len(c) == 0)

    def test_check_rev(self):
        fr = ['f_engine']
        tcr = {'LAST': [self.test_part, self.test_rev],
               'ACTIVE': [self.test_part, self.test_rev],
               'FULL': ['HH0', 'A']}
        rev_types = ['LAST', 'ACTIVE', 'FULL']
        for r in rev_types:
            c = cm_revisions.check_rev(tcr[r][0], tcr[r][1], r, self.now, fr, self.test_session)
            self.assertTrue(c)

    def test_datetime(self):
        dt = cm_utils._get_astropytime('2017-01-01', 0.0)
        gps_direct = int(Time('2017-01-01 00:00:00', scale='utc').gps)
        self.assertTrue(int(dt.gps) == gps_direct)


if __name__ == '__main__':
    unittest.main()
