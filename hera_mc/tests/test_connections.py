# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`."""

from __future__ import absolute_import, division, print_function

import sys
from contextlib import contextmanager

import six
import pytest
from astropy.time import Time

from .. import cm_partconnect, cm_handling, cm_health


# define a context manager for checking stdout
# from https://stackoverflow.com/questions/4219717/
#   how-to-assert-output-with-nosetest-unittest-in-python
@contextmanager
def captured_output():
    new_out, new_err = six.StringIO(), six.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


@pytest.fixture(scope='function')
def conns(mcsession):

    test_hpn = ['test_part1', 'test_part2']
    test_rev = 'Q'
    test_mfg = 'XYZ'
    test_hptype = 'vapor'
    test_time = Time('2017-07-01 01:00:00', scale='utc').gps
    query_time = Time('2017-08-01 01:00:00', scale='utc')

    session = mcsession
    for tp in test_hpn:
        part = cm_partconnect.Parts()
        part.hpn = tp
        part.hpn_rev = test_rev
        part.hptype = test_hptype
        part.manufacture_number = test_mfg
        part.start_gpstime = test_time
        session.add(part)
    session.commit()

    # Add test connection
    connection = cm_partconnect.Connections()
    connection.upstream_part = test_hpn[0]
    connection.up_part_rev = test_rev
    connection.downstream_part = test_hpn[1]
    connection.down_part_rev = test_rev
    connection.upstream_output_port = 'up_and_out'
    connection.downstream_input_port = 'down_and_in'
    connection.start_gpstime = test_time
    session.add(connection)
    session.commit()

    cm_handle = cm_handling.Handling(session)

    class DataHolder(object):
        def __init__(self, test_session, test_hpn, test_rev, test_hptype,
                     test_mfg, test_time, query_time, cm_handle):
            self.test_session = test_session
            self.test_hpn = test_hpn
            self.test_rev = test_rev
            self.test_hptype = test_hptype
            self.test_mfg = test_mfg
            self.test_time = test_time
            self.query_time = query_time
            self.cm_handle = cm_handle

    conns = DataHolder(session, test_hpn, test_rev, test_hptype, test_mfg,
                       test_time, query_time, cm_handle)

    # yields the data we need but will continue to the del call after tests
    yield conns

    # some post-test object cleanup
    del(conns)

    return


def test_update_new(conns):
    u = 'new_test_part_up'
    d = 'new_test_part_down'
    r = 'A'
    a = 'up_and_out'
    b = 'down_and_in'
    g = conns.test_time
    for tp in [u, d]:
        part = cm_partconnect.Parts()
        part.hpn = tp
        part.hpn_rev = r
        part.hptype = conns.test_hptype
        part.manufacture_number = conns.test_mfg
        part.start_gpstime = conns.test_time
        conns.test_session.add(part)
    conns.test_session.commit()
    data = [[u, r, d, r, a, b, g, 'upstream_part', u],
            [u, r, d, r, a, b, g, 'up_part_rev', r],
            [u, r, d, r, a, b, g, 'downstream_part', d],
            [u, r, d, r, a, b, g, 'down_part_rev', r],
            [u, r, d, r, a, b, g, 'upstream_output_port', a],
            [u, r, d, r, a, b, g, 'downstream_input_port', b],
            [u, r, d, r, a, b, g, 'start_gpstime', g]]
    cm_partconnect.update_connection(conns.test_session, data,
                                     add_new_connection=True)
    located = conns.cm_handle.get_part_connection_dossier(
        [u], r, a, 'now', True)
    prkey = list(located.keys())[0]
    assert str(located[prkey]).startswith('NEW_TEST_PART_UP:A')
    ckey = located[prkey].keys_down[0]
    assert located[prkey].down[ckey].upstream_part == u
    with captured_output() as (out, err):
        conns.cm_handle.show_connections(located)
    assert ('new_test_part_up:A | up_and_out  | down_and_in | '
            'new_test_part_down:A' in out.getvalue().strip())
    with captured_output() as (out, err):
        conns.cm_handle.show_connections(located, verbosity=1)
    assert ('new_test_part_up:A | new_test_part_down:A'
            in out.getvalue().strip())
    with captured_output() as (out, err):
        conns.cm_handle.show_connections(located, verbosity=2)
    assert ('new_test_part_up:A | up_and_out  | down_and_in | '
            'new_test_part_down:A' in out.getvalue().strip())


def test_get_null_connection():
    nc = cm_partconnect.get_null_connection()
    assert nc.upstream_part == cm_partconnect.no_connection_designator


def test_get_dossier(conns):
    x = conns.cm_handle.get_part_connection_dossier(
        'test_part1', 'active', 'all', at_date='now', exact_match=True)
    y = list(x.keys())[0]
    assert y == 'test_part1:Q'
    with captured_output() as (out, err):
        conns.cm_handle.show_connections(x)
    assert ('test_part1:Q | up_and_out  | down_and_in | test_part2:Q'
            in out.getvalue().strip())
    x = conns.cm_handle.get_part_connection_dossier(
        'test_part2', 'active', 'all', at_date='now', exact_match=True)
    y = list(x.keys())[0]
    assert y == 'test_part2:Q'
    with captured_output() as (out, err):
        conns.cm_handle.show_connections(x)
    assert ('test_part1:Q | up_and_out  | down_and_in | test_part2:Q'
            in out.getvalue().strip())
    old_time = Time('2014-08-01 01:00:00', scale='utc')
    x = conns.cm_handle.get_part_connection_dossier(
        'test_part1', 'active', 'all', at_date=old_time, exact_match=True)
    assert len(x) == 0
    x = conns.cm_handle.get_part_connection_dossier(
        'test_part2', 'active', 'all', at_date=old_time, exact_match=True)
    assert len(x) == 0
    z = {}
    z['tst'] = cm_handling.PartConnectionDossierEntry(
        'test_part1', 'active', 'all')
    with captured_output() as (out, err):
        conns.cm_handle.show_connections(z)
    assert 'Q' not in out.getvalue().strip()


