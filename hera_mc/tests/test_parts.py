# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.connections`."""

import pytest
import numpy as np
from astropy.time import Time
from collections import OrderedDict

from hera_mc import (
    cm_partconnect,
    cm_utils,
    cm_handling,
    cm_revisions,
    cm_dossier,
    cm_active,
)


@pytest.fixture(scope="function")
def parts(mcsession):
    """Fixture for commonly used part data."""
    test_session = mcsession
    test_part = "test_part"
    test_rev = "Q"
    test_hptype = "antenna"
    start_time = Time("2019-07-01 01:00:00", scale="utc")
    cm_handle = cm_handling.Handling(test_session)

    # Add a test part
    part = cm_partconnect.Parts()
    part.hpn = test_part
    part.hpn_rev = test_rev
    part.hptype = test_hptype
    part.manufacture_number = "XYZ"
    part.start_gpstime = start_time.gps
    test_session.add(part)
    test_session.commit()

    class DataHolder(object):
        def __init__(
            self, test_session, test_part, test_rev, test_hptype, start_time, cm_handle
        ):
            self.test_session = test_session
            self.test_part = test_part
            self.test_rev = test_rev
            self.test_hptype = test_hptype
            self.start_time = start_time
            self.cm_handle = cm_handle

    parts = DataHolder(
        test_session, test_part, test_rev, test_hptype, start_time, cm_handle
    )

    # yields the data we need but will continue to the del call after tests
    yield parts

    # some post-test object cleanup
    del parts

    return


def test_update_new(parts):
    ntp = "new_test_part"
    data = [
        [ntp, "X", "hpn", ntp],
        [ntp, "X", "hpn_rev", "X"],
        [ntp, "X", "hptype", "antenna"],
        [ntp, "X", "start_gpstime", 1172530000],
    ]
    cm_partconnect.update_part(parts.test_session, data)
    located = parts.cm_handle.get_dossier(
        hpn=[ntp], rev=["X"], at_date="now", exact_match=True
    )
    prkey = list(located.keys())[0]
    assert prkey == "NEW_TEST_PART:X"


def test_find_part_type(parts):
    pt = parts.cm_handle.get_part_type_for(parts.test_part)
    assert pt == parts.test_hptype


def test_various_handling_utils(parts, capsys):
    parts.cm_handle._get_allowed_ports(["a"])
    assert parts.cm_handle.allowed_ports[0] == "A"
    parts.cm_handle._get_allowed_ports("a,b")
    assert parts.cm_handle.allowed_ports[0] == "A"
    parts.cm_handle._get_allowed_ports({"a": "A"})
    assert parts.cm_handle.allowed_ports is None


def test_apriori(mcsession):
    active = cm_active.ActiveData(mcsession)
    active.load_apriori()
    assert active.apriori["HH700:A"].status == "not_connected"


def test_duplicate(mcsession):
    active = cm_active.ActiveData(mcsession)
    active.pytest_param = "up"
    pytest.raises(ValueError, active.load_connections)
    active.pytest_param = "down"
    pytest.raises(ValueError, active.load_connections)


