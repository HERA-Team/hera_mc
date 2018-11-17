# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.cm_transfer`.
"""

from __future__ import absolute_import, division, print_function

import unittest
import six
import argparse
import sys

from .. import cm_utils
from ..tests import TestHERAMC


class TestUtils(TestHERAMC):

    def test_log(self):
        from argparse import Namespace
        a = Namespace(test=True, val=0)
        cm_utils.log('nosetests', args=a)

    def test_various(self):
        a, b, c, d = cm_utils.split_connection_key('a:b:c:d')
        self.assertEqual(c[0], 'c')
        args = argparse.Namespace(a='def_test', unittesting='')
        x = cm_utils.query_default(a, args)
        self.assertEqual(x, 'def_test')
        args = argparse.Namespace(a='def_test', unittesting='none')
        x = cm_utils.query_default(a, args)
        self.assertEqual(x, None)
        args = argparse.Namespace(a='def_test', unittesting='unittest')
        x = cm_utils.query_default(a, args)
        self.assertEqual(x, 'unittest')

    def test_stringify_listify(self):
        x = cm_utils.stringify(None)
        self.assertTrue(x is None)
        x = cm_utils.stringify('Test')
        self.assertEqual(x, 'Test')
        x = cm_utils.stringify(['a', 'b'])
        self.assertEqual(x, 'a,b')
        x = cm_utils.stringify(0)
        self.assertEqual(x, '0')
        x = cm_utils.listify(None)
        self.assertTrue(x is None)
        x = cm_utils.listify('Test')
        self.assertEqual(x[0], 'Test')
        x = cm_utils.listify('a,b')
        self.assertEqual(x[0], 'a')
        x = cm_utils.listify(['a', 'b'])
        self.assertEqual(x[0], 'a')

    def test_verbosity(self):
        sys.argv = ['test', '-v', '0']
        p = argparse.ArgumentParser()
        cm_utils.add_verbosity_args(p)
        args = p.parse_args()
        x = cm_utils.parse_verbosity(args.verbosity)
        self.assertEqual(x, 0)
        x = cm_utils.parse_verbosity(None)
        self.assertEqual(x, 1)
        x = cm_utils.parse_verbosity('vv')
        self.assertEqual(x, 3)
        self.assertRaises(ValueError, cm_utils.parse_verbosity, 'x')

    def test_datetime(self):
        from astropy.time import Time
        sys.argv = ['test']
        p = argparse.ArgumentParser()
        cm_utils.add_date_time_args(p)
        args = p.parse_args()
        self.assertEqual(args.date, 'now')
        self.assertEqual(args.time, 0.0)
        import datetime
        tout = cm_utils.get_astropytime(datetime.datetime.now())
        self.assertEqual(type(tout), Time)
        tout = cm_utils.get_astropytime(2400001.0)
        self.assertEqual(type(tout), Time)
        self.assertRaises(ValueError, cm_utils.get_astropytime, 0.0)
        tout = cm_utils.get_astropytime('none')
        self.assertEqual(tout, None)
        tout = cm_utils.get_astropytime('2018/1/1', '0.0')
        self.assertEqual(type(tout), Time)
        self.assertRaises(ValueError, cm_utils.get_astropytime, '18/1/1')
        tout = cm_utils.get_astropytime('2018/1/1', '12:30:00')
        self.assertEqual(type(tout), Time)
        self.assertRaises(ValueError, cm_utils.get_astropytime, '2018/1/1', '0:0:0:0')
        self.assertRaises(ValueError, cm_utils.get_astropytime, '2018/1/1', 'x')

    def test_put_keys_in_numerical_order(self):
        x = cm_utils.put_keys_in_numerical_order(['HH1', 'HH0:A'])
        self.assertEqual(x[0], 'HH0:A')


if __name__ == '__main__':
    unittest.main()
