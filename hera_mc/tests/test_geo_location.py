# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.geo_location and geo_handling`."""

from __future__ import absolute_import, division, print_function

import pytest

from .. import geo_location, geo_handling
from ..tests import checkWarnings
from astropy.time import Time


@pytest.fixture(scope='function')
def geo_handle(mcsession):
    return geo_handling.Handling(mcsession, testing=True)


def test_cofa(mcsession, geo_handle):
    geo_handle.get_station_types()
    station_types = [type.lower() for type in geo_handle.station_types.keys()]
    assert 'cofa' in station_types

    cofa = geo_handle.cofa()[0]

    # test that function works the same as method
    cofa_func = geo_handling.cofa(session=mcsession)[0]
    assert cofa.isclose(cofa_func)


def test_update_new(mcsession, geo_handle):
    nte = 'HH_new_test_element'
    data = [[nte, 'station_name', nte],
            [nte, 'station_type_name', 'herahex'],
            [nte, 'datum', 'WGS84'],
            [nte, 'tile', '34J'],
            [nte, 'northing', 6600000.0],
            [nte, 'easting', 541000.0],
            [nte, 'elevation', 1050.0],
            [nte, 'created_gpstime', 1172530000]]
    geo_location.update(mcsession, data, add_new_geo=True)
    located = geo_handle.get_location([nte], 'now')
    assert located[0].station_type_name == 'herahex'


def test_update_update(mcsession, geo_handle):
    data = [["HH23", 'elevation', 1100.0]]
    geo_location.update(mcsession, data, add_new_geo=False)
    located = geo_handle.get_location(["HH23"], 'now')
    assert located[0].elevation == 1100.0


def test_random(geo_handle):
    geo_handle.start_file('test')


def test_geo_location(mcsession):
    g = geo_location.GeoLocation()
    g.geo(station_name='TestSetAttr')
    assert g.station_name == 'TESTSETATTR'
    print(g)
    s = geo_location.StationType()
    print(s)
    rv = geo_location.update()
    assert not rv
    rv = geo_location.update(session=mcsession, data='HH0:Tile')
    assert not rv
    rv = geo_location.update(session=mcsession,
                             data='HH0:Tile:34J,Elevation:0.0,Northing')
    assert rv
    rv = geo_location.update(session=mcsession, data='HHX:Tile:34J')
    assert rv
    rv = geo_location.update(session=mcsession, data='HH0:Tile:34J',
                             add_new_geo=True)
    assert rv
    rv = geo_location.update(session=mcsession, data='HH0:NotThere:34J')
    assert rv


def test_station_types(geo_handle):
    geo_handle.get_station_types()
    assert geo_handle.station_types['cofa']['Prefix'] == 'COFA'


def test_get_ants_installed_since(geo_handle):
    query_date = Time('2017-05-01 01:00:00', scale='utc')
    ants_in = geo_handle.get_ants_installed_since(
        query_date, station_types_to_check=['HH'])
    assert len(ants_in) == 7


def test_plotting(geo_handle):
    stations_to_plot = ['HH0']
    query_date = Time('2017-08-25 01:00:00', scale='utc')
    stations = geo_handle.get_location(stations_to_plot, query_date)
    geo_handle.plot_stations(stations, xgraph='E', ygraph='N',
                             show_label='name', marker_color='k',
                             marker_shape='*', marker_size=14)
    geo_handle.plot_stations(stations, xgraph='E', ygraph='N', show_label='num',
                             marker_color='k', marker_shape='*', marker_size=14)
    geo_handle.plot_stations(stations, xgraph='E', ygraph='N', show_label='ser',
                             marker_color='k', marker_shape='*', marker_size=14)
    geo_handle.plot_stations(stations, xgraph='E', ygraph='N',
                             show_label='other_thing', marker_color='k',
                             marker_shape='*', marker_size=14)
    geo_handle.plot_station_types(query_date=query_date,
                                  station_types_to_use=['HH'], xgraph='E',
                                  ygraph='N', show_state='active',
                                  show_label='name')
    geo_handle.plot_station_types(query_date=query_date,
                                  station_types_to_use=['HH'],
                                  xgraph='E', ygraph='N',
                                  show_state='active', show_label='name')
    geo_handle.print_loc_info(None)
    geo_handle.print_loc_info(stations)
    geo_handle.plot_all_stations()
    geo_handle.set_graph('testit')
    assert geo_handle.graph == 'testit'
    geo_handle.plot_all_stations()


def test_antenna_label(geo_handle):
    stations_to_plot = ['HH0']
    query_date = Time('2017-08-25 01:00:00', scale='utc')
    stations = geo_handle.get_location(stations_to_plot, query_date)
    x = geo_handle.get_antenna_label('name', stations[0], query_date)
    assert x == 'HH0'
    x = geo_handle.get_antenna_label('num', stations[0], query_date)
    assert x == '0'
    x = geo_handle.get_antenna_label('ser', stations[0], query_date)
    assert x == 'H3'


def test_parse_station_types(geo_handle):
    st = geo_handle.parse_station_types_to_check('all')
    assert 'container' in st
    st = geo_handle.parse_station_types_to_check('hh')
    assert 'herahexe' in st


def test_get_active_stations(geo_handle):
    active = geo_handle.get_active_stations(
        'now', ['HH'], hookup_type='parts_paper')
    assert active[0].station_name == 'HH0'


def test_is_in_database(geo_handle):
    assert geo_handle.is_in_database('HH23', 'geo_location')
    assert geo_handle.is_in_database('HH23', 'connections')
    assert not geo_handle.is_in_database('BB0', 'geo_location')
    pytest.raises(ValueError, geo_handle.is_in_database, 'HH666', 'wrong_one')


def test_find_antenna_station_pair(geo_handle):
    ant, rev = geo_handle.find_antenna_at_station('HH23', 'now')
    assert ant == 'A23'
    ant, rev = geo_handle.find_antenna_at_station('BB23', 'now')
    assert ant is None
    c = checkWarnings(geo_handle.find_antenna_at_station, ['HH68', 'now'],
                      message='More than one active connection for HH68')
    assert len(c) == 2
    stn = geo_handle.find_station_of_antenna('A23', 'now')
    assert stn == 'HH23'
    stn = geo_handle.find_station_of_antenna(23, 'now')
    assert stn == 'HH23'
    stn = geo_handle.find_station_of_antenna(1024, 'now')
    assert stn is None
    pytest.raises(ValueError, geo_handle.find_station_of_antenna, 68, 'now')
