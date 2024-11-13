# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.geo_location and geo_handling`."""
import pytest
from astropy.time import Time

from .. import cm_active, cm_partconnect, geo_handling, geo_location, geo_sysdef

# Sometimes a connection is closed, which is handled and doesn't produce an error
# or even a warning under normal testing. But for the warnings test where we
# pass `-W error`, the warning causes an error so we filter it out here.
pytestmark = pytest.mark.filterwarnings("ignore:connection:ResourceWarning:psycopg")


@pytest.fixture(scope="function")
def geo_handle(mcsession):
    return geo_handling.Handling(mcsession, testing=True)


def test_cofa(mcsession, geo_handle):
    geo_handle.get_station_types()
    station_types = [stn_type.lower() for stn_type in geo_handle.station_types.keys()]
    assert "cofa" in station_types

    cofa = geo_handle.cofa()[0]

    # test that function works the same as method
    cofa_func = geo_handling.cofa(testing=True)[0]
    assert cofa.isclose(cofa_func)


def test_load_geo(mcsession):
    active = cm_active.ActiveData(mcsession)
    active.load_geo()
    assert "COFA_FAKE" in active.geo.keys()


def test_geo_sysdef():
    n = geo_sysdef.read_nodes()
    assert n[3]["ants"][1] == 37
    a = geo_sysdef.read_antennas()
    assert int(a["HH123"]["E"]) == 540945


def test_geo_regions():
    err_msg = "1000 is not valid antenna."
    with pytest.raises(ValueError, match=err_msg):
        geo_sysdef.ant_region(ants=1000)
    with pytest.warns(UserWarning, match="HH does not match region A"):
        ret = geo_sysdef.ant_region(ants="HH325")
    assert ret == "A"
    testing = [123, "123", "HH123", "A123"]
    ret = geo_sysdef.ant_region(ants=testing)
    for r in ret:
        assert r == "W"


def test_update_new(mcsession, geo_handle):
    nte = "HH_new_test_element"
    data = [
        [nte, "station_name", nte],
        [nte, "station_type_name", "herahex"],
        [nte, "datum", "WGS84"],
        [nte, "tile", "34J"],
        [nte, "northing", 6600000.0],
        [nte, "easting", 541000.0],
        [nte, "elevation", 1050.0],
        [nte, "created_gpstime", 1172530000],
    ]
    geo_location.update(session=mcsession, data=data, add_new_geo=True)
    located = geo_handle.get_location([nte], "now")
    assert located[0].station_type_name == "herahex"
    nte = "HH_another_new_test_element"
    data = [
        [nte, "station_name", nte],
        [nte, "station_type_name", "herahex"],
        [nte, "datum", "WGS84"],
        [nte, "tile", "34J"],
        [nte, "northing", 6600000.0],
        [nte, "easting", 541000.0],
        [nte, "elevation", 1050.0],
        [nte, "created_gpstime", 1172530000],
    ]
    err_msg = "{} does not exist and add_new_geo not enabled.".format(nte)
    with pytest.raises(ValueError, match=err_msg):
        geo_location.update(session=mcsession, data=data, add_new_geo=False)


def test_update_update(mcsession, geo_handle):
    data = [["HH704", "elevation", 1100.0]]
    geo_location.update(mcsession, data, add_new_geo=False)
    located = geo_handle.get_location(["HH704"], "now")
    assert located[0].elevation == 1100.0
    err_msg = "HH704 exists and and_new_geo is enabled."
    with pytest.raises(ValueError, match=err_msg):
        geo_location.update(session=mcsession, data=data, add_new_geo=True)


def test_random(geo_handle, capsys):
    geo_handle.start_file("test")
    captured = capsys.readouterr()
    assert "Writing to new test" in captured.out


def test_geo_location(mcsession):
    g = geo_location.GeoLocation()
    g.geo(station_name="TestSetAttr")
    assert g.station_name == "TESTSETATTR"
    rv = geo_location.update()
    assert not rv
    err_msg = "Invalid parse request - need 3 parameters for at least first one."
    with pytest.raises(ValueError, match=err_msg):
        geo_location.update(session=mcsession, data="HH0:Tile")
    err_msg = "Invalid format for update request."
    with pytest.raises(ValueError, match=err_msg):
        geo_location.update(
            session=mcsession, data="HH0:Tile:34J,Elevation:0.0,Northing"
        )


def test_station_types(geo_handle):
    geo_handle.get_station_types()
    assert geo_handle.station_types["cofa"]["Prefix"] == "COFA"


def test_get_ants_installed_since(geo_handle):
    query_date = Time("2017-05-01 01:00:00", scale="utc")
    ants_in = geo_handle.get_ants_installed_since(
        query_date, station_types_to_check=["HH"]
    )
    assert len(ants_in) == 13


