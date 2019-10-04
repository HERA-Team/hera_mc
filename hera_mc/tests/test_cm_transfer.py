# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

<<<<<<< HEAD
"""Testing for `hera_mc.cm_transfer`."""

from __future__ import absolute_import, division, print_function

import os

import pytest

from .. import cm_transfer, mc


def test_classTime():
    pytest.raises(ValueError, cm_transfer.CMVersion.create, None, None)


def test_db_to_csv():
    files_written = cm_transfer.package_db_to_csv(tables='parts')
    assert len(files_written) == 1
    files_written = cm_transfer.package_db_to_csv(tables='all')
    assert len(files_written) == 6
    for fw in files_written:
        os.remove(fw)


def test_main_validation():
    valid = cm_transfer.db_validation(None, 'testing_not_main')
    assert valid
    valid = cm_transfer.db_validation('pw4maindb', 'testing_main')
    assert valid
    pytest.raises(ValueError, cm_transfer.db_validation, False, 'testing_main')
    pytest.raises(ValueError, cm_transfer.db_validation, 'x', 'testing_main')


def test_initialization():
    pytest.raises(ValueError, cm_transfer._initialization, 'testing_main',
                  None)
    t = mc.get_cm_csv_path(testing=True)
    assert 'test_data' in t


def test_check_if_main(mcsession):
    result = cm_transfer.check_if_main(mcsession)
    assert not result


def test_cm_table_info():
    from hera_mc import cm_table_info
    ot = ','.join(cm_table_info.order_the_tables(None))
    assert (ot == 'part_info,connections,parts,geo_location,station_type,'
            'apriori_antenna')
    ot = ','.join(cm_table_info.order_the_tables(['notthere', 'parts']))
    assert ot == 'parts'
=======
"""Testing for `hera_mc.cm_transfer`.
"""

from __future__ import absolute_import, division, print_function

import unittest
import os
import subprocess

from .. import cm_transfer, mc
from ..tests import TestHERAMC, is_onsite
from astropy.time import Time


class TestTransfer(TestHERAMC):

    def setUp(self):
        super(TestTransfer, self).setUp()

    def test_classTime(self):
        self.assertRaises(ValueError, cm_transfer.CMVersion.create, None, None)

    def test_db_to_csv(self):
        files_written = cm_transfer.package_db_to_csv(tables='parts')
        files_written = cm_transfer.package_db_to_csv(tables='all')
        for fw in files_written:
            os.remove(fw)

    def test_main_validation(self):
        valid = cm_transfer.db_validation(None, 'testing_not_main')
        self.assertTrue(valid)
        valid = cm_transfer.db_validation('pw4maindb', 'testing_main')
        self.assertTrue(valid)
        self.assertRaises(ValueError, cm_transfer.db_validation, False, 'testing_main')
        self.assertRaises(ValueError, cm_transfer.db_validation, 'x', 'testing_main')

    def test_initialization(self):
        self.assertRaises(ValueError, cm_transfer._initialization, 'testing_main', None)
        t = mc.get_cm_csv_path(testing=True)
        self.assertTrue('test_data' in t)

    def test_check_if_main(self):
        result = cm_transfer.check_if_main(self.test_session)
        self.assertFalse(result)

    def test_cm_table_info(self):
        from hera_mc import cm_table_info
        ot = ','.join(cm_table_info.order_the_tables(None))
        self.assertTrue(ot == 'part_info,connections,parts,geo_location,station_type,apriori_antenna')
        ot = ','.join(cm_table_info.order_the_tables(['notthere', 'parts']))
        self.assertTrue(ot == 'parts')


if __name__ == '__main__':
    unittest.main()
>>>>>>> add test files