def test_rosetta(mcsession, capsys):
    active = cm_active.ActiveData(mcsession)
    at_date = Time("2020-07-01 01:00:00", scale="utc")
    active.load_parts(at_date)
    active.load_rosetta(at_date)
    assert active.rosetta["SNPC000700"].syspn == "heraNode700Snap700"
    print(active.rosetta["SNPC000700"])
    captured = capsys.readouterr()
    assert captured.out.strip().startswith("<SNPC000700")
    cm_partconnect.update_part_rosetta(
        "SNPC000702", "heraNode700Snap1", at_date, session=mcsession
    )
    active.load_rosetta(at_date)
    assert active.rosetta["SNPC000702"].syspn == "heraNode700Snap2"
    stop_at = Time("2020-08-01 01:00:00", scale="utc")
    cm_partconnect.update_part_rosetta(
        "SNPC000771", "heraNode771Snap2", at_date, date2=stop_at, session=mcsession
    )
    active.load_rosetta(Time("2020-07-15 01:00:00", scale="utc"))
    assert int(active.rosetta["SNPC000771"].start_gpstime) == 1277600418
    cm_partconnect.update_part_rosetta(
        "SNPC000709", "heraNode700Snap709", stop_at, session=mcsession
    )
    assert int(active.rosetta["SNPC000709"].stop_gpstime) == 1280278818
    # Add a test part to fail on update part

    rose = cm_partconnect.PartRosetta()
    rose.hpn = "SNPC000701"
    rose.syspn = "heraNode0Snap701"
    rose.start_gpstime = Time("2019-07-15 01:00:00", scale="utc").gps
    mcsession.add(rose)
    mcsession.commit()
    with pytest.raises(
        ValueError,
        match="Multiple rosetta relationships active" " for heraNode0Snap701",
    ):
        cm_partconnect.update_part_rosetta(
            "SNPC000701", "heraNode0Snap701", stop_at, None, session=mcsession
        )
    # Add a test part to fail on load active
    rose = cm_partconnect.PartRosetta()
    rose.hpn = "SNPC000701"
    rose.syspn = "heraNode700Snap700"
    rose.start_gpstime = Time("2019-07-01 01:00:00", scale="utc").gps
    mcsession.add(rose)
    mcsession.commit()
    pytest.raises(ValueError, active.load_rosetta)
    rose2 = cm_partconnect.PartRosetta()
    rose2.hpn = "SNPC000712"
    rose2.syspn = "heraNode712Snap712"
    rose2.start_gpstime = Time("2019-07-01 01:00:00", scale="utc").gps
    rose2.stop_gpstime = Time("2020-08-01 01:00:00", scale="utc").gps
    mcsession.add(rose2)
    mcsession.commit()
    with pytest.warns(
        UserWarning,
        match="No action taken.  <SNPC000712  -  heraNode712Snap712 ::"
        " 1245978018 - 1280278818> already has a valid stop date",
    ):
        cm_partconnect.update_part_rosetta(
            "SNPC000712", "heraNode712Snap712", "2020/01/02", session=mcsession
        )


def test_update_part(parts, capsys):
    data = [[parts.test_part, parts.test_rev, "not_an_attrib", "Z"]]
    cm_partconnect.update_part(parts.test_session, data)
    captured = capsys.readouterr()
    assert "does not exist as a field" in captured.out.strip()
    data = [[parts.test_part, parts.test_rev, "hpn_rev", "Z"]]
    cm_partconnect.update_part(parts.test_session, data)
    dtq = Time("2019-09-01 01:00:00", scale="utc")
    located = parts.cm_handle.get_dossier(
        hpn=[parts.test_part], rev=None, at_date=dtq, exact_match=False
    )
    assert len(list(located.keys())) == 1
    assert located[list(located.keys())[0]].part.hpn_rev == "Z"


def test_format_and_check_update_part_request():
    request = "test_part:Q:hpn_rev:A"
    x = cm_partconnect.format_and_check_update_part_request(request)
    assert list(x.keys())[0] == "test_part:Q"
    pytest.raises(
        ValueError,
        cm_partconnect.format_and_check_update_part_request,
        "test_part:hpn_rev:A",
    )
    request = "test_part:Q:hpn_rev:A,test_part:mfg:xxx,nope,another:one"
    x = cm_partconnect.format_and_check_update_part_request(request)
    assert x["test_part:Q"][2][3] == "one"


def test_format_check_update_connection_request(capsys):
    request = "1,2,3"
    x = cm_partconnect.format_check_update_connection_request(request)
    captured = capsys.readouterr()
    assert captured.out.strip().startswith("Invalid")
    request = "1:2:3:4:5:6:7"
    x = cm_partconnect.format_check_update_connection_request(request)
    assert x["1:2:3:4"][0][1] == "LAST"


