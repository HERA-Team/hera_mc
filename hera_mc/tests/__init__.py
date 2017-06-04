# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Setup testing environment.

"""

from hera_mc import mc

test_db = None


def setup_package():
    global test_db

    test_db = mc.connect_to_mc_testing_db()
    test_db.create_tables()


def teardown_package():
    test_db.drop_tables()
