#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Checks for node over-temperature conditions.
"""
import argparse
from hera_mc import watch_dog


parser = argparse.ArgumentParser()
parser.add_argument('--age', help="Time threshold in hours", default=1.1, type=float)
parser.add_argument('--email', help="E-mails to use (csv-list)", default=None)
args = parser.parse_args()

if args.email is not None:
    args.email = args.email.split(',')
args.age = int(3600 * args.age)  # Convert to seconds.
print(args)

watch_dog.node_verdict(age_out=args.age, To=args.email, testing=False)