def test_show_dossier(parts, capsys):
    pytest.importorskip("tabulate")
    cm_partconnect.add_part_info(
        parts.test_session,
        parts.test_part,
        parts.test_rev,
        "Testing",
        parts.start_time,
        reference="reference",
    )
    located = parts.cm_handle.get_dossier(
        hpn=[parts.test_part], rev=parts.test_rev, at_date="now", exact_match=True
    )
    captured = parts.cm_handle.show_dossier(located, ["hpn", "start_gpstime"])
    assert "TEST_PART" in captured
    captured = parts.cm_handle.show_dossier({}, ["hpn"])
    assert "Part not found" in captured
    located = parts.cm_handle.get_dossier(
        hpn=["A700"], rev=["H"], at_date="now", exact_match=True
    )
    captured = parts.cm_handle.show_dossier(located, ["comment", "posting_gpstime"])
    assert "Comment 2" in captured
    located = parts.cm_handle.get_dossier(
        hpn=["HH700"], rev=["A"], at_date="now", exact_match=True
    )
    captured = parts.cm_handle.show_dossier(located, ["geo"])
    assert "540901.6E, 6601070.7N, 1052.6m" in captured


def test_various_dossier(capsys):
    d = cm_dossier.PartEntry("A", "B")
    d.part = "test"
    print(d)
    captured = capsys.readouterr()
    assert captured.out.strip() == "A:B -- test"
    d.connections.down = {"B": None}
    d.connections.up = {"A": None}
    d.input_ports = ["b"]
    d.output_ports = ["a"]
    x = d.table_row(["up.", "down."], "A")
    assert len(x) == 0


def test_part_info(parts, mcsession, capsys):
    cm_partconnect.add_part_info(
        parts.test_session,
        parts.test_part,
        parts.test_rev,
        "Testing",
        Time("2017-07-01 01:00:00"),
        reference="reference",
    )
    located = parts.cm_handle.get_dossier(
        hpn=[parts.test_part], rev=parts.test_rev, at_date="now", exact_match=True
    )
    assert "Testing" in located[list(located.keys())[0]].part_info.comment
    test_info = cm_partconnect.PartInfo()
    test_info.info(hpn="A", hpn_rev="B", posting_gpstime=1172530000, comment="Hey Hey!")
    print(test_info)
    captured = capsys.readouterr()
    assert "heraPartNumber id = A:B" in captured.out.strip()
    test_info.gps2Time()
    assert int(test_info.posting_date.gps) == 1172530000
    with pytest.warns(UserWarning, match="No action taken. Comment is empty."):
        cm_partconnect.add_part_info(mcsession, "HH700", "A", "  ", "2020/01/02")


def test_equality():
    p1 = cm_partconnect.Parts()
    p1.hpn = "hpn1"
    p1.hpn_rev = "hpn1_rev"
    p2 = cm_partconnect.Parts()
    p2.hpn = "hpn2"
    p2.hpn_rev = "hpn2_rev"
    assert p1 == p1
    assert p1 != p2


def test_add_new_parts(parts, capsys):
    a_time = Time("2017-07-01 01:00:00", scale="utc")
    data = [[parts.test_part, parts.test_rev, parts.test_hptype, "xxx"]]
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

    data = [["part_X", "X", "station", "mfg_X"]]
    p = cm_partconnect.Parts()
    p.part(test_attribute="test")
    assert p.test_attribute == "test"
    cm_partconnect.add_new_parts(parts.test_session, data, a_time, True)
    located = parts.cm_handle.get_dossier(
        hpn=["part_X"], rev=["X"], at_date=a_time, exact_match=True
    )
    assert len(list(located.keys())) == 1
    assert located[list(located.keys())[0]].part.hpn == "part_X"


def test_stop_parts(parts, capsys):
    hpnr = [["test_part", "Q"]]
    at_date = Time("2017-12-01 01:00:00", scale="utc")
    cm_partconnect.stop_existing_parts(
        parts.test_session, hpnr, at_date, allow_override=False
    )
    p = parts.cm_handle.get_part_from_hpnrev(hpnr[0][0], hpnr[0][1])
    assert p.stop_gpstime == 1196125218
    cm_partconnect.stop_existing_parts(
        parts.test_session, hpnr, at_date, allow_override=False
    )
    captured = capsys.readouterr()
    assert "Override not enabled.  No action." in captured.out.strip()
    cm_partconnect.stop_existing_parts(
        parts.test_session, hpnr, at_date, allow_override=True
    )
    captured = capsys.readouterr()
    assert "Override enabled.   New value 1196125218" in captured.out.strip()
    hpnr = [["no_part", "Q"]]
    cm_partconnect.stop_existing_parts(
        parts.test_session, hpnr, at_date, allow_override=False
    )
    captured = capsys.readouterr()
    assert "no_part:Q is not found, so can't stop it." in captured.out.strip()


