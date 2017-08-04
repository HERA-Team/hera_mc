# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Setup testing environment.

"""

import unittest
from hera_mc import mc, cm_transfer
import warnings
import sys

test_db = None


def setup_package():
    global test_db

    test_db = mc.connect_to_mc_testing_db()
    test_db.create_tables()
    session = test_db.sessionmaker()
    cm_transfer._initialization(session, mc.test_data_path)


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


# Functions that are useful for testing:
def clearWarnings():
    """Quick code to make warnings reproducible."""
    for name, mod in list(sys.modules.items()):
        try:
            reg = getattr(mod, "__warningregistry__", None)
        except ImportError:
            continue
        if reg:
            reg.clear()


def checkWarnings(func, func_args=[], func_kwargs={},
                  category=UserWarning,
                  nwarnings=1, message=None, known_warning=None):
    """Function to check expected warnings."""

    clearWarnings()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")  # All warnings triggered
        retval = func(*func_args, **func_kwargs)  # Run function
        # Verify
        if len(w) != nwarnings:
            print('wrong number of warnings. Expected number was {nexp}, '
                  'actual number was {nact}.'.format(nexp=nwarnings, nact=len(w)))
            for idx, wi in enumerate(w):
                print('warning {i} is: {w}'.format(i=idx, w=wi))
            assert(False)
        else:
            for i, w_i in enumerate(w):
                if w_i.category is not category[i]:
                    assert(False)
                if message[i] is not None:
                    if message[i] not in str(w_i.message):
                        print('expected message ' + str(i) + ' was: ', message[i])
                        print('message ' + str(i) + ' was: ', str(w_i.message))
                        assert(False)
        return retval
