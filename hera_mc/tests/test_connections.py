# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`."""

from __future__ import absolute_import, division, print_function

import pytest
from astropy.time import Time

from .. import cm_partconnect, cm_handling, cm_dossier


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


def test_update_new(conns, capsys):
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
    located = conns.cm_handle.get_dossier([u], r, 'physical', 'now', exact_match=True)
    prkey = list(located.keys())[0]
    assert prkey == 'NEW_TEST_PART_UP:A'
    ckey = located[prkey].output_ports
    assert a in ckey

    captured = conns.cm_handle.show_dossier(located, ['hpn'])
    assert 'NEW_TEST_PART_UP' in captured


def test_get_null_connection():
    nc = cm_partconnect.get_null_connection()
    assert nc.upstream_part == cm_partconnect.no_connection_designator


def test_stop_existing_connections_to_part(conns, capsys):
    cmh = cm_handling.Handling()
    conn_list = [['HH00', 'A', 'ground']]
    stop_Time = Time('2019-10-27T00:53:53.530')
    cm_partconnect.stop_existing_connections_to_part(conns.test_session, cmh, conn_list, stop_Time)
    captured = capsys.readouterr()
    assert captured.out.strip().startswith("There are no connections to stop")
    conn_list = [['HH700', 'A', 'ground']]


def test_various_connection(capsys):
    c = cm_partconnect.Connections()
    print(c)
    captured = capsys.readouterr()
    assert captured.out.strip().startswith('<None')
    c.stop_gpstime = 1256172851.53
    c.gps2Time()
    assert c.stop_date.isot == '2019-10-27T00:53:53.530'


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
