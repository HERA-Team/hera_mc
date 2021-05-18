# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.node`."""
import copy
import os
from math import floor

from astropy.time import Time, TimeDelta
import numpy as np
import pytest

from .. import node
from ..tests import requires_redis


@pytest.fixture(scope='module')
def nodelist():
    return list(range(1, 4))


@pytest.fixture(scope='module')
def sensor():
    return {
        '1': {'temp_top': 30., 'temp_mid': 31.98, 'temp_bot': 41,
              'temp_humid': 33.89, 'humid': 32.5,
              'timestamp': Time(1512770942.726777, format='unix').to_datetime()},
        '2': {'temp_top': None, 'temp_mid': None, 'temp_bot': None,
              'temp_humid': 33, 'humid': 40.,
              'timestamp': Time(1512770942.995268, format='unix').to_datetime()},
        '3': {'temp_top': 29.1, 'temp_mid': 33.8, 'temp_bot': 41.6,
              'temp_humid': None, 'humid': None,
              'timestamp': Time(1512770942.861526, format='unix').to_datetime()}
    }


@pytest.fixture(scope='module')
def power():
    return {
        '1': {'power_snap_relay': True, 'power_snap_0': False,
              'power_snap_1': True, 'power_snap_2': False,
              'power_snap_3': False, 'power_pam': True,
              'power_fem': True,
              'timestamp': Time(1512770942.726777, format='unix').to_datetime()},
        '2': {'power_snap_relay': False, 'power_snap_0': True,
              'power_snap_1': False,
              'power_snap_2': True, 'power_snap_3': True, 'power_pam': False,
              'power_fem': False,
              'timestamp': Time(1512770942.995268, format='unix').to_datetime()},
        '3': {'power_snap_relay': False, 'power_snap_0': False,
              'power_snap_1': False,
              'power_snap_2': False, 'power_snap_3': False, 'power_pam': False,
              'power_fem': False,
              'timestamp': Time(1512770942.861526, format='unix').to_datetime()}
    }


board_info_str = ('''
wrc# ver
WR Core build: 064c608-dirty
Built on Jan 24 2017, 16:38:15
Built for 117 kB RAM, stack is 2048 bytes
1-wire ROM ID (DS18B20U) : 0x72000009
EEPROM FRU info is valid:
 FRU VENDOR  : 7S
 FRU DEVICE  : WRLEN
 FRU SERIAL  : 7SWRLENv?.0-S08_313
 FRU PARTNUM : 7SWRLENv?.0-S08
 FRU FID     : 2017-12-13 10:25:23.617560
 FRU CUSTOM  : tag
Gateware info:
 GW ID      : 0x751e41c0
 GW VERSION : 3.9.29
 GW DATE    : 17/03/29 17:18
''')

board_info_str = 'some very long string\n blah blah blah'


