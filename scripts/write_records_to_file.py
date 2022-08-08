#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""script to write M&C records to a CSV file

"""

from astropy.time import Time, TimeDelta

from hera_mc import cm_utils, mc

valid_tables = {
    "hera_obs": {
        "method": "get_obs_by_time",
        "filter_column": ["tag"],
        "arg_name": ["tag"],
    },
    "rtp_server_status": {
        "method": "get_rtp_server_status",
        "filter_column": ["hostname"],
        "arg_name": ["hostname"],
    },
    "lib_server_status": {
        "method": "get_librarian_server_status",
        "filter_column": ["hostname"],
        "arg_name": ["hostname"],
    },
    "subsystem_error": {
        "method": "get_subsystem_error",
        "filter_column": ["subsystem"],
        "arg_name": ["subsystem"],
    },
    "daemon_status": {
        "method": "get_daemon_status",
        "filter_column": ["name"],
        "arg_name": ["daemon_name"],
    },
    "lib_status": {"method": "get_lib_status"},
    "lib_raid_status": {
        "method": "get_lib_raid_status",
        "filter_column": ["hostname"],
        "arg_name": ["hostname"],
    },
    "lib_raid_errors": {
        "method": "get_lib_raid_error",
        "filter_column": ["hostname"],
        "arg_name": ["hostname"],
    },
    "lib_remote_status": {
        "method": "get_lib_remote_status",
        "filter_column": ["remote_name"],
        "arg_name": ["remote_name"],
    },
    "lib_files": {
        "method": "get_lib_files",
        "filter_column": ["obsid"],
        "arg_name": ["obsid"],
    },
    "rtp_process_event": {
        "method": "get_rtp_process_event",
        "filter_column": ["obsid"],
        "arg_name": ["obsid"],
    },
    "rtp_process_record": {
        "method": "get_rtp_process_record",
        "filter_column": ["obsid"],
        "arg_name": ["obsid"],
    },
    "rtp_task_jobid": {
        "method": "get_rtp_task_jobid",
        "filter_column": ["obsid", "task_name"],
        "arg_name": ["obsid", "task_name"],
    },
    "rtp_task_resource_record": {
        "method": "get_rtp_task_resource_record",
        "filter_column": ["obsid", "task_name"],
        "arg_name": ["obsid", "task_name"],
    },
    "rtp_task_multiple_jobid": {
        "method": "get_rtp_task_multiple_jobid",
        "filter_column": ["obsid_start", "task_name"],
        "arg_name": ["obsid_start", "task_name"],
    },
    "rtp_task_multiple_resource_record": {
        "method": "get_rtp_task_multiple_resource_record",
        "filter_column": ["obsid_start", "task_name"],
        "arg_name": ["obsid_start", "task_name"],
    },
    "rtp_launch_record": {"method": "get_rtp_launch_record_by_time"},
    "weather_data": {
        "method": "get_weather_data",
        "filter_column": ["variable"],
        "arg_name": ["variable"],
    },
    "node_sensor": {
        "method": "get_node_sensor_readings",
        "filter_column": ["nodeID"],
        "arg_name": ["node"],
    },
    "node_power_status": {
        "method": "get_node_power_status",
        "filter_column": ["nodeID"],
        "arg_name": ["node"],
    },
    "node_power_command": {
        "method": "get_node_power_command",
        "filter_column": ["nodeID"],
        "arg_name": ["node"],
    },
    "node_white_rabbit_status": {
        "method": "get_node_white_rabbit_status",
        "filter_column": ["nodeID"],
        "arg_name": ["node"],
    },
    "array_signal_source": {
        "method": "get_array_signal_source",
        "filter_column": ["source"],
        "arg_name": ["source"],
    },
    "correlator_component_event_time": {
        "method": "get_correlator_component_event_time",
        "filter_column": ["component", "event"],
        "arg_name": ["component", "event"],
    },
    "correlator_config_params": {
        "method": "get_correlator_config_params",
        "filter_column": ["config_hash", "parameter"],
        "arg_name": ["config_hash", "parameter"],
    },
    "correlator_config_active_snap": {
        "method": "get_correlator_config_active_snaps",
        "filter_column": ["config_hash"],
        "arg_name": ["config_hash"],
    },
    "correlator_config_input_index": {
        "method": "get_correlator_config_active_snaps",
        "filter_column": ["config_hash", "correlator_index"],
        "arg_name": ["config_hash", "correlator_index"],
    },
    "correlator_config_phase_switch_index": {
        "method": "get_correlator_config_phase_switch_index",
        "filter_column": ["config_hash"],
        "arg_name": ["config_hash"],
    },
    "correlator_config_status": {
        "method": "get_correlator_config_status",
        "filter_column": ["config_hash"],
        "arg_name": ["config_hash"],
    },
    "correlator_software_version": {
        "method": "get_correlator_software_versions",
        "filter_column": ["package"],
        "arg_name": ["package"],
    },
    "snap_config_version": {"method": "get_snap_config_version"},
    "snap_status": {
        "method": "get_snap_status",
        "filter_column": ["nodeID"],
        "arg_name": ["node"],
    },
    "antenna_status": {
        "method": "get_antenna_status",
        "filter_column": ["antenna_number"],
        "arg_name": ["antenna_number"],
    },
    "ant_metrics": {
        "method": "get_ant_metric",
        "filter_column": ["ant", "pol", "metric", "obsid"],
        "arg_name": ["ant", "pol", "metric", "obsid"],
    },
    "array_metrics": {
        "method": "get_array_metric",
        "filter_column": ["metric", "obsid"],
        "arg_name": ["metric", "obsid"],
    },
    "hera_autos": {
        "method": "get_autocorrelation",
        "filter_column": ["antenna_number"],
        "arg_name": ["antenna_number"],
    },
}

# get commands without write_to_file options:
#   get_correlator_config_file, get_metric_desc

if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.description = """Write M&C records to a CSV file"""
    parser.add_argument("table", help="table to get info from")

    filter_args = {}
    for table, table_dict in valid_tables.items():
        if "arg_name" in table_dict:
            for arg_name in table_dict["arg_name"]:
                if arg_name not in filter_args:
                    filter_args[arg_name] = [table]
                else:
                    filter_args[arg_name].append(table)

    for arg_name, table_list in filter_args.items():
        parser.add_argument(
            "--" + arg_name,
            help=f"only include the specified {arg_name} (for tables {table_list}).",
            default=None,
        )

    parser.add_argument("--filename", help="filename to save data to")
    parser.add_argument(
        "--start-date", dest="start_date", help="Start date YYYY/MM/DD", default=None
    )
    parser.add_argument(
        "--start-time", dest="start_time", help="Start time in HH:MM", default="17:00"
    )
    parser.add_argument(
        "--stop-date", dest="stop_date", help="Stop date YYYY/MM/DD", default=None
    )
    parser.add_argument(
        "--stop-time", dest="stop_time", help="Stop time in HH:MM", default="7:00"
    )
    parser.add_argument(
        "-l",
        "--last-period",
        dest="last_period",
        default=None,
        help="Time period from present for data (in minutes). "
        "If present ignores start/stop.",
    )

    args = parser.parse_args()

    if args.last_period:
        stop_time = Time.now()
        start_time = stop_time - TimeDelta(
            float(args.last_period) / (60.0 * 24.0), format="jd"
        )
    else:
        start_time = cm_utils.get_astropytime(args.start_date, args.start_time)
        stop_time = cm_utils.get_astropytime(args.stop_date, args.stop_time)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()

    for arg_name, table_list in filter_args.items():
        if getattr(args, arg_name) is not None and table not in table_list:
            print(
                f"{arg_name} is specified but does not apply to table {table}, "
                "so it will be ignored."
            )

    method_kwargs = {
        "starttime": start_time,
        "stoptime": stop_time,
        "write_to_file": True,
        "filename": args.filename,
    }
    for index, col in enumerate(valid_tables[args.table]["filter_column"]):
        method_kwargs[col] = getattr(args, valid_tables[args.table]["arg_name"][index])

    getattr(session, valid_tables[args.table]["method"])(**method_kwargs)
