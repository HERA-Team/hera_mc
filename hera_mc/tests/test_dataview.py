# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`.

"""

from __future__ import absolute_import, division, print_function

import unittest
from astropy.time import Time, TimeDelta
import os

from .. import mc, cm_utils, cm_dataview
from ..tests import TestHERAMC


class TestParts(TestHERAMC):

    def setUp(self):
        super(TestParts, self).setUp()

    def test_ant_by_day(self):
        dv = cm_dataview.Dataview(session=self.test_session)
        start = cm_utils.get_astropytime(1184354550)
        stop = cm_utils.get_astropytime(1184354600)
        interval = 1.0
        filename = None
        n = dv.ants_by_day(start, stop, interval, filename, output_date_format='jd')
        self.assertEqual(len(n.keys()), 1)
        filename = os.path.expanduser('~/hera_mc_dataview_test.txt')
        n = dv.ants_by_day(start, stop, interval, filename, output_date_format='iso')
        self.assertEqual(len(n.keys()), 1)
        os.remove(filename)

    def test_connected_by_day(self):
        dv = cm_dataview.Dataview(session=self.test_session)
        start = cm_utils.get_astropytime(1184354550)
        stop = cm_utils.get_astropytime(1184354600)
        interval = 10.0
        filename = None
        n = dv.connected_by_day(start, stop, interval)
        self.assertEqual(len(n.keys()), 1)
        filename = os.path.expanduser('~/hera_mc_dataview_test.txt')
        n = dv.connected_by_day(start, stop, interval, output=filename, output_date_format='iso')
        self.assertEqual(len(n.keys()), 1)
        os.remove(filename)


if __name__ == '__main__':
    unittest.main()
