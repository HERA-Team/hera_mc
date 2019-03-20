# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Setup testing environment.

"""

from __future__ import absolute_import, division, print_function

import unittest
import socket
import warnings
import sys
import collections

from hera_mc import mc, cm_transfer
from hera_mc.mc_session import MCSession
from hera_mc.utils import get_iterable

test_db = None


def is_onsite():
    return (socket.gethostname() == 'qmaster')


def setup_package():
    global test_db

    test_db = mc.connect_to_mc_testing_db()
    test_db.create_tables()
    session = test_db.sessionmaker()
    cm_transfer._initialization(session=session, cm_csv_path=mc.test_data_path)


def teardown_package():
    test_db.drop_tables()


# create a class for most tests to inheret from with db setup stuff
class TestHERAMC(unittest.TestCase):

    def setUp(self):
        self.test_db = test_db
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = MCSession(bind=self.test_conn)
        import astropy
        astropy.utils.iers.conf.auto_max_age = None

    def tearDown(self):
        self.test_session.close()

        # rollback - everything that happened with the
        # Session above (including calls to commit())
        # is rolled back.
        self.test_trans.rollback()

        # return connection to the Engine
        self.test_conn.close()

        # delete the hookup cache file
        from .. import cm_hookup
        hookup = cm_hookup.Hookup(session=self.test_session)
        hookup.delete_cache_file()


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
    if (not isinstance(category, list) or len(category) == 1) and nwarnings > 1:
        if isinstance(category, list):
            category = category * nwarnings
        else:
            category = [category] * nwarnings

    if (not isinstance(message, list) or len(message) == 1) and nwarnings > 1:
        if isinstance(message, list):
            message = message * nwarnings
        else:
            message = [message] * nwarnings

    category = get_iterable(category)
    message = get_iterable(message)

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
