# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.cm_transfer`."""

import os

import pytest

from .. import cm_transfer, mc


def test_classTime():
    pytest.raises(ValueError, cm_transfer.CMVersion.create, None, None)


def test_db_to_csv():
    files_written = cm_transfer.package_db_to_csv(tables='parts')
    assert len(files_written) == 1
    files_written = cm_transfer.package_db_to_csv(tables='all')
    assert len(files_written) == 7
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
    t = 'part_info,apriori_antenna,part_rosetta,connections,parts,geo_location,station_type'
    assert (ot == t)
    ot = ','.join(cm_table_info.order_the_tables(['notthere', 'parts']))
    assert ot == 'parts'
