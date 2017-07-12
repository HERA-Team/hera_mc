# hera_mc

[![Build Status](https://travis-ci.org/HERA-Team/hera_mc.svg?branch=master)](https://travis-ci.org/HERA-Team/hera_mc)
[![Coverage Status](https://coveralls.io/repos/github/HERA-Team/hera_mc/badge.svg?branch=master)](https://coveralls.io/github/HERA-Team/hera_mc?branch=master)

This is the main repository for HERA's monitor and control subsystems.
Installation instructions may be found in [INSTALL.md](./INSTALL.md).

# Adding a new table

To add a new table into the M&C database:
0. Invoke 'createdb hera_mc' to make the database if needed.
1. Create a new module under `hera_mc`, basing on e.g. `observation.py`.
2. Add `from . import my_new_module` line in `__init__.py`.
3. Rerun `python setup.py install` to install the new module(s).
4. Optionally, update the schema of the production database:
  1. Edit `~/.hera_mc/mc_config.json` to change the "mode" of the
	 production database to "testing".
  2. Run `mc_initialize_db.py`
  3. Edit `~/.hera_mc/mc_config.json` to change the "mode" of the
	 production database back to "production".
  4. If you then run `psql` and connect to the production database (usually
     `hera_mc`), you should see the new table.

# Deleting a database
dropdb hera_mc

# Running psql on qmaster

This runs under the HERA conda environment on qmaster.  

To check environments: `conda info --envs`

To change environments:  `source activate HERA`

To run psql:  `psql -U hera -h qmaster hera_mc`
