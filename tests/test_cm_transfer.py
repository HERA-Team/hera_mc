# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.cm_transfer`."""

import os

import pytest

from hera_mc import cm_gen_sqlite, cm_hookup, cm_transfer, mc
from hera_mc.cm_partconnect import Connections
from hera_mc.mc import AutomappedDB

# Sometimes a connection is closed, which is handled and doesn't produce an error
# or even a warning under normal testing. But for the warnings test where we
# pass `-W error`, the warning causes an error so we filter it out here.
pytestmark = pytest.mark.filterwarnings("ignore:connection:ResourceWarning:psycopg")


def test_classTime():
    pytest.raises(ValueError, cm_transfer.CMVersion.create, None, None)


def test_gen_sqlite():
    test_hash_file = "test_hash_file.json"
    testsqlite = cm_gen_sqlite.SqliteHandling(
        cm_table_hash_file=test_hash_file, testing=True
    )
    testsqlite.cm_table_list = ["station_type"]
    testsqlite.write_table_hash_dict()
    testsqlite.get_table_hash_dict()
    testsqlite.hash_dict = None
    same_hash = testsqlite.different_table_hash_dict()
    assert same_hash is False
    testsqlite.hash_dict = {"initialization_data_station_type.csv": "abc123"}
    same_hash = testsqlite.different_table_hash_dict()
    assert same_hash is True
    testsqlite.hash_dict = {"notthisone": "noway"}
    same_hash = testsqlite.different_table_hash_dict()
    assert same_hash is True
    testsqlite.cm_table_hash_file = "nosuchfile"
    same_hash = testsqlite.different_table_hash_dict()
    assert same_hash is True
    this_hash = cm_gen_sqlite.hash_file("nosuchfile")
    assert this_hash is None
    os.remove(os.path.join(testsqlite.cm_csv_path, test_hash_file))


def test_update_sqlite(mcsession):
    testsqlite = cm_gen_sqlite.SqliteHandling(testing=True)

    testsqlite.update_sqlite("test_hera_mc.db")

    # connect to this file as a new database, check if it has the same stuff
    new_sqlite_file = os.path.join(testsqlite.cm_csv_path, "test_hera_mc.db")
    new_sqlite_db = AutomappedDB("sqlite:///" + new_sqlite_file)
    new_sqlite_session = new_sqlite_db.sessionmaker()

    # get something out of the sqlite db and out of the postgres db and check they
    # are the same
    psql_connections = mcsession.query(Connections).all()
    assert len(psql_connections) == 139

    sqlite_connections = new_sqlite_session.query(Connections).all()
    assert len(sqlite_connections) == 139

    psql_hookup = cm_hookup.Hookup(mcsession)
    psql_hud = psql_hookup.get_hookup(
        ["HH701"],
        at_date="2019-07-03",
        exact_match=True,
        hookup_type="parts_hera",
    )
    psql_pams = psql_hud[list(psql_hud.keys())[0]].get_part_from_type(
        "post-amp", include_ports=True, include_revs=True
    )

    sqlite_hookup = cm_hookup.Hookup(new_sqlite_session)
    sqlite_hud = sqlite_hookup.get_hookup(
        ["HH701"],
        at_date="2019-07-03",
        exact_match=True,
        hookup_type="parts_hera",
    )
    sqlite_pams = sqlite_hud[list(sqlite_hud.keys())[0]].get_part_from_type(
        "post-amp", include_ports=True, include_revs=True
    )

    assert psql_pams == sqlite_pams

    os.remove(new_sqlite_file)


def test_sqlite_postgres_match(mcsession, mc_sqlite_session):
    # get something out of the sqlite db and out of the postgres db and check they
    # are the same
    psql_connections = mcsession.query(Connections).all()
    assert len(psql_connections) == 139

    sqlite_connections = mc_sqlite_session.query(Connections).all()
    assert len(sqlite_connections) == 139

    psql_hookup = cm_hookup.Hookup(mcsession)
    psql_hud = psql_hookup.get_hookup(
        ["HH701"],
        at_date="2019-07-03",
        exact_match=True,
        hookup_type="parts_hera",
    )
    psql_pams = psql_hud[list(psql_hud.keys())[0]].get_part_from_type(
        "post-amp", include_ports=True, include_revs=True
    )

    sqlite_hookup = cm_hookup.Hookup(mc_sqlite_session)
    sqlite_hud = sqlite_hookup.get_hookup(
        ["HH701"],
        at_date="2019-07-03",
        exact_match=True,
        hookup_type="parts_hera",
    )
    sqlite_pams = sqlite_hud[list(sqlite_hud.keys())[0]].get_part_from_type(
        "post-amp", include_ports=True, include_revs=True
    )

    assert psql_pams == sqlite_pams


def test_db_to_csv():
    pytest.importorskip("pandas")
    files_written = cm_transfer.package_db_to_csv(tables="parts")
    assert len(files_written) == 1
    files_written = cm_transfer.package_db_to_csv(tables="all")
    assert len(files_written) == 7
    for fw in files_written:
        os.remove(fw)


def test_main_validation():
    valid = cm_transfer.db_validation(None, "testing_not_main")
    assert valid
    valid = cm_transfer.db_validation("pw4maindb", "testing_main")
    assert valid
    pytest.raises(ValueError, cm_transfer.db_validation, False, "testing_main")
    pytest.raises(ValueError, cm_transfer.db_validation, "x", "testing_main")


def test_initialization():
    pytest.raises(ValueError, cm_transfer._initialization, "testing_main", None)
    t = mc.get_cm_csv_path(testing=True)
    assert "test_data" in t


def test_check_if_main(mcsession):
    result = cm_transfer.check_if_main(mcsession)
    assert not result
    with mc.MCSessionWrapper(session="testing_not_main") as session:
        result = cm_transfer.check_if_main(session)
    assert not result
    wrapper = mc.MCSessionWrapper(session="testing_main")
    result = cm_transfer.check_if_main(wrapper.session)
    wrapper.wrapup()
    assert result
    wrapper = mc.MCSessionWrapper(session=mcsession)
    wrapper.wrapup(updated=True)


def test_cm_table_info():
    from hera_mc import cm_table_info

    ot = ",".join(cm_table_info.order_the_tables(None))
    t = "part_info,apriori_antenna,part_rosetta,connections,parts,geo_location,station_type"
    assert ot == t
    ot = ",".join(cm_table_info.order_the_tables(["notthere", "parts"]))
    assert ot == "parts"
