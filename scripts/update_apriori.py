#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to update the apriori antenna status.
"""

from hera_mc import mc, cm_utils, cm_partconnect


if __name__ == "__main__":
    parser = mc.get_mc_argument_parser()
    parser.add_argument("-p", "--hpn", help="HERA part number")
    parser.add_argument(
        "-s",
        "--status",
        help="New apriori status.",
        choices=[
            "dish_maintenance",
            "dish_ok",
            "RF_maintenance",
            "RF_ok",
            "digital_maintenance",
            "digital_ok",
            "calibration_maintenance",
            "calibration_ok",
            "calibration_triage",
        ],
    )
    cm_utils.add_date_time_args(parser)
    args = parser.parse_args()

    # Pre-process some args
    at_date = cm_utils.get_astropytime(args.date, args.time, args.format)

    db = mc.connect_to_mc_db(args)
    session = db.sessionmaker()
    cm_partconnect.update_apriori_antenna(
        antenna=args.hpn,
        status=args.status,
        start_gpstime=at_date.gps,
        stop_gpstime=None,
        session=session,
    )
