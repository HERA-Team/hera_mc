# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.cm_transfer`."""

import argparse
import sys
import subprocess
import os

import pytest

import hera_mc
from hera_mc import cm_utils, mc


def test_log():
    from argparse import Namespace
    a = Namespace(test=True, val=0)
    cm_utils.log('testing', args=a)


def test_various():
    a = 'a'
    args = argparse.Namespace(a='def_test', unittesting='')
    x = cm_utils.query_default(a, args)
    assert x == 'def_test'
    args = argparse.Namespace(a='def_test', unittesting='none')
    x = cm_utils.query_default(a, args)
    assert x is None
    args = argparse.Namespace(a='def_test', unittesting='false')
    x = cm_utils.query_default(a, args)
    assert not x
    args = argparse.Namespace(a='def_test', unittesting='true')
    x = cm_utils.query_default(a, args)
    assert x
    args = argparse.Namespace(a='def_test', unittesting='unittest')
    x = cm_utils.query_default(a, args)
    assert x == 'unittest'
    spk = cm_utils.make_part_key(None, None)
    assert spk == cm_utils.system_wide_key
    a, b, c = cm_utils.split_part_key('a:b:c')
    assert c == 'c'
    is_active = cm_utils.is_active(None, None, None)
    assert is_active
    t_tst = cm_utils.get_astropytime('now')
    out = cm_utils.get_stopdate(t_tst)
    assert out == t_tst
    d = cm_utils.get_time_for_display(None)
    assert d == 'None'
    c = cm_utils.put_keys_in_order(['1:A:Z', '2:B:X'], 'RPN')
    assert c[0] == '1:A:Z'


@pytest.mark.parametrize(("input", "expected"),
                         [(None, None), ('Test', 'Test'), (['a', 'b'], 'a,b'), (1, '1')])
def test_stringify(input, expected):
    x = cm_utils.stringify(input)
    if expected is not None:
        assert x == expected
    else:
        assert x is expected


@pytest.mark.parametrize(("input", "expected"),
                         [('Test', ['Test']),
                          ('a,b', ['a', 'b']),
                          (['Test'], ['Test']),
                          (1, [1]),
                          ('1-3', [1, 2, 3])])
def test_listify(input, expected):
    x = cm_utils.listify(input)
    assert x == expected
    x = cm_utils.listify(None, None_as_list=False)
    assert x is None
    x = cm_utils.listify(None, None_as_list=True)
    assert x[0] is None
    x = cm_utils.listify('0-3', prefix='Test')
    assert x == ['Test0', 'Test1', 'Test2', 'Test3']
    x = cm_utils.listify('0,3,4', prefix='Test', padding=3)
    assert x == ['Test000', 'Test003', 'Test004']
    x = cm_utils.listify('N0-A', prefix='Test', padding=3)
    assert x == ['TestN0-A']


def test_match_list():
    x = cm_utils.match_list(['a', 'b'], 'c', None)
    y = list(x)
    assert y[1][1] == 'c'
    x = cm_utils.match_list('a', ['b', 'c'], 'upper')
    y = list(x)
    assert y[1][0] == 'A'
    x = cm_utils.match_list(1, 2, 'lower')
    y = list(x)
    assert y[0][0] == '1'
    with pytest.raises(ValueError) as ml:
        cm_utils.match_list([1, 2, 3], [1, 2, 3, 4, 5])
    assert str(ml.value).startswith('Lists must be same length')
    with pytest.raises(ValueError) as ml:
        cm_utils.match_list([1], [2], 'x')
    assert str(ml.value).startswith('Invalid case_type.')


def test_peel():
    x = cm_utils.peel_key('X9:V', 'RNP')
    assert x[0] == 'V'
    x = cm_utils.peel_key('X9:V', 'PRN')
    assert x[0] == 'X'


def test_to_upper():
    x = cm_utils.to_upper('a')
    assert x == 'A'
    x = cm_utils.to_upper(['a'])
    assert x[0] == 'A'
    x = cm_utils.to_upper(1)
    assert x == '1'
    x = cm_utils.to_upper(None)
    assert x is None


def test_to_lower():
    x = cm_utils.to_lower('a')
    assert x == 'a'
    x = cm_utils.to_lower(['a'])
    assert x[0] == 'a'
    x = cm_utils.to_lower(1)
    assert x == '1'
    x = cm_utils.to_lower(None)
    assert x is None


def test_verbosity():
    sys.argv = ['test', '-v', '0']
    p = argparse.ArgumentParser()
    cm_utils.add_verbosity_args(p)
    args = p.parse_args()
    x = cm_utils.parse_verbosity(args.verbosity)
    assert x == 0
    x = cm_utils.parse_verbosity(None)
    assert x == 1
    x = cm_utils.parse_verbosity('vv')
    assert x == 3
    with pytest.raises(ValueError) as tv:
        cm_utils.parse_verbosity('x')
    assert str(tv.value).startswith("Invalid argument to verbosity")


def test_datetime():
    from astropy.time import Time
    sys.argv = ['test']
    p = argparse.ArgumentParser()
    cm_utils.add_date_time_args(p)
    args = p.parse_args()
    assert args.date == 'now'
    assert args.time == 0.0
    import datetime
    tout = cm_utils.get_astropytime(datetime.datetime.now())
    assert type(tout) == Time
    tout = cm_utils.get_astropytime(2400001.0)
    assert type(tout) == Time
    pytest.raises(ValueError, cm_utils.get_astropytime, 0.0)
    tout = cm_utils.get_astropytime('none')
    assert tout is None
    tout = cm_utils.get_astropytime('2018/1/1', '0.0')
    assert type(tout) == Time
    pytest.raises(ValueError, cm_utils.get_astropytime, '18/1/1')
    tout = cm_utils.get_astropytime('2018/1/1', '12:30:00')
    assert type(tout) == Time
    pytest.raises(ValueError, cm_utils.get_astropytime, '2018/1/1', '0:0:0:0')
    pytest.raises(ValueError, cm_utils.get_astropytime, '2018/1/1', 'x')


def test_put_keys_in_order():
    x = cm_utils.put_keys_in_order(['HH1', 'HH0:A'])
    assert x[0] == 'HH0:A'


def test_get_cm_repo_git_hash():
    cm_hash = cm_utils.get_cm_repo_git_hash(cm_csv_path=mc.test_data_path)

    git_hash = subprocess.check_output(['git', '-C', '.', 'rev-parse', 'HEAD'],
                                       stderr=subprocess.STDOUT).strip()

    assert cm_hash, git_hash

    example_config_path = os.path.join(os.path.dirname(hera_mc.__path__[0]),
                                       'ci', 'example_config.json')
    pytest.raises(ValueError, cm_utils.get_cm_repo_git_hash,
                  mc_config_path=example_config_path)