def test_cm_version(parts):
    parts.cm_handle.add_cm_version(
        Time("2019-09-20 01:00:00", scale="utc"), "Test-git-hash"
    )
    gh = parts.cm_handle.get_cm_version(Time("2019-09-20 01:00:00", scale="utc"))
    assert gh == "Test-git-hash"


def test_active_revisions(parts):
    active = cm_active.ActiveData(parts.test_session)
    active.load_parts()
    revs = active.revs("HH")
    assert revs[0].hpn == "HH"
    hndl = cm_handling.Handling(parts.test_session)
    with pytest.raises(ValueError) as ml:
        hndl.get_dossier("HH701", at_date="2019/12/01", active=active)
    assert str(ml.value).startswith("Supplied")
    active.at_date = Time("2019-12-10")
    xxx = hndl.get_dossier("HH701", at_date=None, active=active)
    yyy = list(xxx.keys())[0]
    assert yyy == "HH701:A"


def test_active_revisions_mixed_start_time(parts):
    test_part = "test_part2"
    test_rev = "Q"
    test_hptype = "antenna"
    start_time = Time("2019-07-01 00:30:00", scale="utc")

    # Add a test part
    part = cm_partconnect.Parts()
    part.hpn = test_part
    part.hpn_rev = test_rev
    part.hptype = test_hptype
    part.manufacture_number = "XYZ"
    part.start_gpstime = start_time.gps
    parts.test_session.add(part)
    parts.test_session.commit()

    active = cm_active.ActiveData(parts.test_session)
    active.load_parts()
    key_order = np.argsort([active.parts[k].start_gpstime for k in active.parts.keys()])
    key_order = [list(active.parts.keys())[k] for k in key_order]
    # print(active.parts[key_order[-1]])
    # print(active.parts[key_order[-2]])
    key_order[-1], key_order[-2] = key_order[-2], key_order[-1]
    active.parts = OrderedDict({key: active.parts[key] for key in key_order})
    # vals = list(active.parts.values())
    # print(vals[0])
    # print(vals[1])
    revs = active.revs("TEST_PART")

    assert revs[0].hpn == "TEST_PART"
    assert revs[0].number == 2
    assert revs[0].started == start_time.gps


@pytest.mark.filterwarnings("ignore:ERFA function")
def test_active_revisions_mixed_stop_time(parts):
    test_part = "new_part2"
    test_rev = "Q"
    test_hptype = "antenna"
    start_time = Time("2019-07-01 00:30:00", scale="utc")
    stop_time = Time("2050-07-01 01:45:00", scale="utc")

    # Add a test part
    part = cm_partconnect.Parts()
    part.hpn = test_part
    part.hpn_rev = test_rev
    part.hptype = test_hptype
    part.manufacture_number = "XYZ"
    part.start_gpstime = start_time.gps
    part.stop_gpstime = stop_time.gps
    parts.test_session.add(part)
    parts.test_session.commit()
    #
    test_part = "new_part3"
    test_rev = "Q"
    test_hptype = "antenna"
    start_time = Time("2019-07-01 00:31:00", scale="utc")
    stop_time = Time("2050-07-01 02:45:00", scale="utc")

    # Add a test part
    part1 = cm_partconnect.Parts()
    part1.hpn = test_part
    part1.hpn_rev = test_rev
    part1.hptype = test_hptype
    part1.manufacture_number = "XYZ"
    part1.start_gpstime = start_time.gps
    part1.stop_gpstime = stop_time.gps
    parts.test_session.add(part1)
    parts.test_session.commit()

    active = cm_active.ActiveData(parts.test_session)

    active.load_parts()
    key_order = np.argsort([active.parts[k].start_gpstime for k in active.parts.keys()])

    key_order = [list(active.parts.keys())[k] for k in key_order]
    active.parts = OrderedDict({key: active.parts[key] for key in key_order})

    vals = list(active.parts.values())
    assert part1 in vals

    revs = active.revs("NEW_PART")

    assert revs[0].hpn == "NEW_PART"
    assert revs[0].number == 2
    assert revs[0].ended == stop_time.gps


