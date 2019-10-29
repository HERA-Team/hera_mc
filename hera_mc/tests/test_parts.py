# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`."""

from __future__ import absolute_import, division, print_function

import pytest
from astropy.time import Time

from hera_mc import cm_partconnect, cm_utils, cm_handling, cm_revisions


@pytest.fixture(scope='function')
def parts(mcsession):
    """Fixture for commonly used part data."""
    test_session = mcsession
    test_part = 'test_part'
    test_rev = 'Q'
    test_hptype = 'antenna'
    start_time = Time('2019-07-01 01:00:00', scale='utc')
    cm_handle = cm_handling.Handling(test_session)

    # Add a test part
    part = cm_partconnect.Parts()
    part.hpn = test_part
    part.hpn_rev = test_rev
    part.hptype = test_hptype
    part.manufacture_number = 'XYZ'
    part.start_gpstime = start_time.gps
    test_session.add(part)
    test_session.commit()

    class DataHolder(object):
        def __init__(self, test_session, test_part, test_rev, test_hptype,
                     start_time, cm_handle):
            self.test_session = test_session
            self.test_part = test_part
            self.test_rev = test_rev
            self.test_hptype = test_hptype
            self.start_time = start_time
            self.cm_handle = cm_handle

    parts = DataHolder(test_session, test_part, test_rev, test_hptype,
                       start_time, cm_handle)

    # yields the data we need but will continue to the del call after tests
    yield parts

    # some post-test object cleanup
    del(parts)

    return


def test_update_new(parts):
    ntp = 'new_test_part'
    data = [[ntp, 'X', 'hpn', ntp],
            [ntp, 'X', 'hpn_rev', 'X'],
            [ntp, 'X', 'hptype', 'antenna'],
            [ntp, 'X', 'start_gpstime', 1172530000]]
    cm_partconnect.update_part(parts.test_session, data)
    located = parts.cm_handle.get_dossier(hpn=[ntp], rev=['X'], at_date='now', exact_match=True)
    prkey = list(located.keys())[0]
    assert prkey == 'NEW_TEST_PART:X'


def test_find_part_type(parts):
    pt = parts.cm_handle.get_part_type_for(parts.test_part)
    assert pt == parts.test_hptype


def test_update_part(parts, capsys):
    data = [[parts.test_part, parts.test_rev, 'not_an_attrib', 'Z']]
    cm_partconnect.update_part(parts.test_session, data)
    captured = capsys.readouterr()
    assert 'does not exist as a field' in captured.out.strip()
    data = [[parts.test_part, parts.test_rev, 'hpn_rev', 'Z']]
    cm_partconnect.update_part(parts.test_session, data)
    dtq = Time('2019-09-01 01:00:00', scale='utc')
    located = parts.cm_handle.get_dossier(
        hpn=[parts.test_part], rev=None, at_date=dtq, exact_match=True)
    assert len(list(located.keys())) == 1
    assert located[list(located.keys())[0]].part.hpn_rev == 'Z'


def test_format_and_check_update_part_request(parts):
    request = 'test_part:Q:hpn_rev:A'
    x = cm_partconnect.format_and_check_update_part_request(request)
    assert list(x.keys())[0] == 'test_part:Q'
    pytest.raises(ValueError,
                  cm_partconnect.format_and_check_update_part_request,
                  'test_part:hpn_rev:A')
    request = 'test_part:Q:hpn_rev:A,test_part:mfg:xxx,nope,another:one'
    x = cm_partconnect.format_and_check_update_part_request(request)
    assert x['test_part:Q'][2][3] == 'one'


def test_show_dossier(parts, capsys):
    cm_partconnect.add_part_info(
        parts.test_session, parts.test_part, parts.test_rev, parts.start_time,
        'Testing', 'library_file')
    located = parts.cm_handle.get_dossier(hpn=[parts.test_part], rev=parts.test_rev,
                                          at_date='now', exact_match=True)
    captured = parts.cm_handle.show_dossier(located, ['hpn'])
    assert 'TEST_PART' in captured
    captured = parts.cm_handle.show_dossier({}, ['hpn'])
    assert 'Part not found' in captured
    located = parts.cm_handle.get_dossier(hpn=['A700'], rev=['H'], at_date='now', exact_match=True)
    captured = parts.cm_handle.show_dossier(located, ['comment'])
    assert 'Comment 2' in captured
    located = parts.cm_handle.get_dossier(
        hpn=['HH700'], rev=['A'], at_date='now', exact_match=True)
    captured = parts.cm_handle.show_dossier(located, ['geo'])
    assert '540901.6E, 6601070.7N, 1052.6m' in captured


