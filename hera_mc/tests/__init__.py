# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Setup testing environment.

"""

import unittest
from hera_mc import mc, cm_transfer

test_db = None


def setup_package():
    global test_db

    test_db = mc.connect_to_mc_testing_db()
    test_db.create_tables()
    session = test_db.sessionmaker()
    # This has to be deleted (if we want to reinstate, we need to wait until after the csv change has happened --
    #                         I don't think we do though.)
    # cm_transfer._initialization(session)


def teardown_package():
    test_db.drop_tables()


# create a class for most tests to inheret from with db setup stuff
class TestHERAMC(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()