@pytest.mark.filterwarnings("ignore:ERFA function")
def test_active_revisions_mixed_stop_one_none(parts):
    test_part = "new_part2"
    test_rev = "Q"
    test_hptype = "antenna"
    start_time = Time("2019-07-01 00:30:00", scale="utc")
    stop_time = Time("2050-07-01 01:45:00", scale="utc")

    # Add a test part
    part = cm_partconnect.Parts()
    part.hpn = test_part
    part.hpn_rev = test_rev
    part.hptype = test_hptype
    part.manufacture_number = "XYZ"
    part.start_gpstime = start_time.gps
    part.stop_gpstime = stop_time.gps
    parts.test_session.add(part)
    parts.test_session.commit()
    #
    test_part = "new_part3"
    test_rev = "Q"
    test_hptype = "antenna"
    start_time = Time("2019-07-01 00:31:00", scale="utc")

    # Add a test part
    part1 = cm_partconnect.Parts()
    part1.hpn = test_part
    part1.hpn_rev = test_rev
    part1.hptype = test_hptype
    part1.manufacture_number = "XYZ"
    part1.start_gpstime = start_time.gps
    parts.test_session.add(part1)
    parts.test_session.commit()

    active = cm_active.ActiveData(parts.test_session)

    active.load_parts()
    key_order = np.argsort([active.parts[k].start_gpstime for k in active.parts.keys()])

    key_order = [list(active.parts.keys())[k] for k in key_order]
    active.parts = OrderedDict({key: active.parts[key] for key in key_order})

    vals = list(active.parts.values())
    assert part1 in vals

    revs = active.revs("NEW_PART")

    assert revs[0].hpn == "NEW_PART"
    assert revs[0].number == 2
    assert revs[0].ended is None


def test_get_revisions_of_type(parts, capsys):
    pytest.importorskip("tabulate")
    at_date = None
    rev_types = ["LAST", "ACTIVE", "ALL", "A"]
    for rq in rev_types:
        revision = cm_revisions.get_revisions_of_type(
            "HH700", rq, at_date, session=parts.test_session
        )
        assert revision[0].rev == "A"
        revision = cm_revisions.get_revisions_of_type(
            None, rq, at_date, session=parts.test_session
        )
        assert len(revision) == 0
    revision = cm_revisions.get_revisions_of_type(
        parts.test_part, "LAST", "now", session=parts.test_session
    )
    assert revision[0].rev == "Q"
    revision = cm_revisions.get_revisions_of_type(
        None, "ACTIVE", "now", session=parts.test_session
    )
    captured = cm_revisions.show_revisions(revision)
    assert "No revisions found" in captured
    revision = cm_revisions.get_revisions_of_type(
        "HH700", "ACTIVE", "now", session=parts.test_session
    )
    captured = cm_revisions.show_revisions(revision)
    assert "HH700" in captured
    assert revision[0].hpn == "HH700"
    captured = cm_revisions.show_revisions(revision, "present")
    assert "HH700" in captured
    captured = cm_revisions.show_revisions(revision, "HPN,Revision")
    assert "HH700" in captured
    with pytest.raises(ValueError) as ml:
        cm_revisions.get_revisions_of_type("HH700", "FULL")
    assert str(ml.value).startswith("FULL")
    rev = cm_revisions.get_last_revision("TEST", parts.test_session)
    assert rev[0].hpn == "TEST"


def test_datetime(parts):
    dt = cm_utils.get_astropytime("2017-01-01", 0.0)
    gps_direct = int(Time("2017-01-01 00:00:00", scale="utc").gps)
    assert int(dt.gps) == gps_direct
