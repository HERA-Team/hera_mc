# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.server_status`.

"""
import unittest

import numpy as np
import datetime
import pytz

from hera_mc import mc
from hera_mc.server_status import ServerStatus


class test_hera_mc(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_db.create_tables()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()
        self.test_db.drop_tables()

    def test_add_server_status(self):
        hostname = 'test_host'
        ip_address = '0.0.0.0'
        server_time = pytz.utc.localize(datetime.datetime.utcnow())
        num_cores = 16
        cpu_load_pct = 20.5
        uptime_days = 31.4
        memory_used_pct = 43.2
        memory_size_gb = 32.
        disk_space_pct = 46.8
        disk_size_gb = 510.4
        network_bandwidth_mbs = 10.4

        expected = ServerStatus(hostname=hostname, mc_time=pytz.utc.localize(datetime.datetime.utcnow()),
                                ip_address=ip_address, system_time=server_time,
                                num_cores=num_cores, cpu_load_pct=cpu_load_pct,
                                uptime_days=uptime_days, memory_used_pct=memory_used_pct,
                                memory_size_gb=memory_size_gb, disk_space_pct=disk_space_pct,
                                disk_size_gb=disk_size_gb,
                                network_bandwidth_mbs=network_bandwidth_mbs)
        print(expected)
        self.test_session.add_server_status(hostname, ip_address, server_time, num_cores,
                                            cpu_load_pct, uptime_days, memory_used_pct,
                                            memory_size_gb, disk_space_pct, disk_size_gb,
                                            network_bandwidth_mbs=network_bandwidth_mbs)
        result = self.test_session.get_server_status(server_time)[0]

        # check that the mc_times are very close
        mc_time_diff = abs(expected.mc_time.astimezone(pytz.utc) - result.mc_time.astimezone(pytz.utc))
        self.assertTrue(mc_time_diff < datetime.timedelta(seconds=0.01))

        # they are close enough. set them equal to test the rest of the objects
        expected.mc_time = result.mc_time.astimezone(pytz.utc)

        self.assertEqual(result, expected)

        self.test_session.add_server_status('test_host2', ip_address, server_time, num_cores,
                                            cpu_load_pct, uptime_days, memory_used_pct,
                                            memory_size_gb, disk_space_pct, disk_size_gb,
                                            network_bandwidth_mbs=network_bandwidth_mbs)

        result_host = self.test_session.get_server_status(server_time, hostname=hostname,
                                                          stoptime=server_time + datetime.timedelta(minutes=2))
        self.assertEqual(len(result_host), 1)
        result_host = result_host[0]
        self.assertEqual(result_host, expected)

        result_mult = self.test_session.get_server_status(server_time,
                                                          stoptime=server_time + datetime.timedelta(minutes=2))

        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_server_status(server_time, hostname='test_host2')[0]
        # mc_times will be different. set them equal so that doesn't control the test
        expected.mc_time = result2.mc_time.astimezone(pytz.utc)
        self.assertNotEqual(result2, expected)


if __name__ == '__main__':
    unittest.main()
