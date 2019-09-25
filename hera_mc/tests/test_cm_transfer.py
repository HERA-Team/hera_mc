# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.cm_transfer`."""

from __future__ import absolute_import, division, print_function

import os

import pytest

from .. import cm_transfer, mc


def test_classTime():
    pytest.raises(ValueError, cm_transfer.CMVersion.create, None, None)


def test_db_to_csv():
    files_written = cm_transfer.package_db_to_csv(tables='parts')
    files_written = cm_transfer.package_db_to_csv(tables='all')
    for fw in files_written:
        os.remove(fw)


def test_main_validation():
    valid = cm_transfer.db_validation(None, 'testing_not_main')
    assert valid
    valid = cm_transfer.db_validation(False, 'testing_main')
    assert not valid
    valid = cm_transfer.db_validation('x', 'testing_main')
    assert not valid
    valid = cm_transfer.db_validation('pw4maindb', 'testing_main')
    assert valid


def test_initialization():
    t = cm_transfer._initialization(session='testing_main', cm_csv_path=None)
    assert not t
    t = mc.get_cm_csv_path(testing=True)
    assert 'test_data' in t


def test_check_if_main(mcsession):
    result = cm_transfer.check_if_main(mcsession)
    assert not result


def test_cm_table_info():
    from hera_mc import cm_table_info
    ot = ','.join(cm_table_info.order_the_tables(None))
    assert ot == 'part_info,connections,parts,geo_location,station_type,apriori_antenna'
    ot = ','.join(cm_table_info.order_the_tables(['notthere', 'parts']))
    assert ot == 'parts'
