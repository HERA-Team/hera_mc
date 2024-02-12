# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2019 the HERA Collaboration
# Licensed under the 2-clause BSD License

"""Testing environment setup and teardown for pytest."""
import json
import os
import urllib
import warnings

import pytest
from astropy.time import Time
from astropy.utils import iers

from hera_mc import cm_transfer, mc
from hera_mc.data import DATA_PATH

test_db = None


@pytest.fixture(autouse=True, scope="session")
def setup_and_teardown_package():
    global test_db

    # Do a calculation that requires a current IERS table. This will trigger
    # automatic downloading of the IERS table if needed, including trying the
    # mirror site in python 3 (but won't redownload if a current one exists).
    # If there's not a current IERS table and it can't be downloaded, turn off
    # auto downloading for the tests and turn it back on once all tests are
    # completed (done by extending auto_max_age).
    # Also, the checkWarnings function will ignore IERS-related warnings.
    try:
        t1 = Time.now()
        t1.ut1
    except (urllib.error.URLError, IOError, iers.IERSRangeError):
        iers.conf.auto_max_age = None

    test_db = mc.connect_to_mc_testing_db()
    test_db.create_tables()
    session = test_db.sessionmaker()
    cm_transfer._initialization(
        session=session, cm_csv_path=mc.test_data_path, testing=True
    )

    config_path = os.path.expanduser("~/.hera_mc/mc_config.json")
    with open(config_path) as f:
        config_data = json.load(f)

    if "sqlite_testing" in config_data["databases"]:
        sqlite_filename = config_data["databases"]["sqlite_testing"]["url"].split(
            "sqlite:///"
        )[-1]
        sqlite_dir, sqlite_basename = os.path.split(sqlite_filename)
        if not os.path.exists(sqlite_dir):
            config_data["databases"]["sqlite_testing"]["url"] = (
                "sqlite:///" + os.path.join(DATA_PATH, "test_data", sqlite_basename)
            )
        with open(config_path, "w") as fp:
            json.dump(config_data, fp)

        test_sqlite_db = mc.connect_to_mc_testing_db(forced_db_name="sqlite_testing")
        test_sqlite_db.create_tables()
        sqlite_session = test_sqlite_db.sessionmaker()
        cm_transfer._initialization(
            session=sqlite_session, cm_csv_path=mc.test_data_path, testing=True
        )
    else:
        test_sqlite_db = None

    yield test_db, test_sqlite_db

    iers.conf.auto_max_age = 30
    test_db.drop_tables()
    if test_sqlite_db is not None:
        test_sqlite_db.drop_tables()


@pytest.fixture(scope="function")
def mcsession(setup_and_teardown_package):
    test_db, _ = setup_and_teardown_package
    test_conn = test_db.engine.connect()
    test_trans = test_conn.begin()
    test_session = mc.MCSession(bind=test_conn)

    yield test_session

    test_session.close()
    # rollback - everything that happened with the
    # Session above (including calls to commit())
    # is rolled back.
    with warnings.catch_warnings():
        # If an error was raised, rollback may have already been called. If so, this
        # will give a warning which we filter out here.
        warnings.filterwarnings(
            "ignore", "transaction already deassociated from connection"
        )
        test_trans.rollback()

    # return connection to the Engine
    test_conn.close()

    # delete the hookup cache file
    from .. import cm_hookup

    hookup = cm_hookup.Hookup(None)
    hookup.delete_cache_file()


@pytest.fixture(scope="session")
def mc_sqlite_session(setup_and_teardown_package):
    _, test_sqlite_db = setup_and_teardown_package

    if test_sqlite_db is None:
        pytest.skip()

    test_conn = test_sqlite_db.engine.connect()
    test_trans = test_conn.begin()
    test_sqlite_session = mc.MCSession(bind=test_conn)

    yield test_sqlite_session

    test_sqlite_session.close()
    # rollback - everything that happened with the
    # Session above (including calls to commit())
    # is rolled back.
    test_trans.rollback()

    # return connection to the Engine
    test_conn.close()