@pytest.fixture(scope='module')
def white_rabbit_status():
    return {
        '1': {'timestamp': Time(1512770942.726777, format='unix').to_datetime(),
              'board_info_str': (board_info_str),
              'aliases': ['heraNode0wr'],
              'ip': '10.80.2.138',
              'mode': 'WRC_SLAVE_WR0',
              'serial': 'wr-len4p0',
              'temp': 46.0,
              'sw_build_date': Time('2017-01-24 16:38:15').to_datetime(),
              'wr_gw_date': Time('2017-03-29 17:18:00').to_datetime(),
              'wr_gw_version': '3.9.29',
              'wr_gw_id': '0x751e41c0',
              'wr_build': '064c608-dirty',
              'wr_fru_custom': 'tag',
              'wr_fru_device': 'WRLEN',
              'wr_fru_fid': Time('2017-12-13 10:25:23.617560').to_datetime(),
              'wr_fru_partnum': '7SWRLENv?.0-S08',
              'wr_fru_serial': '7SWRLENv?.0-S08_313',
              'wr_fru_vendor': '7S',
              'wr0_ad': 65000,
              'wr1_ad': None,
              'wr0_asym': 9541,
              'wr1_asym': None,
              'wr0_aux': 0,
              'wr1_aux': None,
              'wr0_cko': -1,
              'wr1_cko': None,
              'wr0_crtt': 3322243,
              'wr1_crtt': None,
              'wr0_dms': 1889158,
              'wr1_dms': None,
              'wr0_drxm': 237577,
              'wr1_drxm': None,
              'wr0_drxs': 4000,
              'wr1_drxs': None,
              'wr0_dtxm': 224037,
              'wr1_dtxm': None,
              'wr0_dtxs': 0,
              'wr1_dtxs': None,
              'wr0_hd': 59195,
              'wr1_hd': None,
              'wr0_lnk': True,
              'wr1_lnk': True,
              'wr0_lock': True,
              'wr1_lock': True,
              'wr0_md': 49807,
              'wr1_md': None,
              'wr0_mu': 3787857,
              'wr1_mu': None,
              'wr0_nsec': 515715728,
              'wr1_nsec': None,
              'wr0_rx': 157265,
              'wr1_rx': 0,
              'wr0_setp': 311,
              'wr1_setp': None,
              'wr0_ss': "'TRACK_PHASE'",
              'wr1_ss': None,
              'wr0_sv': 1,
              'wr1_sv': None,
              'wr0_syncs': 'wr0',
              'wr1_syncs': None,
              'wr0_tx': 34791,
              'wr1_tx': 86437,
              'wr0_ucnt': 31814,
              'wr1_ucnt': None,
              'wr0_sec': 1575578672,
              'wr1_sec': None},
        '2': {'timestamp': Time(1512770942.995268, format='unix').to_datetime(),
              'board_info_str': None,
              'aliases': ['heraNode7wr', 'heraNode7wr_alias'],
              'ip': '10.80.2.144',
              'mode': 'WRC_SLAVE_WR0',
              'serial': 'wr-len7p0',
              'temp': 47.812,
              'sw_build_date': None,
              'wr_gw_date': None,
              'wr_gw_version': None,
              'wr_gw_id': None,
              'wr_build': None,
              'wr_fru_custom': None,
              'wr_fru_device': None,
              'wr_fru_fid': None,
              'wr_fru_partnum': None,
              'wr_fru_serial': None,
              'wr_fru_vendor': None,
              'wr0_ad': 65000,
              'wr1_ad': None,
              'wr0_asym': 2158,
              'wr1_asym': None,
              'wr0_aux': 0,
              'wr1_aux': None,
              'wr0_cko': 2,
              'wr1_cko': None,
              'wr0_crtt': 1525938,
              'wr1_crtt': None,
              'wr0_dms': 990482,
              'wr1_dms': None,
              'wr0_drxm': 229671,
              'wr1_drxm': None,
              'wr0_drxs': 3200,
              'wr1_drxs': None,
              'wr0_dtxm': 224313,
              'wr1_dtxm': None,
              'wr0_dtxs': 0,
              'wr1_dtxs': None,
              'wr0_hd': 59391,
              'wr1_hd': None,
              'wr0_lnk': True,
              'wr1_lnk': False,
              'wr0_lock': True,
              'wr1_lock': False,
              'wr0_md': 48721,
              'wr1_md': None,
              'wr0_mu': 1983122,
              'wr1_mu': None,
              'wr0_nsec': 73300560,
              'wr1_nsec': None,
              'wr0_rx': 157982,
              'wr1_rx': 0,
              'wr0_setp': 13582,
              'wr1_setp': None,
              'wr0_ss': "'TRACK_PHASE'",
              'wr1_ss': None,
              'wr0_sv': 1,
              'wr1_sv': None,
              'wr0_syncs': 'wr0',
              'wr1_syncs': None,
              'wr0_tx': 34916,
              'wr1_tx': 86795,
              'wr0_ucnt': 31935,
              'wr1_ucnt': None,
              'wr0_sec': 1575578804,
              'wr1_sec': None},
        '3': {'timestamp': Time(1512770942.995268, format='unix').to_datetime(),
              'board_info_str': None,
              'aliases': [],
              'ip': None,
              'mode': None,
              'serial': None,
              'temp': np.nan,
              'sw_build_date': None,
              'wr_gw_date': None,
              'wr_gw_version': None,
              'wr_gw_id': None,
              'wr_build': None,
              'wr_fru_custom': None,
              'wr_fru_device': None,
              'wr_fru_fid': None,
              'wr_fru_partnum': None,
              'wr_fru_serial': None,
              'wr_fru_vendor': None,
              'wr0_ad': 65000,
              'wr1_ad': None,
              'wr0_asym': 2158,
              'wr1_asym': None,
              'wr0_aux': 0,
              'wr1_aux': None,
              'wr0_cko': 2,
              'wr1_cko': None,
              'wr0_crtt': 1525938,
              'wr1_crtt': None,
              'wr0_dms': 990482,
              'wr1_dms': None,
              'wr0_drxm': 229671,
              'wr1_drxm': None,
              'wr0_drxs': 3200,
              'wr1_drxs': None,
              'wr0_dtxm': 224313,
              'wr1_dtxm': None,
              'wr0_dtxs': 0,
              'wr1_dtxs': None,
              'wr0_hd': 59391,
              'wr1_hd': None,
              'wr0_lnk': True,
              'wr1_lnk': True,
              'wr0_lock': None,
              'wr1_lock': True,
              'wr0_md': 48721,
              'wr1_md': None,
              'wr0_mu': 1983122,
              'wr1_mu': None,
              'wr0_nsec': 73300560,
              'wr1_nsec': None,
              'wr0_rx': 157982,
              'wr1_rx': 0,
              'wr0_setp': 13582,
              'wr1_setp': None,
              'wr0_ss': "'TRACK_PHASE'",
              'wr1_ss': None,
              'wr0_sv': 1,
              'wr1_sv': None,
              'wr0_syncs': 'wr0',
              'wr1_syncs': None,
              'wr0_tx': 34916,
              'wr1_tx': 86795,
              'wr0_ucnt': 31935,
              'wr1_ucnt': None,
              'wr0_sec': 1575578804,
              'wr1_sec': None}
    }


