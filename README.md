# hera_mc

This is the main repository for HERA's monitor and control subsystems.
Installation instructions may be found in [INSTALL.md](./INSTALL.md).

# Adding a new table

To add a new table into the M&C database:
0. Invoke 'createdb hera_mc' to make the database if needed.
1. Create a new module under `hera_mc`, basing on e.g. `host_status.py`.
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

# Deleting a table
dropdb hera_mc
