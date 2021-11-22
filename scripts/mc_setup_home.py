#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Script to setup the mc_config file.
"""
import os
import sys

logname = os.getenv("LOGNAME")
mc_config_path = os.path.expanduser("~/.hera_mc")
if os.path.exists(mc_config_path):
    if os.path.exists(os.path.join(mc_config_path, "mc_config.json")):
        print(
            "~/.hera_mc/mc_config.json already exists -- renaming to mc_config.json.bak"
        )
        os.rename(
            os.path.join(mc_config_path, "mc_config.json"),
            os.path.join(mc_config_path, "mc_config.json.bak"),
        )
else:
    print("Creating {}".format(mc_config_path))
    os.mkdir(mc_config_path)

cwd = os.getcwd()
h, t = os.path.split(cwd)
if t != "hera_cm_db_updates":
    print("You need to be in the hera_cm_db_updates directory to run this.")
    sys.exit()
assumed_hera_cm_db_updates_location = cwd
mc_config = """{{
    "default_db_name": "hera_mc_sqlite",
    "databases": {{
        "hera_mc": {{
            "url": "postgresql://{}@localhost/hera_mc",
            "mode": "production"
            }},
        "testing": {{
            "url": "postgresql://{}@localhost/hera_mc_test",
            "mode": "testing"
            }},
        "hera_mc_sqlite": {{
            "url": "sqlite:///{}/hera_mc.db",
            "mode": "production"
            }}
        }},
    "cm_csv_path": "{}"
}}
""".format(
    logname,
    logname,
    assumed_hera_cm_db_updates_location,
    assumed_hera_cm_db_updates_location,
)

with open(os.path.join(mc_config_path, "mc_config.json"), "w") as f:
    f.write(mc_config)

print("\nThis assumes your login name is\n\t{}".format(logname))
print(
    "and that hera_cm_db_updates is installed at\n\t{}".format(
        assumed_hera_cm_db_updates_location
    )
)
print(
    "\nIf either of these are incorrect, please edit {}".format(
        os.path.join(mc_config_path, "mc_config.json")
    )
)
