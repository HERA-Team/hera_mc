#! /usr/bin/env python

import argparse
import hera_mc.mc as mc
import os

default_config_file = os.path.expanduser('~/.hera_mc/mc_config.json')

parser = argparse.ArgumentParser()
parser.add_argument('--config_file', type=str, default=None,
                    help='full path to hera mc_config.json file specifiying '
                         'test_db and mc_db.')
parser.add_argument('--use_test', dest='use_test', action='store_false',
                    help='use test_db rather than mc_db')
parser.set_defaults(use_test=False)
args = parser.parse_args()

if args.config_file is None:
    test_db, mc_db = mc.get_configs(config_file=default_config_file)
else:
    test_db, mc_db = mc.get_configs(config_file=args.config_file)

db_use = mc.DB_declarative(use_test=args.use_test)
db_use.create_tables()