def test_part_info(parts, capsys):
    cm_partconnect.add_part_info(
        parts.test_session, parts.test_part, parts.test_rev,
        Time('2017-07-01 01:00:00'), 'Testing', 'library_file')
    located = parts.cm_handle.get_dossier(hpn=[parts.test_part], rev=parts.test_rev,
                                          at_date='now', exact_match=True)
    assert 'Testing' in located[list(located.keys())[0]].part_info.comment
    test_info = cm_partconnect.PartInfo()
    test_info.info(hpn='A', hpn_rev='B', posting_gpstime=1172530000,
                   comment='Hey Hey!')
    print(test_info)
    captured = capsys.readouterr()
    assert 'heraPartNumber id = A:B' in captured.out.strip()
    test_info.gps2Time()
    assert int(test_info.posting_date.gps) == 1172530000


def test_add_new_parts(parts, capsys):
    a_time = Time('2017-07-01 01:00:00', scale='utc')
    data = [[parts.test_part, parts.test_rev, parts.test_hptype, 'xxx']]
    cm_partconnect.add_new_parts(parts.test_session, data, a_time, True)
    captured = capsys.readouterr()
    assert "No action." in captured.out.strip()

    cm_partconnect.stop_existing_parts(parts.test_session, data, a_time, False)
    cm_partconnect.add_new_parts(parts.test_session, data, a_time, False)
    captured = capsys.readouterr()
    assert "No action." in captured.out.strip()
    cm_partconnect.add_new_parts(parts.test_session, data, a_time, True)
    captured = capsys.readouterr()
    assert "Restarting part test_part:q" in captured.out.strip()

    data = [['part_X', 'X', 'station', 'mfg_X']]
    p = cm_partconnect.Parts()
    p.part(test_attribute='test')
    assert p.test_attribute == 'test'
    cm_partconnect.add_new_parts(parts.test_session, data, a_time, True)
    located = parts.cm_handle.get_dossier(
        hpn=['part_X'], rev=['X'], at_date=a_time, exact_match=True)
    assert len(list(located.keys())) == 1
    assert located[list(located.keys())[0]].part.hpn == 'part_X'


def test_stop_parts(parts, capsys):
    hpnr = [['test_part', 'Q']]
    at_date = Time('2017-12-01 01:00:00', scale='utc')
    cm_partconnect.stop_existing_parts(parts.test_session, hpnr, at_date,
                                       allow_override=False)
    p = parts.cm_handle.get_part_from_hpnrev(hpnr[0][0], hpnr[0][1])
    assert p.stop_gpstime == 1196125218
    cm_partconnect.stop_existing_parts(parts.test_session, hpnr, at_date,
                                       allow_override=False)
    captured = capsys.readouterr()
    assert "Override not enabled.  No action." in captured.out.strip()
    cm_partconnect.stop_existing_parts(parts.test_session, hpnr, at_date,
                                       allow_override=True)
    captured = capsys.readouterr()
    assert "Override enabled.   New value 1196125218" in captured.out.strip()
    hpnr = [['no_part', 'Q']]
    cm_partconnect.stop_existing_parts(parts.test_session, hpnr, at_date,
                                       allow_override=False)
    captured = capsys.readouterr()
    assert "no_part:Q is not found, so can't stop it." in captured.out.strip()


def test_cm_version(parts):
    parts.cm_handle.add_cm_version(Time('2019-09-20 01:00:00', scale='utc'),
                                   'Test-git-hash')
    gh = parts.cm_handle.get_cm_version(Time('2019-09-20 01:00:00',
                                             scale='utc'))
    assert gh == 'Test-git-hash'


def test_get_revisions_of_type(parts, capsys):
    at_date = None
    rev_types = ['LAST', 'ACTIVE', 'ALL', 'A']
    for rq in rev_types:
        revision = cm_revisions.get_revisions_of_type(
            'HH700', rq, at_date, parts.test_session)
        assert revision[0].rev == 'A'
        revision = cm_revisions.get_revisions_of_type(
            None, rq, at_date, parts.test_session)
        assert len(revision) == 0
    revision = cm_revisions.get_revisions_of_type(
        parts.test_part, 'LAST', 'now', parts.test_session)
    assert revision[0].rev == 'Q'
    revision = cm_revisions.get_revisions_of_type(
        None, 'ACTIVE', 'now', parts.test_session)
    cm_revisions.show_revisions(revision)
    captured = capsys.readouterr()
    assert 'No revisions found' in captured.out.strip()
    revision = cm_revisions.get_revisions_of_type(
        'HH700', 'ACTIVE', 'now', parts.test_session)
    cm_revisions.show_revisions(revision)
    captured = capsys.readouterr()
    assert '1230372018' in captured.out.strip()
    assert revision[0].hpn == 'HH700'


def test_datetime(parts):
    dt = cm_utils.get_astropytime('2017-01-01', 0.0)
    gps_direct = int(Time('2017-01-01 00:00:00', scale='utc').gps)
    assert int(dt.gps) == gps_direct