@pytest.fixture(scope='module')
def white_rabbit_status_cleaned(white_rabbit_status):
    cleaned_dict = {}
    for node_str, node_dict in white_rabbit_status.items():
        nodeID = int(node_str)
        cleaned_dict[node_str] = {
            'node_time': Time(node_dict['timestamp'], format='datetime', scale='utc'),
            'node': nodeID
        }
        for key, value in node.wr_key_dict.items():
            # key is column name, value is related key into wr_data
            wr_data_value = node_dict[value]
            if isinstance(wr_data_value, float) and np.isnan(wr_data_value):
                wr_data_value = None

            if key in node.wr_datetime_keys and wr_data_value is not None:
                cleaned_dict[node_str][key] = Time(wr_data_value, format='datetime', scale='utc')
            elif key in node.wr_tai_sec_keys and wr_data_value is not None:
                cleaned_dict[node_str][key] = Time(wr_data_value, format='unix', scale='tai')
            elif key == 'aliases' and wr_data_value is not None:
                if len(wr_data_value) == 0:
                    cleaned_dict[node_str][key] = None
                else:
                    cleaned_dict[node_str][key] = ', '.join(wr_data_value)
            else:
                cleaned_dict[node_str][key] = wr_data_value
    return cleaned_dict


@pytest.fixture(scope='module')
def white_rabbit_status_sql(white_rabbit_status_cleaned):
    sql_dict = {}
    for node_str, node_dict in white_rabbit_status_cleaned.items():
        nodeID = int(node_str)
        sql_dict[node_str] = {
            'node_time': floor(node_dict['node_time'].gps),
            'node': nodeID
        }
        for key in node.wr_key_dict:
            wr_data_value = node_dict[key]
            if isinstance(wr_data_value, float) and np.isnan(wr_data_value):
                wr_data_value = None

            if ((key in node.wr_datetime_keys or key in node.wr_tai_sec_keys)
                    and wr_data_value is not None):
                sql_dict[node_str][key] = floor(wr_data_value.gps)
            else:
                sql_dict[node_str][key] = wr_data_value
    return sql_dict


