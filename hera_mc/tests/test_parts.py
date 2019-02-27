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

from .. import part_connect, mc, cm_utils, cm_handling, cm_revisions
from ..tests import TestHERAMC


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


class TestParts(TestHERAMC):

    def setUp(self):
        super(TestParts, self).setUp()

        self.test_part = 'test_part'
        self.test_rev = 'Q'
        self.test_hptype = 'antenna'
        self.start_time = Time('2017-07-01 01:00:00', scale='utc')
        self.now = cm_utils.get_astropytime('now')
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

    def test_update_new(self):
        ntp = 'new_test_part'
        data = [[ntp, 'X', 'hpn', ntp],
                [ntp, 'X', 'hpn_rev', 'X'],
                [ntp, 'X', 'hptype', 'antenna'],
                [ntp, 'X', 'start_gpstime', 1172530000]]
        part_connect.update_part(self.test_session, data, add_new_part=True)
        located = self.h.get_part_dossier([ntp], 'X', 'now', True)
        prkey = list(located.keys())[0]
        self.assertTrue(str(located[prkey]).startswith('NEW_TEST_PART:X'))
        if len(list(located.keys())) == 1:
            self.assertTrue(located[list(located.keys())[0]].part.hpn == ntp)
        else:
            self.assertFalse("Part Number should be unique.")

    def test_find_part_type(self):
        pt = self.h.get_part_type_for(self.test_part)
        self.assertTrue(pt == self.test_hptype)

    def test_update_update(self):
        data = [[self.test_part, self.test_rev, 'hpn_rev', 'Z']]
        part_connect.update_part(self.test_session, data, add_new_part=False)
        located = self.h.get_part_dossier([self.test_part], 'Z', Time('2017-07-01 01:00:00', scale='utc'), True)
        if len(list(located.keys())) == 1:
            self.assertTrue(located[list(located.keys())[0]].part.hpn_rev == 'Z')
        else:
            self.assertFalse()

    def test_show_parts(self):
        part_connect.add_part_info(self.test_session, self.test_part, self.test_rev, 'now', 'Testing', 'library_file')
        located = self.h.get_part_dossier([self.test_part], self.test_rev, self.start_time, True)
        with captured_output() as (out, err):
            self.h.show_parts(located)
        self.assertTrue('TEST_PART  | Q     | antenna     |         | 2017-07-01 01:00:37' in out.getvalue().strip())
        with captured_output() as (out, err):
            self.h.show_parts(located, notes_only=True)
        self.assertTrue('library_file' in out.getvalue().strip())
        with captured_output() as (out, err):
            self.h.show_parts({})
        self.assertTrue('Part not found' in out.getvalue().strip())
        located = self.h.get_part_dossier(['A0'], ['H'], 'now', True)
        with captured_output() as (out, err):
            self.h.show_parts(located, notes_only=True)
        self.assertTrue('Comment 2' in out.getvalue().strip())
        located = self.h.get_part_dossier(['HH0'], ['A'], 'now', True)
        with captured_output() as (out, err):
            self.h.show_parts(located)
        self.assertTrue('540901.6E, 6601070.7N, 1052.6m' in out.getvalue().strip())

    def test_part_info(self):
        part_connect.add_part_info(self.test_session, self.test_part, self.test_rev, 'now', 'Testing', 'library_file')
        located = self.h.get_part_dossier([self.test_part], self.test_rev, self.start_time, True)
        self.assertTrue(located[list(located.keys())[0]].part_info[0].comment == 'Testing')

    def test_add_new_parts(self):
        data = [['part_X', 'X', 'station', 'mfg_X']]
        p = part_connect.Parts()
        part_connect.add_new_parts(self.test_session, p, data, Time('2017-07-01 01:00:00', scale='utc'), True)
        located = self.h.get_part_dossier(['part_X'], 'X', Time('2017-07-01 01:00:00'), True)
        if len(list(located.keys())) == 1:
            self.assertTrue(located[list(located.keys())[0]].part.hpn == 'part_X')
        else:
            self.assertFalse()

    def test_cm_version(self):
        self.h.add_cm_version(cm_utils.get_astropytime('now'), 'Test-git-hash')
        gh = self.h.get_cm_version()
        self.assertTrue(gh == 'Test-git-hash')

    def test_get_revisions_of_type(self):
        at_date = None
        rev_types = ['LAST', 'ACTIVE', 'ALL', 'A']
        for rq in rev_types:
            revision = cm_revisions.get_revisions_of_type('HH0', rq, at_date, self.test_session)
            self.assertTrue(revision[0].rev == 'A')
            revision = cm_revisions.get_revisions_of_type(None, rq, at_date, self.test_session)
            self.assertTrue(len(revision) == 0)
        revision = cm_revisions.get_revisions_of_type('TEST_FEED', 'LAST', 'now', self.test_session)
        self.assertEqual(revision[0].rev, 'Z')
        revision = cm_revisions.get_revisions_of_type(None, 'ACTIVE', 'now', self.test_session)
        with captured_output() as (out, err):
            cm_revisions.show_revisions(revision)
        self.assertTrue('No revisions found' in out.getvalue().strip())
        revision = cm_revisions.get_revisions_of_type('HH23', 'ACTIVE', 'now', self.test_session)
        with captured_output() as (out, err):
            cm_revisions.show_revisions(revision)
        self.assertTrue('1096509616.0' in out.getvalue().strip())
        self.assertEqual(revision[0].hpn, 'HH23')
        revision = cm_revisions.get_revisions_of_type('help', 'help')
        self.assertEqual(revision, None)

    def test_listify_hpn(self):
        testing = [['hpn', 'rev'], [['hpn1', 'hpn2', 'hpn3'], 'rev'], [['hpn1', 'hpn2'], ['rev1', 'rev2']]]
        for testit in testing:
            h, r = self.h.listify_hpnrev(testit[0], testit[1])
            self.assertEqual(len(h), len(r))

    def test_listify_hpn_error(self):
        self.assertRaises(ValueError, self.h.listify_hpnrev, ['hpn'], 1)
        self.assertRaises(ValueError, self.h.listify_hpnrev, ['hpn'], ['A', 'B'])
        self.assertRaises(ValueError, self.h.listify_hpnrev, 1, 1)

    def test_get_part_types(self):
        at_date = self.now
        a = self.h.get_part_types('all', at_date)
        self.assertTrue('terminals' in a['feed']['output_ports'])
        with captured_output() as (out, err):
            self.h.show_part_types()
        self.assertTrue('A, B, Q, R, Z' in out.getvalue().strip())

    def test_check_overlapping(self):
        from .. import cm_health
        c = cm_health.check_part_for_overlapping_revisions(self.test_part, self.test_session)
        self.assertTrue(len(c) == 0)
        # Add a test part
        part = part_connect.Parts()
        part.hpn = self.test_part
        part.hpn_rev = 'B'
        part.hptype = self.test_hptype
        part.manufacture_number = 'XYZ'
        part.start_gpstime = self.start_time.gps
        self.test_session.add(part)
        self.test_session.commit()
        c = cm_health.check_part_for_overlapping_revisions(self.test_part, self.test_session)
        self.assertTrue(len(c) == 1)

    def test_datetime(self):
        dt = cm_utils.get_astropytime('2017-01-01', 0.0)
        gps_direct = int(Time('2017-01-01 00:00:00', scale='utc').gps)
        self.assertTrue(int(dt.gps) == gps_direct)


if __name__ == '__main__':
    unittest.main()
