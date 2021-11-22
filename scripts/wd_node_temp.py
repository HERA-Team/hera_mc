#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Checks for node over-temperature conditions.
"""
import argparse
from hera_mc import watch_dog


parser = argparse.ArgumentParser("Script for cronjob monitoring node temperatures.")
parser.add_argument(
    "--date", help="Date to use (see cm_utils.get_astropytime)", default="now"
)
parser.add_argument("--time", help="Time to use (  ''  )", default=0.0)
parser.add_argument("--temp", help="Temperature threshold in Celsius", default=45.0)
parser.add_argument("--age", help="Time threshold in days", default=1.0)
parser.add_argument("--email", help="E-mails to use (csv-list)", default=None)
args = parser.parse_args()

if args.email is not None:
    args.email = args.email.split(",")

watch_dog.node_temperature(
    at_date=args.date,
    at_time=args.time,
    temp_threshold=float(args.temp),
    time_threshold=float(args.age),
    To=args.email,
    testing=False,
    session=None,
)
