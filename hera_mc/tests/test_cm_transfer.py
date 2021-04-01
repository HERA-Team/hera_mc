# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.cm_transfer`."""

import os

import pytest

from .. import cm_transfer, mc, cm_gen_sqlite


def test_classTime():
    pytest.raises(ValueError, cm_transfer.CMVersion.create, None, None)


def test_gen_sqlite():
    test_hash_file = 'test_hash_file.json'
    test_hash_dict = {'initialization_data_station_type.csv': 'abc123'}
    cm_gen_sqlite.write_table_hash_info(test_hash_dict, hash_file=test_hash_file)
    hash_dict = cm_gen_sqlite.get_table_hash_info(['station_type'])
    assert 'initialization_data_station_type.csv' in hash_dict.keys()
    same_hash = cm_gen_sqlite.same_table_hash_info(test_hash_dict, test_hash_file)
    assert same_hash is True
    same_hash = cm_gen_sqlite.same_table_hash_info(hash_dict, test_hash_file)
    assert same_hash is False
    same_hash = cm_gen_sqlite.same_table_hash_info({'notthisone': 'noway'}, test_hash_file)
    assert same_hash is False
    same_hash = cm_gen_sqlite.same_table_hash_info(test_hash_dict, 'nosuchfile')
    assert same_hash is False
    this_hash = cm_gen_sqlite.hash_file('nosuchfile')
    assert this_hash is None
    cm_gen_sqlite.update_sqlite(['station_type'], 'test_hera_mc.db')
    CM_CSV_PATH = mc.get_cm_csv_path()
    os.remove(os.path.join(CM_CSV_PATH, test_hash_file))
    os.remove(os.path.join(CM_CSV_PATH, 'test_hera_mc.db'))


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
