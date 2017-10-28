# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.cm_dataview`.


"""

from __future__ import absolute_import, division, print_function

import unittest

from astropy.time import Time, TimeDelta
import os
import os.path

from hera_mc import mc, cm_utils, cm_dataview
from hera_mc.tests import TestHERAMC


class TestParts(TestHERAMC):

    def setUp(self):
        super(TestParts, self).setUp()

        self.start_time = Time('2017-07-01 01:00:00', scale='utc')
        self.now = cm_utils._get_astropytime('now')
        self.dv = cm_dataview.Dataview(self.test_session, hookup_list_to_cache=['force_specific'])

    def test_dbread_write_file(self):
        output_options = cm_utils.listify('flag,corr')
        filename = ['testflag.txt', 'testcorr.txt']
        parts_list = ['HH0']
        fc_map = self.dv.read_db(parts_list, self.start_time, self.now, dt=1.0)
        for i, output in enumerate(output_options):
            self.dv.write_fc_map_file(filename[i], output)
            self.assertTrue(os.path.isfile(filename[i]))

        # cleanup files
        for file in filename:
            if os.path.exists(file):
                os.remove(file)

    def test_read_files(self):
        filename = [os.path.join(mc.test_data_path, 'HH0_15_flag.txt'), 'not_a_real_file']
        parts, fc_map = self.dv.read_fc_map_files(filename)
        self.assertTrue(parts[0] == 'HH0')


if __name__ == '__main__':
    unittest.main()
