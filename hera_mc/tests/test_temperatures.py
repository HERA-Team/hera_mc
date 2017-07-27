# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.temperatures`.

"""
from __future__ import absolute_import, division, print_function

import unittest

from math import floor
import numpy as np
from astropy.time import Time, TimeDelta
from hera_mc import mc, temperatures
from hera_mc.tests import TestHERAMC


class TestTemperatures(TestHERAMC):

    def test_add_paper_temps(self):
        t1 = Time('2016-01-10 01:15:23', scale='utc')
        t2 = t1 + TimeDelta(120.0, format='sec')

        temp_list = (np.arange(28) + 300.).tolist()
        temp2_list = (np.arange(28) + 310.).tolist()
        temp_colnames = ['balun_east', 'cable_east',
                         'balun_west', 'cable_west',
                         'rcvr_1a', 'rcvr_1b', 'rcvr_2a', 'rcvr_2b',
                         'rcvr_3a', 'rcvr_3b', 'rcvr_4a', 'rcvr_4b',
                         'rcvr_5a', 'rcvr_5b', 'rcvr_6a', 'rcvr_6b',
                         'rcvr_7a', 'rcvr_7b', 'rcvr_8a', 'rcvr_8b']
        temp_indices = (np.array([1, 2, 3, 4, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18,
                                  19, 20, 22, 23, 24, 25]) - 1).tolist()

        temp_values = [temp_list[i] for i in temp_indices]
        temp2_values = [temp2_list[i] for i in temp_indices]

        temp_dict = dict(zip(temp_colnames, temp_values))
        temp2_dict = dict(zip(temp_colnames, temp2_values))

        self.test_session.add_paper_temps(t1, temp_list)
        self.test_session.add_paper_temps(t2, temp2_list)

        expected = [temperatures.PaperTemperatures(time=int(floor(t1.gps)), **temp_dict)]
        result = self.test_session.get_paper_temps(t1 - TimeDelta(3.0, format='sec'))
        self.assertEqual(len(result), len(expected))
        for i in range(0, len(result)):
            self.assertTrue(result[i].isclose(expected[i]))

        result = self.test_session.get_paper_temps(t1 + TimeDelta(200.0, format='sec'))
        self.assertEqual(result, [])

        expected2 = [temperatures.PaperTemperatures(time=int(floor(t1.gps)),
                                                    **temp_dict),
                     temperatures.PaperTemperatures(time=int(floor(t2.gps)),
                                                    **temp2_dict)]
        result = self.test_session.get_paper_temps(t1 - TimeDelta(3.0, format='sec'),
                                                   stoptime=t2 + TimeDelta(1.0, format='sec'))
        self.assertEqual(len(result), len(expected2))
        for i in range(0, len(result)):
            self.assertTrue(result[i].isclose(expected2[i]))


if __name__ == '__main__':
    unittest.main()
