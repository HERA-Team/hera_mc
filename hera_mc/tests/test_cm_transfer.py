# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.cm_transfer`.
"""

from __future__ import absolute_import, division, print_function

import unittest
import os
import subprocess

from .. import cm_transfer
from ..tests import TestHERAMC
from astropy.time import Time


class TestTransfer(TestHERAMC):

    def setUp(self):
        super(TestTransfer, self).setUp()

    def test_db_to_csv(self):
        files_written = cm_transfer.package_db_to_csv(tables='parts')
        files_written = cm_transfer.package_db_to_csv(tables='all')
        for fw in files_written:
            os.remove(fw)

    def test_main_validation(self):
        valid = cm_transfer.db_validation(None, 'testing_not_main')
        self.assertTrue(valid)
        valid = cm_transfer.db_validation(False, 'testing_main')
        self.assertFalse(valid)
        valid = cm_transfer.db_validation('x', 'testing_main')
        self.assertFalse(valid)
        valid = cm_transfer.db_validation('pw4maindb', 'testing_main')
        self.assertTrue(valid)

    def test_initialization(self):
        t = cm_transfer._initialization(session='testing_main', cm_csv_path=None)
        self.assertFalse(t)


if __name__ == '__main__':
    unittest.main()
