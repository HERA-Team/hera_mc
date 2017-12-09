# -*- mode: python; coding: utf-8 -*-
# Copyright 2017 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.roach`.

"""
from __future__ import absolute_import, division, print_function

import unittest
import nose.tools as nt
import socket
from math import floor
from astropy.time import Time, TimeDelta
from hera_mc import mc, roach
from hera_mc.tests import TestHERAMC


roach_example_dict = {
    'pf1': {'raw.current.1v5': '10162', 'raw.temp.outlet': '31750',
            'raw.fan.chs2': '7650', 'raw.fan.chs1': '7650',
            'raw.fan.chs0': '7650', 'human_timestamp': 'Sat Dec  9 00:09:02 2017',
            'raw.current.3v3': '1962', 'raw.voltage.1v5': '1504',
            'raw.current.12v': '3286', 'raw.voltage.1v8': '1802',
            'raw.voltage.2v5': '2503', 'raw.voltage.12v': '11538',
            'raw.temp.ambient': '30000', 'raw.voltage.5v': '5125',
            'raw.voltage.1v': '1009', 'raw.current.5v': '4395',
            'raw.current.1v': '1577', 'raw.temp.inlet': '32000',
            'raw.temp.fpga': '57000', 'raw.voltage.3v3aux': '3398',
            'timestamp': '1512770942.726777', 'raw.current.1v8': '1577',
            'raw.voltage.5vaux': '5082', 'raw.current.2v5': '3665',
            'raw.voltage.3v3': '3366', 'raw.fan.fpga': '5730',
            'raw.temp.ppc': '45000'},
    'pf3': {'raw.current.1v5': '10292', 'raw.temp.outlet': '29500',
            'raw.fan.chs2': '7650', 'raw.fan.chs1': '7650',
            'raw.fan.chs0': '7650', 'human_timestamp': 'Sat Dec  9 00:09:02 2017',
            'raw.current.3v3': '1962', 'raw.voltage.1v5': '1498',
            'raw.current.12v': '3160', 'raw.voltage.1v8': '1808',
            'raw.voltage.2v5': '2503', 'raw.voltage.12v': '11552',
            'raw.temp.ambient': '29000', 'raw.voltage.5v': '5125',
            'raw.voltage.1v': '1009', 'raw.current.5v': '4343',
            'raw.current.1v': '1411', 'raw.temp.inlet': '31250',
            'raw.temp.fpga': '54000', 'raw.voltage.3v3aux': '3398',
            'timestamp': '1512770942.995268', 'raw.current.1v8': '1411',
            'raw.voltage.5vaux': '5060', 'raw.current.2v5': '3690',
            'raw.voltage.3v3': '3355', 'raw.fan.fpga': '5730',
            'raw.temp.ppc': '46000'},
    'pf2': {'raw.current.1v5': '10743', 'raw.temp.outlet': '32250',
            'raw.fan.chs2': '7650', 'raw.fan.chs1': '7650',
            'raw.fan.chs0': '7650', 'human_timestamp': 'Sat Dec  9 00:09:02 2017',
            'raw.current.3v3': '1962', 'raw.voltage.1v5': '1504',
            'raw.current.12v': '3390', 'raw.voltage.1v8': '1808',
            'raw.voltage.2v5': '2503', 'raw.voltage.12v': '11603',
            'raw.temp.ambient': '31000', 'raw.voltage.5v': '5120',
            'raw.voltage.1v': '1004', 'raw.current.5v': '4813',
            'raw.current.1v': '1476', 'raw.temp.inlet': '31750',
            'raw.temp.fpga': '58000', 'raw.voltage.3v3aux': '3393',
            'timestamp': '1512770942.861526', 'raw.current.1v8': '1476',
            'raw.voltage.5vaux': '5087', 'raw.current.2v5': '3665',
            'raw.voltage.3v3': '3355', 'raw.fan.fpga': '5760',
            'raw.temp.ppc': '45000'},
    'pf5': {'raw.current.1v5': '10363', 'raw.temp.outlet': '32250',
            'raw.fan.chs2': '7650', 'raw.fan.chs1': '7650',
            'raw.fan.chs0': '7650', 'human_timestamp': 'Sat Dec  9 00:09:03 2017',
            'raw.current.3v3': '1992', 'raw.voltage.1v5': '1493',
            'raw.current.12v': '3160', 'raw.voltage.1v8': '1808',
            'raw.voltage.2v5': '2497', 'raw.voltage.12v': '11860',
            'raw.temp.ambient': '29000', 'raw.voltage.5v': '5114',
            'raw.voltage.1v': '1004', 'raw.current.5v': '4395',
            'raw.current.1v': '1606', 'raw.temp.inlet': '28250',
            'raw.temp.fpga': '61000', 'raw.voltage.3v3aux': '3388',
            'timestamp': '1512770943.260739', 'raw.current.1v8': '1606',
            'raw.voltage.5vaux': '5060', 'raw.current.2v5': '3714',
            'raw.voltage.3v3': '3360', 'raw.fan.fpga': '5730',
            'raw.temp.ppc': '43000'},
    'pf4': {'raw.current.1v5': '10363', 'raw.temp.outlet': '32250',
            'raw.fan.chs2': '7650', 'raw.fan.chs1': '7650',
            'raw.fan.chs0': '7650', 'human_timestamp': 'Sat Dec  9 00:09:03 2017',
            'raw.current.3v3': '1962', 'raw.voltage.1v5': '1498',
            'raw.current.12v': '3265', 'raw.voltage.1v8': '1808',
            'raw.voltage.2v5': '2508', 'raw.voltage.12v': '11730',
            'raw.temp.ambient': '31000', 'raw.voltage.5v': '4951',
            'raw.voltage.1v': '1009', 'raw.current.5v': '4395',
            'raw.current.1v': '1511', 'raw.temp.inlet': '32500',
            'raw.temp.fpga': '57000', 'raw.voltage.3v3aux': '3393',
            'timestamp': '1512770943.127049', 'raw.current.1v8': '1511',
            'raw.voltage.5vaux': '4979', 'raw.current.2v5': '3723',
            'raw.voltage.3v3': '3355', 'raw.fan.fpga': '5730',
            'raw.temp.ppc': '46000'},
    'pf7': {'raw.current.1v5': '10683', 'raw.temp.outlet': '31500',
            'raw.fan.chs2': '7650', 'raw.fan.chs1': '7650',
            'raw.fan.chs0': '7650', 'human_timestamp': 'Sat Dec  9 00:09:03 2017',
            'raw.current.3v3': '1992', 'raw.voltage.1v5': '1504',
            'raw.current.12v': '3495', 'raw.voltage.1v8': '1808',
            'raw.voltage.2v5': '2497', 'raw.voltage.12v': '11552',
            'raw.temp.ambient': '30000', 'raw.voltage.5v': '5098',
            'raw.voltage.1v': '1004', 'raw.current.5v': '5023',
            'raw.current.1v': '1636', 'raw.temp.inlet': '32750',
            'raw.temp.fpga': '56000', 'raw.voltage.3v3aux': '3371',
            'timestamp': '1512770943.52817', 'raw.current.1v8': '1636',
            'raw.voltage.5vaux': '5017', 'raw.current.2v5': '3682',
            'raw.voltage.3v3': '3355', 'raw.fan.fpga': '5730',
            'raw.temp.ppc': '47000'},
    'pf6': {'raw.current.1v5': '10162', 'raw.temp.outlet': '32500',
            'raw.fan.chs2': '7650', 'raw.fan.chs1': '7650',
            'raw.fan.chs0': '7650', 'human_timestamp': 'Sat Dec  9 00:09:03 2017',
            'raw.current.3v3': '1926', 'raw.voltage.1v5': '1504',
            'raw.current.12v': '3307', 'raw.voltage.1v8': '1813',
            'raw.voltage.2v5': '2503', 'raw.voltage.12v': '11552',
            'raw.temp.ambient': '30000', 'raw.voltage.5v': '5098',
            'raw.voltage.1v': '1009', 'raw.current.5v': '4500',
            'raw.current.1v': '1577', 'raw.temp.inlet': '32250',
            'raw.temp.fpga': '59000', 'raw.voltage.3v3aux': '3382',
            'timestamp': '1512770943.394443', 'raw.current.1v8': '1577',
            'raw.voltage.5vaux': '5017', 'raw.current.2v5': '3690',
            'raw.voltage.3v3': '3344', 'raw.fan.fpga': '5730',
            'raw.temp.ppc': '45000'},
    'pf8': {'raw.current.1v5': '10422', 'raw.temp.outlet': '32250',
            'raw.fan.chs2': '7650', 'raw.fan.chs1': '7650',
            'raw.fan.chs0': '7650', 'human_timestamp': 'Sat Dec  9 00:09:03 2017',
            'raw.current.3v3': '1962', 'raw.voltage.1v5': '1504',
            'raw.current.12v': '3244', 'raw.voltage.1v8': '1808',
            'raw.voltage.2v5': '2508', 'raw.voltage.12v': '11505',
            'raw.temp.ambient': '32000', 'raw.voltage.5v': '5120',
            'raw.voltage.1v': '1004', 'raw.current.5v': '4081',
            'raw.current.1v': '1476', 'raw.temp.inlet': '34000',
            'raw.temp.fpga': '57000', 'raw.voltage.3v3aux': '3404',
            'timestamp': '1512770943.66201', 'raw.current.1v8': '1476',
            'raw.voltage.5vaux': '5049', 'raw.current.2v5': '3649',
            'raw.voltage.3v3': '3355', 'raw.fan.fpga': '5730',
            'raw.temp.ppc': '49000'}}


def is_at_katcp_enabled_site():
    return (socket.gethostname() == 'qmaster')


class TestRoach(TestHERAMC):

    def test_add_roach(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        ambient_temp = float(roach_example_dict['pf1']['raw.temp.ambient']) / 1000.
        inlet_temp = float(roach_example_dict['pf1']['raw.temp.inlet']) / 1000.
        outlet_temp = float(roach_example_dict['pf1']['raw.temp.outlet']) / 1000.
        fpga_temp = float(roach_example_dict['pf1']['raw.temp.fpga']) / 1000.
        ppc_temp = float(roach_example_dict['pf1']['raw.temp.ppc']) / 1000.
        self.test_session.add_roach_temperature(t1, 1, ambient_temp, inlet_temp,
                                                outlet_temp, fpga_temp, ppc_temp)

        expected = roach.RoachTemperature(time=int(floor(t1.gps)), roach=1,
                                          ambient_temp=30., inlet_temp=32.,
                                          outlet_temp=31.75, fpga_temp=57.,
                                          ppc_temp=45.)
        result = self.test_session.get_roach_temperature(t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        ambient_temp = float(roach_example_dict['pf2']['raw.temp.ambient']) / 1000.
        inlet_temp = float(roach_example_dict['pf2']['raw.temp.inlet']) / 1000.
        outlet_temp = float(roach_example_dict['pf2']['raw.temp.outlet']) / 1000.
        fpga_temp = float(roach_example_dict['pf2']['raw.temp.fpga']) / 1000.
        ppc_temp = float(roach_example_dict['pf2']['raw.temp.ppc']) / 1000.
        self.test_session.add_roach_temperature(t1, 2, ambient_temp, inlet_temp,
                                                outlet_temp, fpga_temp, ppc_temp)

        result = self.test_session.get_roach_temperature(t1 - TimeDelta(3.0, format='sec'),
                                                         roach=1)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_roach_temperature(t1 - TimeDelta(3.0, format='sec'),
                                                         stoptime=t1)
        self.assertEqual(len(result), 2)

        result = self.test_session.get_roach_temperature(t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

    def test_create_from_redis(self):
        roach_obj_list = roach.create_from_redis(roach_example_dict)

        for obj in roach_obj_list:
            self.test_session.add(obj)

        t1 = Time(1512770942.726777, format='unix')
        result = self.test_session.get_roach_temperature(t1 - TimeDelta(3.0, format='sec'),
                                                         roach=1)

        expected = roach.RoachTemperature(time=int(floor(t1.gps)), roach=1,
                                          ambient_temp=30., inlet_temp=32.,
                                          outlet_temp=31.75, fpga_temp=57.,
                                          ppc_temp=45.)
        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue(result.isclose(expected))

        result = self.test_session.get_roach_temperature(t1 - TimeDelta(3.0, format='sec'),
                                                         stoptime=t1 + TimeDelta(5.0, format='sec'))
        self.assertEqual(len(result), 8)

    def test_add_from_redis(self):

        if is_at_katcp_enabled_site():
            self.test_session.add_roach_temperature_from_redis()
            result = self.test_session.get_roach_temperature(Time.now() - TimeDelta(120.0, format='sec'),
                                                             stoptime=Time.now() + TimeDelta(120.0, format='sec'))
            self.assertEqual(len(result), 8)


if __name__ == '__main__':
    unittest.main()