def test_add_node_sensor_readings(mcsession, sensor, tmpdir):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    top_sensor_temp = sensor['1']['temp_top']
    middle_sensor_temp = sensor['1']['temp_mid']
    bottom_sensor_temp = sensor['1']['temp_bot']
    humidity_sensor_temp = sensor['1']['temp_humid']
    humidity = sensor['1']['humid']
    test_session.add_node_sensor_readings(t1, 1, top_sensor_temp,
                                          middle_sensor_temp,
                                          bottom_sensor_temp,
                                          humidity_sensor_temp, humidity)

    expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                               top_sensor_temp=30., middle_sensor_temp=31.98,
                               bottom_sensor_temp=41.,
                               humidity_sensor_temp=33.89, humidity=32.5)
    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    top_sensor_temp = sensor['2']['temp_top']
    middle_sensor_temp = sensor['2']['temp_mid']
    bottom_sensor_temp = sensor['2']['temp_bot']
    humidity_sensor_temp = sensor['2']['temp_humid']
    humidity = sensor['2']['humid']
    test_session.add_node_sensor_readings(t1, 2, top_sensor_temp,
                                          middle_sensor_temp,
                                          bottom_sensor_temp,
                                          humidity_sensor_temp,
                                          humidity)

    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 2

    result_most_recent = test_session.get_node_sensor_readings()
    assert len(result) == 2
    assert result_most_recent == result

    filename = os.path.join(tmpdir, 'test_node_sensor_file.csv')
    test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1,
        write_to_file=True, filename=filename)
    os.remove(filename)

    test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1,
        write_to_file=True)
    default_filename = 'node_sensor.csv'
    os.remove(default_filename)

    result = test_session.get_node_sensor_readings(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_create_sensor_readings(mcsession, nodelist, sensor):
    test_session = mcsession
    sensor_obj_list = node.create_sensor_readings(
        node_list=nodelist, sensor_dict=sensor)

    for obj in sensor_obj_list:
        test_session.add(obj)

    t1 = Time(1512770942.726777, format='unix')
    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)

    expected = node.NodeSensor(time=int(floor(t1.gps)), node=1,
                               top_sensor_temp=30., middle_sensor_temp=31.98,
                               bottom_sensor_temp=41.,
                               humidity_sensor_temp=33.89,
                               humidity=32.5)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=2)

    expected = node.NodeSensor(time=int(floor(t1.gps)), node=2,
                               top_sensor_temp=None, middle_sensor_temp=None,
                               bottom_sensor_temp=None,
                               humidity_sensor_temp=33, humidity=40.)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=3)

    expected = node.NodeSensor(time=int(floor(t1.gps)), node=3,
                               top_sensor_temp=29.1, middle_sensor_temp=33.8,
                               bottom_sensor_temp=41.6,
                               humidity_sensor_temp=None, humidity=None)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_sensor_readings(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        stoptime=t1 + TimeDelta(5.0, format='sec'))
    assert len(result) == 3

    result_most_recent = test_session.get_node_sensor_readings(
        most_recent=True)
    assert result_most_recent == result


def test_sensor_reading_errors(mcsession, sensor):
    test_session = mcsession
    top_sensor_temp = sensor['1']['temp_top']
    middle_sensor_temp = sensor['1']['temp_mid']
    bottom_sensor_temp = sensor['1']['temp_bot']
    humidity_sensor_temp = sensor['1']['temp_humid']
    humidity = sensor['1']['humid']
    with pytest.raises(ValueError) as cm:
        test_session.add_node_sensor_readings(
            'foo', 1, top_sensor_temp, middle_sensor_temp,
            bottom_sensor_temp, humidity_sensor_temp, humidity)
    assert str(cm.value).startswith('time must be an astropy Time object')


@requires_redis
def test_add_node_sensor_readings_from_nodecontrol(mcsession):
    test_session = mcsession

    node_list = node.get_node_list()

    test_session.add_node_sensor_readings_from_nodecontrol()
    result = test_session.get_node_sensor_readings(
        starttime=Time.now() - TimeDelta(120.0, format='sec'),
        stoptime=Time.now() + TimeDelta(120.0, format='sec'))

    nodes_with_status = []
    for sensor_obj in result:
        nodes_with_status.append(sensor_obj.node)
    if len(result) != len(nodes_with_status):
        print('Nodes that hera_node_mc returns as active:')
        print(node_list)
        print('Nodes with sensor readings:')
        print(nodes_with_status)
    assert len(result) == len(nodes_with_status)


