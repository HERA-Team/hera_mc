#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""script to write M&C records to a CSV file

"""
from __future__ import absolute_import, division, print_function

import sys
import six
from astropy.time import Time, TimeDelta

from hera_mc import mc, cm_utils

valid_tables = {'hera_obs': {'method': 'get_obs_by_time'},
                'rtp_server_status': {'method': 'get_rtp_server_status',
                                      'filter_column': 'hostname',
                                      'arg_name': 'hostname'},
                'lib_server_status': {'method': 'get_librarian_server_status',
                                      'filter_column': 'hostname',
                                      'arg_name': 'hostname'},
                'subsystem_error': {'method': 'get_subsystem_error'},
                'lib_status': {'method': 'get_lib_status'},
                'lib_raid_status': {'method': 'get_lib_raid_status'},
                'lib_raid_errors': {'method': 'get_lib_raid_error',
                                    'filter_column': 'hostname',
                                    'arg_name': 'hostname'},
                'lib_remote_status': {'method': 'get_lib_remote_status',
                                      'filter_column': 'remote_name',
                                      'arg_name': 'remote_name'},
                'lib_files': {'method': 'get_lib_files',
                              'filter_column': 'obsid',
                              'arg_name': 'obsid'},
                'rtp_status': {'method': 'get_rtp_status'},
                'rtp_process_event': {'method': 'get_rtp_process_event',
                                      'filter_column': 'obsid',
                                      'arg_name': 'obsid'},
                'rtp_process_record': {'method': 'get_rtp_process_record',
                                       'filter_column': 'obsid',
                                       'arg_name': 'obsid'},
                'rtp_task_resource_record': {'method': 'get_rtp_task_resource_record',
                                             'filter_column': 'obsid',
                                             'arg_name': 'obsid'},
                'weather_data': {'method': 'get_weather_data',
                                 'filter_column': 'variable',
                                 'arg_name': 'variable'},
                'node_sensor': {'method': 'get_node_sensor_readings',
                                'filter_column': 'nodeID',
                                'arg_name': 'node'},
                'node_power_status': {'method': 'get_node_power_status',
                                      'filter_column': 'nodeID',
                                      'arg_name': 'node'},
                'node_power_command': {'method': 'get_node_power_command',
                                       'filter_column': 'nodeID',
                                       'arg_name': 'node'},
                'correlator_control_state': {'method': 'get_correlator_control_state',
                                             'filter_column': 'state_type',
                                             'arg_name': 'state_type'},
                'correlator_control_command': {'method': 'get_correlator_control_command',
                                               'filter_column': 'command',
                                               'arg_name': 'command'},
                'correlator_take_data_arguments': {'method': 'get_correlator_take_data_arguments'}}

if __name__ == '__main__':
    parser = mc.get_mc_argument_parser()
    parser.description = """Write M&C records to a CSV file"""
    parser.add_argument('table', help="table to get info from")

    list_of_filter_args = []
    for table, table_dict in six.iteritems(valid_tables):
        if 'arg_name' in table_dict:
            arg_name = table_dict['arg_name']
            if arg_name not in list_of_filter_args:
                list_of_filter_args.append(arg_name)
                parser.add_argument('--' + arg_name, help="only include the specified " + arg_name,
                                    default=None)

    parser.add_argument('--filename', help="filename to save data to")
    parser.add_argument('--start-date', dest='start_date', help="Start date YYYY/MM/DD", default=None)
    parser.add_argument('--start-time', dest='start_time', help="Start time in HH:MM", default='17:00')
    parser.add_argument('--stop-date', dest='stop_date', help="Stop date YYYY/MM/DD", default=None)
    parser.add_argument('--stop-time', dest='stop_time', help="Stop time in HH:MM", default='7:00')
    parser.add_argument('-l', '--last-period', dest='last_period', default=None,
                        help="Time period from present for data (in minutes).  If present ignores start/stop.")

    args = parser.parse_args()

    if args.last_period:
        stop_time = Time.now()
        start_time = stop_time - TimeDelta(float(args.last_period) / (60.0 * 24.0), format='jd')
    else:
        start_time = cm_utils.get_astropytime(args.start_date, args.start_time)
        stop_time = cm_utils.get_astropytime(args.stop_date, args.stop_time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    relevant_arg_name = valid_tables[args.table]['arg_name']
    for arg in list_of_filter_args:
        if getattr(args, arg) is not None and arg != relevant_arg_name:
            print('{arg} is specified but does not apply to table {table}, '
                  'so it will be ignored.'.format(arg=arg, table=args.table))

    method_kwargs = {'starttime': start_time, 'stoptime': stop_time,
                     valid_tables[args.table]['filter_column']: getattr(args, valid_tables[args.table]['arg_name']),
                     'write_to_file': True, 'filename': args.filename}
    getattr(session, valid_tables[args.table]['method'])(**method_kwargs)
