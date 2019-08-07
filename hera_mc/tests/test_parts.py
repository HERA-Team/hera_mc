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

from hera_mc import cm_partconnect, mc, cm_utils, cm_handling, cm_revisions
from hera_mc.tests import TestHERAMC, checkWarnings


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
        part = cm_partconnect.Parts()
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
        cm_partconnect.update_part(self.test_session, data)
        located = self.h.get_part_dossier(hpn=[ntp], rev='X', at_date='now', exact_match=True)
        prkey = list(located.keys())[0]
        self.assertTrue(str(located[prkey]).startswith('NEW_TEST_PART:X'))
        if len(list(located.keys())) == 1:
            self.assertTrue(located[list(located.keys())[0]].part.hpn == ntp)
        else:
            self.assertFalse("Part Number should be unique.")

    def test_find_part_type(self):
        pt = self.h.get_part_type_for(self.test_part)
        self.assertTrue(pt == self.test_hptype)

    def test_update_part(self):
        data = [[self.test_part, self.test_rev, 'hpn_rev', 'Z']]
        cm_partconnect.update_part(self.test_session, data)
        dtq = Time('2017-07-01 01:00:00', scale='utc')
        located = self.h.get_part_dossier(hpn=[self.test_part], rev='Z', at_date=dtq, exact_match=True)
        if len(list(located.keys())) == 1:
            self.assertTrue(located[list(located.keys())[0]].part.hpn_rev == 'Z')
        else:
            self.assertFalse()

    def test_part_dossier(self):
        located = self.h.get_part_dossier(hpn=None, rev=None, at_date='now', sort_notes_by='part', exact_match=True)
        self.assertTrue(list(located.keys())[0] == '__Sys__')
        located = self.h.get_part_dossier(hpn=None, rev=None, at_date='now', sort_notes_by='post', exact_match=True)
        with captured_output() as (out, err):
            self.h.show_parts(located, notes_only=True)
        self.assertTrue('System:A' in out.getvalue().strip())

    def test_show_parts(self):
        cm_partconnect.add_part_info(self.test_session, self.test_part, self.test_rev, self.start_time, 'Testing', 'library_file')
        located = self.h.get_part_dossier(hpn=[self.test_part], rev=self.test_rev, at_date='now', exact_match=True)
        with captured_output() as (out, err):
            self.h.show_parts(located)
        self.assertTrue('TEST_PART  | Q     | antenna     |         | 2017-07-01 01:00:37' in out.getvalue().strip())
        with captured_output() as (out, err):
            self.h.show_parts(located, notes_only=True)
        self.assertTrue('library_file' in out.getvalue().strip())
        with captured_output() as (out, err):
            self.h.show_parts({})
        self.assertTrue('Part not found' in out.getvalue().strip())
        located = self.h.get_part_dossier(hpn=['A0'], rev=['H'], at_date='now', exact_match=True)
        with captured_output() as (out, err):
            self.h.show_parts(located, notes_only=True)
        self.assertTrue('Comment 2' in out.getvalue().strip())
        located = self.h.get_part_dossier(hpn=['HH0'], rev=['A'], at_date='now', exact_match=True)
        with captured_output() as (out, err):
            self.h.show_parts(located)
        self.assertTrue('540901.6E, 6601070.7N, 1052.6m' in out.getvalue().strip())

    def test_part_info(self):
        cm_partconnect.add_part_info(self.test_session, self.test_part, self.test_rev, Time('2017-07-01 01:00:00'),
                                     'Testing', 'library_file')
        located = self.h.get_part_dossier(hpn=[self.test_part], rev=self.test_rev, at_date='now', exact_match=True)
        self.assertTrue(located[list(located.keys())[0]].part_info[0].comment == 'Testing')

    def test_add_new_parts(self):
        data = [['part_X', 'X', 'station', 'mfg_X']]
        p = cm_partconnect.Parts()
        cm_partconnect.add_new_parts(self.test_session, data, Time('2017-07-01 01:00:00', scale='utc'), True)
        located = self.h.get_part_dossier(hpn=['part_X'], rev='X', at_date=Time('2017-07-01 01:00:00'), exact_match=True)
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

    def test_match_listify(self):
        testing = [['hpn', 'rev'], [['hpn1', 'hpn2', 'hpn3'], 'rev'], [['hpn1', 'hpn2'], ['rev1', 'rev2']]]
        for testit in testing:
            h, r = cm_utils.match_listify(testit[0], testit[1])
            self.assertEqual(len(h), len(r))
        self.assertRaises(ValueError, cm_utils.match_listify, ['hpn'], ['A', 'B'])
        x = cm_utils.listify(1)
        self.assertEqual(x[0], 1)

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
        part = cm_partconnect.Parts()
        part.hpn = self.test_part
        part.hpn_rev = 'B'
        part.hptype = self.test_hptype
        part.manufacture_number = 'XYZ'
        part.start_gpstime = self.start_time.gps
        self.test_session.add(part)
        self.test_session.commit()
        c = checkWarnings(cm_health.check_part_for_overlapping_revisions, [self.test_part, self.test_session],
                          message='Q and B are overlapping revisions of part test_part')
        self.assertTrue(len(c) == 1)

    def test_datetime(self):
        dt = cm_utils.get_astropytime('2017-01-01', 0.0)
        gps_direct = int(Time('2017-01-01 00:00:00', scale='utc').gps)
        self.assertTrue(int(dt.gps) == gps_direct)


if __name__ == '__main__':
    unittest.main()
