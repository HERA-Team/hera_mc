# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`.

"""

from __future__ import absolute_import, division, print_function

import unittest
from astropy.time import Time, TimeDelta

from .. import mc, cm_utils, cm_dataview
from ..tests import TestHERAMC


class TestParts(TestHERAMC):

    def setUp(self):
        super(TestParts, self).setUp()

    def test_ant_by_day(self):
        dv = cm_dataview.Dataview()
        start = cm_utils.get_astropytime(1184354550)
        stop = cm_utils.get_astropytime(1184354600)
        interval = 1.0
        filename = None
        x = dv.ants_by_day(start, stop, interval, filename, station_types_to_check='default', output_date_format='jd')
        k0 = str(list(x.keys())[0]).split('.')[0]
        self.assertTrue(k0 == '2457952')


if __name__ == '__main__':
    unittest.main()
