# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Testing for `hera_mc.rtp`.

"""
import unittest
import numpy as np
from math import floor
from astropy.time import Time, TimeDelta
from sqlalchemy.exc import NoForeignKeysError

from hera_mc import mc
from hera_mc.rtp import RTPStatus, RTPProcessEvent, RTPProcessRecord


class test_hera_mc(unittest.TestCase):

    def setUp(self):
        self.test_db = mc.connect_to_mc_testing_db()
        self.test_db.create_tables()
        self.test_conn = self.test_db.engine.connect()
        self.test_trans = self.test_conn.begin()
        self.test_session = mc.MCSession(bind=self.test_conn)

        time = Time.now()
        obsid = floor(time.gps)
        self.observation_names = ['starttime', 'stoptime', 'obsid']
        self.observation_values = [time, time + TimeDelta(10 * 60, format='sec'),
                                   obsid]
        self.observation_columns = dict(zip(self.observation_names,
                                            self.observation_values))
        self.test_session.add_obs(*self.observation_values[0:2],
                                  obsid=self.observation_columns['obsid'])
        obs_result = self.test_session.get_obs()
        self.assertTrue(len(obs_result), 1)

        self.status_names = ['time', 'status', 'event_min_elapsed',
                             'num_processes', 'restart_hours_elapsed']
        self.status_values = [time, 'happy', 3.6, 8, 10.2]
        self.status_columns = dict(zip(self.status_names, self.status_values))

        self.event_names = ['time', 'obsid', 'event']
        self.event_values = [time, obsid, 'queued']
        self.event_columns = dict(zip(self.event_names, self.event_values))

        self.record_names = ['time', 'obsid', 'pipeline_list', 'git_version', 'git_hash']
        self.record_values = [time, obsid, 'sample_pipe', 'v0.0.1', 'lskdjf24l']
        self.record_columns = dict(zip(self.record_names, self.record_values))

    def tearDown(self):
        self.test_trans.rollback()
        self.test_conn.close()
        self.test_db.drop_tables()

    def test_add_rtp_status(self):
        self.test_session.add_rtp_status(*self.status_values)

        exp_columns = self.status_columns.copy()
        exp_columns['time'] = exp_columns['time'].gps
        expected = RTPStatus(**exp_columns)

        result = self.test_session.get_rtp_status(self.status_columns['time'])[0]

        self.assertEqual(result, expected)

        new_status_time = self.status_columns['time'] + TimeDelta(5 * 60, format='sec')
        new_status = 'unhappy'
        self.test_session.add_rtp_status(new_status_time, new_status,
                                         self.status_columns['event_min_elapsed'] + 5,
                                         self.status_columns['num_processes'],
                                         self.status_columns['restart_hours_elapsed'] + 5. / 60.)

        result_mult = self.test_session.get_rtp_status(self.status_columns['time'],
                                                       stoptime=new_status_time)
        self.assertEqual(len(result_mult), 2)

        result2 = self.test_session.get_rtp_status(new_status_time)[0]
        self.assertFalse(result2 == expected)

    def test_errors_rtp_status(self):
        self.assertRaises(ValueError, self.test_session.add_rtp_status, 'foo',
                          *self.status_values[1:])

        self.test_session.add_rtp_status(*self.status_values)
        self.assertRaises(ValueError, self.test_session.get_rtp_status, 'unhappy')
        self.assertRaises(ValueError, self.test_session.get_rtp_status,
                          self.status_columns['time'], stoptime='unhappy')

    def test_add_rtp_process_event(self):
        # raise error if try to add process event with unmatched obsid
        # self.assertRaises(NoForeignKeysError, self.test_session.add_rtp_process_event,
        #                   self.event_values[0], self.event_values[1] + 2,
        #                   self.event_values[2])

        self.test_session.add_rtp_process_event(*self.event_values)

        exp_columns = self.event_columns.copy()
        exp_columns['time'] = exp_columns['time'].gps
        expected = RTPProcessEvent(**exp_columns)

        result = self.test_session.get_rtp_process_event(self.event_columns['time'])
        self.assertEqual(len(result), 1)
        result = result[0]
        result_obsid = self.test_session.get_rtp_process_event(self.event_columns['time'],
                                                               obsid=self.event_columns['obsid'])[0]
        self.assertEqual(result, expected)

        new_obsid_time = self.event_columns['time'] + TimeDelta(3 * 60, format='sec')
        new_obsid = self.event_columns['obsid'] + 10
        self.test_session.add_obs(Time(new_obsid_time),
                                  Time(new_obsid_time + TimeDelta(10 * 60, format='sec')),
                                  obsid=new_obsid)
        obs_result = self.test_session.get_obs(obsid=new_obsid)
        self.assertEqual(obs_result[0].obsid, new_obsid)

        self.test_session.add_rtp_process_event(new_obsid_time,
                                                new_obsid,
                                                self.event_columns['event'])
        result_obsid = self.test_session.get_rtp_process_event(self.event_columns['time'],
                                                               obsid=self.event_columns['obsid'])[0]
        self.assertEqual(result_obsid, expected)

        new_event_time = self.event_columns['time'] + TimeDelta(5 * 60, format='sec')
        new_event = 'started'
        self.test_session.add_rtp_process_event(new_event_time,
                                                self.event_columns['obsid'],
                                                new_event)

        result_mult = self.test_session.get_rtp_process_event(self.event_columns['time'],
                                                              stoptime=new_event_time)
        self.assertEqual(len(result_mult), 3)

        result_mult_obsid = self.test_session.get_rtp_process_event(self.event_columns['time'],
                                                                    stoptime=new_event_time,
                                                                    obsid=self.event_columns['obsid'])
        self.assertEqual(len(result_mult_obsid), 2)

        result_new_obsid = self.test_session.get_rtp_process_event(self.event_columns['time'],
                                                                   obsid=new_obsid)[0]

        self.assertFalse(result_new_obsid == expected)

    def test_errors_rtp_process_event(self):
        self.assertRaises(ValueError, self.test_session.add_rtp_process_event, 'foo',
                          *self.event_values[1:])

        self.test_session.add_rtp_process_event(*self.event_values)
        self.assertRaises(ValueError, self.test_session.get_rtp_process_event, 'foo')
        self.assertRaises(ValueError, self.test_session.get_rtp_process_event,
                          self.event_columns['time'], stoptime='bar')

        # self.assertRaises(ValueError, self.test_session.add_rtp_process_event,
        #                   self.event_columns['time'], self.event_columns['obsid'],
        #                   'foo')

    def test_classes_not_equal(self):
        self.test_session.add_rtp_process_event(*self.event_values)
        self.test_session.add_rtp_status(*self.status_values)

        status_result = self.test_session.get_rtp_status(self.status_columns['time'])[0]
        event_result = self.test_session.get_rtp_process_event(self.event_columns['time'])
        self.assertFalse(status_result == event_result)

    def test_add_rtp_process_record(self):
        # raise error if try to add process event with unmatched obsid
        # self.assertRaises(NoForeignKeysError, self.test_session.add_rtp_process_event,
        #                   self.record_values[0], self.record_values[1] + 2,
        #                   self.record_values[2:5])

        self.test_session.add_rtp_process_record(*self.record_values)

        exp_columns = self.record_columns.copy()
        exp_columns['time'] = exp_columns['time'].gps
        expected = RTPProcessRecord(**exp_columns)

        result = self.test_session.get_rtp_process_record(self.record_columns['time'])
        self.assertEqual(len(result), 1)
        result = result[0]
        result_obsid = self.test_session.get_rtp_process_record(self.record_columns['time'],
                                                                obsid=self.record_columns['obsid'])[0]
        self.assertEqual(result, expected)

        new_obsid_time = self.record_columns['time'] + TimeDelta(3 * 60, format='sec')
        new_obsid = self.record_columns['obsid'] + 10
        self.test_session.add_obs(Time(new_obsid_time),
                                  Time(new_obsid_time + TimeDelta(10 * 60, format='sec')),
                                  obsid=new_obsid)
        obs_result = self.test_session.get_obs(obsid=new_obsid)
        self.assertEqual(obs_result[0].obsid, new_obsid)

        self.test_session.add_rtp_process_record(new_obsid_time,
                                                 new_obsid,
                                                 *self.record_values[2:5])
        result_obsid = self.test_session.get_rtp_process_record(self.record_columns['time'],
                                                                obsid=self.record_columns['obsid'])[0]
        self.assertEqual(result_obsid, expected)

        new_record_time = self.record_columns['time'] + TimeDelta(5 * 60, format='sec')
        new_pipeline = 'new_pipe'
        self.test_session.add_rtp_process_record(new_record_time,
                                                 self.record_columns['obsid'],
                                                 new_pipeline, *self.record_values[3:5])

        result_mult = self.test_session.get_rtp_process_record(self.record_columns['time'],
                                                               stoptime=new_record_time)
        self.assertEqual(len(result_mult), 3)

        result_mult_obsid = self.test_session.get_rtp_process_record(self.record_columns['time'],
                                                                     stoptime=new_record_time,
                                                                     obsid=self.record_columns['obsid'])
        self.assertEqual(len(result_mult_obsid), 2)

        result_new_obsid = self.test_session.get_rtp_process_record(self.record_columns['time'],
                                                                    obsid=new_obsid)[0]

        self.assertFalse(result_new_obsid == expected)

    def test_errors_rtp_process_record(self):
        self.assertRaises(ValueError, self.test_session.add_rtp_process_record, 'foo',
                          *self.status_values[1:])

        self.test_session.add_rtp_process_record(*self.record_values)
        self.assertRaises(ValueError, self.test_session.get_rtp_process_record, 'foo')
        self.assertRaises(ValueError, self.test_session.get_rtp_process_record,
                          self.record_columns['time'], stoptime='bar')


if __name__ == '__main__':
    unittest.main()
