# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.server_status`.

"""
import unittest

import numpy as np
import datetime

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
        server_time = datetime.datetime.now()
        num_cores = 16
        cpu_load_pct = 20.5
        uptime_days = 31.4
        memory_used_pct = 43.2
        memory_size_gb = 32.
        disk_space_pct = 46.8
        disk_size_gb = 510.4
        network_bandwidth_mbs = 10.4

        expected = [ServerStatus(hostname=hostname, mc_time=datetime.datetime.now(),
                                 ip_address=ip_address, system_time=server_time,
                                 num_cores=num_cores, cpu_load_pct=cpu_load_pct,
                                 uptime_days=uptime_days, memory_used_pct=memory_used_pct,
                                 memory_size_gb=memory_size_gb, disk_space_pct=disk_space_pct,
                                 disk_size_gb=disk_size_gb, network_bandwidth_mbs=network_bandwidth_mbs)]

        self.test_session.add_server_status(hostname, ip_address, server_time, num_cores,
                                            cpu_load_pct, uptime_days, memory_used_pct, memory_size_gb,
                                            disk_space_pct, disk_size_gb,
                                            network_bandwidth_mbs=network_bandwidth_mbs)
        result = self.test_session.get_server_status(server_time - datetime.timedelta(minutes=15))
        result_host = self.test_session.get_server_status(server_time - datetime.timedelta(minutes=15),
                                                          hostname=hostname)

        self.assertEqual(result, expected)
        self.assertEqual(result_host, expected)

if __name__ == '__main__':
    unittest.main()
