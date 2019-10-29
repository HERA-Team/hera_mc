# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2019 the HERA Collaboration
# Licensed under the 2-clause BSD License

"""Testing environment setup and teardown for pytest."""
from __future__ import absolute_import, division, print_function

import pytest
import six.moves.urllib as urllib
from astropy.utils import iers
from astropy.time import Time

from hera_mc import mc, cm_transfer

test_db = None


@pytest.fixture(autouse=True, scope="session")
def setup_and_teardown_package():
    global test_db

    # Try to download the latest IERS table. If the download succeeds, run a
    # computation that requires the values, so they are cached for all future
    # tests. If it fails, turn off auto downloading for the tests and turn it
    # back on once all tests are completed (done by extending auto_max_age).
    # Also, the checkWarnings function will ignore IERS-related warnings.
    try:
        iers.IERS_A.open(iers.IERS_A_URL)
        t1 = Time.now()
        t1.ut1
    except(urllib.error.URLError, IOError):
        iers.conf.auto_max_age = None

    test_db = mc.connect_to_mc_testing_db()
    test_db.create_tables()
    session = test_db.sessionmaker()
    cm_transfer._initialization(session=session, cm_csv_path=mc.test_data_path)

    yield test_db

    iers.conf.auto_max_age = 30
    test_db.drop_tables()


@pytest.fixture(scope='function')
def mcsession(setup_and_teardown_package):
    test_db = setup_and_teardown_package
    test_conn = test_db.engine.connect()
    test_trans = test_conn.begin()
    test_session = mc.MCSession(bind=test_conn)

    yield test_session

    test_session.close()
    # rollback - everything that happened with the
    # Session above (including calls to commit())
    # is rolled back.
    test_trans.rollback()

    # return connection to the Engine
    test_conn.close()

    # delete the hookup cache file
    from .. import cm_hookup
    hookup = cm_hookup.Hookup(session=test_session)
    hookup.delete_cache_file()