def test_add_node_power_status(mcsession, power):
    test_session = mcsession
    t1 = Time('2016-01-10 01:15:23', scale='utc')

    snap_relay_powered = power['1']['power_snap_relay']
    snap0_powered = power['1']['power_snap_0']
    snap1_powered = power['1']['power_snap_1']
    snap2_powered = power['1']['power_snap_2']
    snap3_powered = power['1']['power_snap_3']
    pam_powered = power['1']['power_pam']
    fem_powered = power['1']['power_fem']
    test_session.add_node_power_status(t1, 1, snap_relay_powered,
                                       snap0_powered, snap1_powered,
                                       snap2_powered, snap3_powered,
                                       fem_powered, pam_powered)

    expected = node.NodePowerStatus(time=int(floor(t1.gps)), node=1,
                                    snap_relay_powered=True,
                                    snap0_powered=False,
                                    snap1_powered=True, snap2_powered=False,
                                    snap3_powered=False, pam_powered=True,
                                    fem_powered=True)
    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    snap_relay_powered = power['2']['power_snap_relay']
    snap0_powered = power['2']['power_snap_0']
    snap1_powered = power['2']['power_snap_1']
    snap2_powered = power['2']['power_snap_2']
    snap3_powered = power['2']['power_snap_3']
    pam_powered = power['2']['power_pam']
    fem_powered = power['2']['power_fem']
    test_session.add_node_power_status(
        t1, 2, snap_relay_powered, snap0_powered, snap1_powered, snap2_powered,
        snap3_powered, fem_powered, pam_powered)

    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    expected = node.NodePowerStatus(time=int(floor(t1.gps)), node=2,
                                    snap_relay_powered=False,
                                    snap0_powered=True,
                                    snap1_powered=False, snap2_powered=True,
                                    snap3_powered=True, pam_powered=False,
                                    fem_powered=False)

    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=2)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 2

    result_most_recent = test_session.get_node_power_status()
    assert len(result_most_recent) == 2
    assert result_most_recent == result

    result = test_session.get_node_power_status(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_create_power_status(mcsession, nodelist, power):
    test_session = mcsession
    sensor_obj_list = node.create_power_status(
        node_list=nodelist, power_dict=power)

    for obj in sensor_obj_list:
        test_session.add(obj)

    t1 = Time(1512770942.726777, format='unix')
    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)

    expected = node.NodePowerStatus(time=int(floor(t1.gps)), node=1,
                                    snap_relay_powered=True,
                                    snap0_powered=False,
                                    snap1_powered=True, snap2_powered=False,
                                    snap3_powered=False, pam_powered=True,
                                    fem_powered=True)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_power_status(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        stoptime=t1 + TimeDelta(5.0, format='sec'))
    assert len(result) == 3

    result_most_recent = test_session.get_node_power_status()
    assert result_most_recent == result


def test_node_power_status_errors(mcsession, power):
    test_session = mcsession
    snap_relay_powered = power['1']['power_snap_relay']
    snap0_powered = power['1']['power_snap_0']
    snap1_powered = power['1']['power_snap_1']
    snap2_powered = power['1']['power_snap_2']
    snap3_powered = power['1']['power_snap_3']
    pam_powered = power['1']['power_pam']
    fem_powered = power['1']['power_fem']
    pytest.raises(ValueError, test_session.add_node_power_status,
                  'foo', 1, snap_relay_powered, snap0_powered, snap1_powered,
                  snap2_powered, snap3_powered, fem_powered, pam_powered)