def test_plotting(geo_handle):
    stations_to_plot = ["HH702"]
    query_date = Time("2019-10-20 01:00:00", scale="utc")
    stations = geo_handle.get_location(stations_to_plot, query_date)
    geo_handle.plot_stations(
        stations,
        xgraph="E",
        ygraph="N",
        show_label="name",
        marker_color="k",
        marker_shape="*",
        marker_size=14,
    )
    geo_handle.plot_stations(
        stations,
        xgraph="E",
        ygraph="N",
        show_label="num",
        marker_color="k",
        marker_shape="*",
        marker_size=14,
    )
    geo_handle.plot_stations(
        stations,
        xgraph="E",
        ygraph="N",
        show_label="ser",
        marker_color="k",
        marker_shape="*",
        marker_size=14,
    )
    geo_handle.plot_stations(
        stations,
        xgraph="E",
        ygraph="N",
        show_label="other_thing",
        marker_color="k",
        marker_shape="*",
        marker_size=14,
    )
    geo_handle.plot_station_types(
        query_date=query_date,
        station_types_to_use=["HH"],
        xgraph="E",
        ygraph="N",
        show_state="active",
        show_label="name",
    )
    geo_handle.plot_station_types(
        query_date=query_date,
        station_types_to_use=["HH"],
        xgraph="E",
        ygraph="N",
        show_state="active",
        show_label="name",
    )
    geo_handle.print_loc_info(None)
    geo_handle.print_loc_info(stations)
    geo_handle.plot_all_stations()
    geo_handle.set_graph("testit")
    assert geo_handle.graph == "testit"
    geo_handle.plot_all_stations()


@pytest.mark.parametrize(
    ("label_type, val"), [("name", "HH700"), ("num", "700"), ("ser", "700")]
)
def test_antenna_label(geo_handle, label_type, val):
    stations_to_plot = ["HH700"]
    query_date = Time("2019-09-20 01:00:00", scale="utc")
    stations = geo_handle.get_location(stations_to_plot, query_date)
    x = geo_handle.get_antenna_label(label_type, stations[0], query_date)
    assert x == val


def test_geo_handling(geo_handle):
    h = geo_handling.get_location(["HH701"], testing=True)
    assert h[0].station_name == "HH701"
    geo_handle.file_type = "csv"
    hdr = geo_handle._loc_line("header")
    assert hdr.startswith("name")
    ll = geo_handle._loc_line(h[0])
    assert ll.startswith("HH701")
    ll = geo_handle._loc_line(h)
    assert ll[0].startswith("HH701")
    geo_handle.file_type = "txt"
    hdr = geo_handle._loc_line("header")
    assert hdr.startswith("name")
    ll = geo_handle._loc_line(h)
    assert ll[0].strip().startswith("HH701")


def test_parse_station_types(geo_handle):
    st = geo_handle.parse_station_types_to_check("all")
    assert "container" in st
    st = geo_handle.parse_station_types_to_check("hh")
    assert "herahexe" in st


def test_get_active_stations(geo_handle):
    active = geo_handle.get_active_stations(["HH"], "now", hookup_type="parts_hera")
    assert len(active) == 11


def test_is_in_database(geo_handle):
    assert geo_handle.is_in_database(station_name="HH700", db_name="geo_location")
    assert geo_handle.is_in_database(station_name="HH700", db_name="connections")
    assert not geo_handle.is_in_database(station_name="BB0", db_name="geo_location")
    err_msg = "db not found."
    with pytest.raises(ValueError, match=err_msg):
        geo_handle.is_in_database(station_name="HH666", db_name="wrong_one")


def test_find_antenna_station_pair(geo_handle, mcsession):
    ant, rev = geo_handle.find_antenna_at_station("HH700", "now")
    assert ant == "A700"
    ant, rev = geo_handle.find_antenna_at_station("BB23", "now")
    assert ant is None
    u = ["HH700", "A", "A700", "H", "ground", "ground", 1220000000]
    data = [
        u + ["upstream_part", u[0]],
        u + ["up_part_rev", u[1]],
        u + ["downstream_part", u[2]],
        u + ["down_part_rev", u[3]],
        u + ["upstream_output_port", u[4]],
        u + ["downstream_input_port", u[5]],
        u + ["start_gpstime", u[6]],
    ]
    cm_partconnect.update_connection(mcsession, data, add_new_connection=True)
    err_msg = "More than one active connection between station and antenna"
    with pytest.raises(ValueError, match=err_msg):
        geo_handle.find_station_of_antenna(antenna=700, query_date="now")
    stn = geo_handle.find_station_of_antenna(antenna="702", query_date="now")
    assert stn == "HH702"
    stn = geo_handle.find_station_of_antenna(antenna="A702", query_date="now")
    assert stn == "HH702"
    stn = geo_handle.find_station_of_antenna(antenna=1024, query_date="now")
    assert stn is None