def test_get_specific_connection(conns):
    c = cm_partconnect.Connections()
    c.upstream_part = conns.test_hpn[0]
    c.up_part_rev = conns.test_rev
    c.downstream_part = conns.test_hpn[1]
    c.down_part_rev = conns.test_rev
    c.upstream_output_port = 'up_and_out'
    c.downstream_input_port = 'down_and_in'
    sc = conns.cm_handle.get_specific_connection(c)
    assert len(sc) == 1

    c.up_part_rev = 'S'
    sc = conns.cm_handle.get_specific_connection(c)
    assert len(sc) == 0

    c.up_part_rev = conns.test_rev
    c.down_part_rev = 'S'
    sc = conns.cm_handle.get_specific_connection(c)
    assert len(sc) == 0

    c.down_part_rev = conns.test_rev
    c.upstream_output_port = 'guk'
    sc = conns.cm_handle.get_specific_connection(c)
    assert len(sc) == 0

    c.upstream_output_port = 'up_and_out'
    c.downstream_input_port = 'guk'
    sc = conns.cm_handle.get_specific_connection(c)
    assert len(sc) == 0

    at_date = Time('2017-05-01 01:00:00', scale='utc')
    sc = conns.cm_handle.get_specific_connection(c, at_date)
    assert len(sc) == 0


def test_check_for_overlap():
    x = cm_health.check_for_overlap([1, 2], [3, 4])
    assert not x
    x = cm_health.check_for_overlap([3, 4], [1, 2])
    assert not x
    x = cm_health.check_for_overlap([1, 10], [2, 8])
    assert x
    x = cm_health.check_for_overlap([2, 8], [1, 10])
    assert x
    x = cm_health.check_for_overlap([1, 5], [3, 8])
    assert x
    x = cm_health.check_for_overlap([3, 8], [1, 5])
    assert x
    x = cm_health.check_for_overlap([1, 8], [8, 10])
    assert not x
    x = cm_health.check_for_overlap([8, 10], [1, 8])
    assert not x


def test_physical_connections(conns):
    x = conns.cm_handle.get_physical_connections()
    y = list(x.keys())
    assert 'PAM75999:A' in y
    x = conns.cm_handle.get_physical_connections('2016/01/01')
    assert not len(x)


def test_duplicate_connections(conns):
    connection = cm_partconnect.Connections()
    healthy = cm_health.Connections(conns.test_session)
    # Specific connections
    duplicates = healthy.check_for_existing_connection(hpn=['a'], side='up', at_date=conns.query_time)
    assert duplicates
    duplicates = healthy.check_for_existing_connection(hpn=conns.test_hpn[0], rev=conns.test_rev, port='up_and_out', at_date=conns.query_time)
    assert duplicates
    duplicates = healthy.check_for_existing_connection(hpn=conns.test_hpn[0], rev=conns.test_rev, port='up_and_out', side='dn', at_date='<')
    assert not duplicates

    # Duplicated connections
    duplicates = healthy.check_for_duplicate_connections()
    assert len(duplicates) == 2
    # Add test duplicate connection
    connection.upstream_part = conns.test_hpn[0]
    connection.up_part_rev = conns.test_rev
    connection.downstream_part = conns.test_hpn[1]
    connection.down_part_rev = conns.test_rev
    connection.upstream_output_port = 'up_and_out'
    connection.downstream_input_port = 'down_and_in'
    connection.start_gpstime = conns.test_time + 10
    conns.test_session.add(connection)
    conns.test_session.commit()
    healthy.conndict = None
    duplicates = healthy.check_for_duplicate_connections()
    assert len(duplicates) == 2
    conn1 = cm_partconnect.Connections()
    conn1.upstream_part = conns.test_hpn[0]
    conn1.up_part_rev = conns.test_rev
    conn1.downstream_part = conns.test_hpn[1]
    conn1.down_part_rev = conns.test_rev
    conn1.upstream_output_port = 'terminal'
    conn1.downstream_input_port = 'n'
    conn1.start_gpstime = conns.test_time + 100
    conns.test_session.add(conn1)
    conn2 = cm_partconnect.Connections()
    conn2.upstream_part = conns.test_hpn[0]
    conn2.up_part_rev = conns.test_rev
    conn2.downstream_part = conns.test_hpn[1]
    conn2.down_part_rev = conns.test_rev
    conn2.upstream_output_port = 'terminal'
    conn2.downstream_input_port = 'e'
    conn2.start_gpstime = conns.test_time + 100
    conns.test_session.add(conn2)
    conns.test_session.commit()
    healthy.conndict = None
    duplicates = healthy.check_for_duplicate_connections()
    assert len(duplicates) == 2
