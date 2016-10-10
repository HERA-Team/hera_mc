#! /usr/bin/env python

import argparse
import hera_mc.mc as mc
from sqlalchemy import create_engine
from sqlalchemy.engine import reflection

parser = argparse.ArgumentParser()
parser.add_argument('--config_file', type=str, default=None,
                    help='full path to hera mc_config.json file specifiying '
                         'test_db and mc_db.')
parser.add_argument('--use_test', dest='use_test', action='store_true',
                    help='use test_db rather than mc_db')
parser.set_defaults(use_test=False)
args = parser.parse_args()

if args.config_file is None:
    test_db, mc_db = mc.get_configs(config_file=mc.default_config_file)
else:
    test_db, mc_db = mc.get_configs(config_file=args.config_file)


if args.use_test is True:
    db_name = test_db
else:
    db_name = mc_db

print('creating engine')
this_engine = create_engine(db_name)
print('reflecting engine into inspector')
insp = reflection.Inspector.from_engine(this_engine)

print(db_name)
print(insp.get_table_names())