@requires_redis
def test_add_node_power_status_from_nodecontrol(mcsession):
    test_session = mcsession

    node_list = node.get_node_list()

    test_session.add_node_power_status_from_nodecontrol()
    result = test_session.get_node_power_status(
        starttime=Time.now() - TimeDelta(120.0, format='sec'),
        stoptime=Time.now() + TimeDelta(120.0, format='sec'))

    nodes_with_status = []
    for pw_obj in result:
        nodes_with_status.append(pw_obj.node)
    if len(result) != len(nodes_with_status):
        print('Nodes that hera_node_mc returns as active:')
        print(node_list)
        print('Nodes with power status info:')
        print(nodes_with_status)
    assert len(result) == len(nodes_with_status)


def test_add_white_rabbit_status(
    mcsession,
    white_rabbit_status_cleaned,
    white_rabbit_status_sql,
    tmpdir,
):
    test_session = mcsession
    t1 = Time(1512770942.726777, format='unix')

    test_session.add_node_white_rabbit_status(white_rabbit_status_cleaned['1'])

    expected = node.NodeWhiteRabbitStatus(**white_rabbit_status_sql['1'])
    result = test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'))

    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    test_session.add_node_white_rabbit_status(white_rabbit_status_cleaned['2'])

    result = test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1)
    assert len(result) == 2

    result_most_recent = test_session.get_node_white_rabbit_status()
    assert len(result) == 2
    assert result_most_recent == result

    filename = os.path.join(tmpdir, 'test_node_white_rabbit_status_file.csv')
    test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1,
        write_to_file=True, filename=filename)
    os.remove(filename)

    test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), stoptime=t1,
        write_to_file=True)
    default_filename = 'node_white_rabbit_status.csv'
    os.remove(default_filename)

    result = test_session.get_node_white_rabbit_status(
        starttime=t1 + TimeDelta(200.0, format='sec'))
    assert result == []


def test_create_white_rabbit_status(mcsession, nodelist, white_rabbit_status,
                                    white_rabbit_status_cleaned,
                                    white_rabbit_status_sql):
    test_session = mcsession
    wr_obj_list = node.create_wr_status(
        node_list=nodelist, wr_status_dict=white_rabbit_status)

    for obj in wr_obj_list:
        test_session.add(obj)

    t1 = Time(1512770942.726777, format='unix')
    result = test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=1)

    expected = node.NodeWhiteRabbitStatus(**white_rabbit_status_sql['1'])
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=2)

    expected = node.NodeWhiteRabbitStatus(**white_rabbit_status_sql['2'])
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'), nodeID=3)

    expected = node.NodeWhiteRabbitStatus(**white_rabbit_status_sql['3'])
    assert len(result) == 1
    result = result[0]
    assert result.isclose(expected)

    result = test_session.get_node_white_rabbit_status(
        starttime=t1 - TimeDelta(3.0, format='sec'),
        stoptime=t1 + TimeDelta(5.0, format='sec'))
    assert len(result) == 3

    result_most_recent = test_session.get_node_white_rabbit_status(
        most_recent=True)
    assert result_most_recent == result


@pytest.mark.parametrize(
    ("key"), ['node_time'] + node.wr_datetime_keys + node.wr_tai_sec_keys
)
def test_white_rabbit_status_errors(mcsession, white_rabbit_status_cleaned, key):
    wr_dict_use = copy.deepcopy(white_rabbit_status_cleaned['1'])
    wr_dict_use[key] = 'foo'
    with pytest.raises(ValueError) as cm:
        mcsession.add_node_white_rabbit_status(wr_dict_use)
    assert str(cm.value).startswith(key + ' must be an astropy Time object')


@requires_redis
def test_add_white_rabbit_status_from_nodecontrol(mcsession):
    test_session = mcsession

    node_list = node.get_node_list()

    test_session.add_node_white_rabbit_status_from_nodecontrol()
    result = test_session.get_node_white_rabbit_status(
        starttime=Time.now() - TimeDelta(120.0, format='sec'),
        stoptime=Time.now() + TimeDelta(120.0, format='sec'))

    nodes_with_status = []
    for wr_obj in result:
        nodes_with_status.append(wr_obj.node)
    if len(result) != len(nodes_with_status):
        print('Nodes that hera_node_mc returns as active:')
        print(node_list)
        print('Nodes with white rabbit status info:')
        print(nodes_with_status)
    assert len(result) == len(nodes_with_status)
