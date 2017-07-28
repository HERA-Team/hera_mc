# hera_mc

[![Build Status](https://travis-ci.org/HERA-Team/hera_mc.svg?branch=master)](https://travis-ci.org/HERA-Team/hera_mc)
[![Coverage Status](https://coveralls.io/repos/github/HERA-Team/hera_mc/badge.svg?branch=master)](https://coveralls.io/github/HERA-Team/hera_mc?branch=master)

This is the main repository for HERA's monitor and control subsystems.
Installation instructions may be found in [INSTALL.md](./INSTALL.md).

# Adding a new table

To add a new table into the M&C database:

First, ensure that the database is configured correctly by running `alembic upgrade head`. If this fails, refer to the direction in [INSTALL.md](./INSTALL.md).

Be sure to do all your work on a branch off of master.

1. Create a new module under `hera_mc`, basing on e.g. `subsystem_error.py` or `observation.py`.
2. Add `from . import my_new_module` line in `__init__.py`.
3. Add methods to interact with your new table. This is most commonly done in `mc_session.py`, and there are many examples there to refer to.
4. Add testing code to cover these methods.
5. Run `alembic revision --autogenerate -m 'version description'` to create a new alembic revision file that will reflect the changes to the database schema you just introduced. Inspect the resulting file carefully -- alembic's autogeneration is very clever but it's certainly not perfect. It tends to make more mistakes with table or column alterations than with table creations.
4. Run `alembic upgrade head` to apply your schema changes. At this point it's a very good idea to inspect the database table (using the psql command line) to make sure the right thing happened. It's also a very good idea to run `alembic downgrade -1` to back up to before your revision and check that the database looks right (of course you then need to re-run the upgrade command to get back to where you meant to be.)
5. Run `nosetests` to check that all the tests pass.
6. When you're satisified that everything works as expected, create a pull request on github to ask for a code review and to get your changes integrated into master.
7. Once the changes have been incorporated into master, you can log onto site, pull the master branch and run `alembic upgrade head` to update the onsite database to the new schema.

# Deleting all the tables in a database (in psql shell)
```
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

# Deleting a database
dropdb hera_mc

# Running psql on qmaster

This runs under the HERA conda environment on qmaster.  

To check environments: `conda info --envs`

To change environments:  `source activate HERA`

To run psql:  `psql -U hera -h qmaster hera_mc`
