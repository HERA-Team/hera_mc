# hera_mc

![](https://github.com/HERA-Team/hera_mc/workflows/Run%20Tests/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/HERA-Team/hera_mc/branch/master/graph/badge.svg)](https://codecov.io/gh/HERA-Team/hera_mc)

This is the main repository for HERA's monitor and control subsystems.
Installation instructions may be found in [INSTALL.md](./INSTALL.md).

# CM-only users
*Note:  if you are only using hera_mc to locally use configuration management (cm) info via sqlite, you may ignore most of this.
        if this is the case, follow the simplified instructions in INSTALL.md*



# Adding a new table

To add a new table into the M&C database:

First, ensure that the database is configured correctly by running `alembic upgrade head`. If this fails, refer to the direction in [INSTALL.md](./INSTALL.md).

Be sure to do all your work on a branch off of master.

1. Create a new module under `hera_mc`, basing on e.g. `subsystem_error.py` or `observation.py`.
2. Add `from . import my_new_module` line in `__init__.py`.
3. Add methods to interact with your new table. This is most commonly done in
`mc_session.py`, and there are many examples there to refer to.
4. Add testing code to cover these methods. -- Be sure to `pip install .` before
the next step (unless you've done a developer install: `pip install -e .`).
5. Run `alembic revision --autogenerate -m 'version description'` to create a
new alembic revision file that will reflect the changes to the database schema
you just introduced. Inspect the resulting file carefully -- alembic's
autogeneration is very clever but it's certainly not perfect. It tends to make
more mistakes with table or column alterations than with table creations. Also
be sure to remove any dropped tables in the upgrade section (and corresponding
  table creation commands in the downgrade portion) -- we have some old tables
  that we no longer use but don't want to drop on site.
6. Run `alembic upgrade head` to apply your schema changes -- be sure to
`pip install .` if you didn't do a developer install. At this point it's a very
good idea to inspect the database table (using the psql command line) to make
sure the right thing happened. It's also a very good idea to run
`alembic downgrade -1` to back up to before your revision and check that the
database looks right (of course you then need to re-run the upgrade command to
  get back to where you meant to be.)
7. Run `pytest` to check that all the tests pass.
8. git add the alembic/version that was created and commit your work.
9. When you're satisfied that everything works as expected, add a description
of your new table to the documentation in docs/mc_definition.tex.
10. Create a pull request on github to ask for a code review and to get your
changes integrated into master.
11. Once the changes have been incorporated into master, you can log onto site,
pull the master branch and run `alembic upgrade head` to update the onsite
database to the new schema.
12. Pull and reinstall in *all* of the following machines & environments
(this is a critical step!):

  - qmaster machine
    - `HERA` conda environment
    - `RTP` conda environment
    - `HERA_py2` conda environment
  - hera-corr-head machine
    - `hera3` conda environment

13. Restart the following daemons across the hera correletor computer cluster.
This is generally done with `systemctl restart <daemon_name>.service`. Some
machines use upstart instead of systemd, as marked below. In those cases, use
`initctl restart <daemon_name>`.

  - qmaster machine
    - `hera-corr-status` daemon
    - `hera-node-status` daemon
    - `hera-server-status` daemon
    - `mc-listen-to-corr-logger` daemon
    - `mc-monitor-daemons` daemon
  - pot1 machine (upstart)
    - `hera-server-status` daemon
  - pot6 machine
    - `hera-server-status` daemon
  - pot7 machine (upstart)
    - `hera-server-status` daemon
  - pot8 machine (upstart)
    - `hera-server-status` daemon
  - still[1-4] machines (upstart)
    - `hera-server-status` daemon
  - gpu[1-8] machines (upstart)
    - `hera-server-status` daemon
  - bigmem[1-2] machines (upstart)
    - `hera-server-status` daemon

# Deleting all the tables in a database (in psql shell)
This can be useful to do on your local machine if your database is in a weird state. Never do this on site!!!
```
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```
If you get an error like `no schema has been selected to create in...` it means that you need to fix permissions like this:
```
grant usage on schema public to public;
grant create on schema public to public;
```

# Deleting a database
This can be useful to do on your local machine if your database is in a weird state. Never do this on site!!!
`dropdb hera_mc`

# Using alembic for the first time with an existing (non-empty) database
If you already have a database filled out with tables but have never run alembic before, you have two choices to start using alembic:

Option 1) Drop all the tables (if you don't care about the data in the database this is easiest, see instructions above) and then run `alembic upgrade head`.

Option 2) identify which alembic version your database schema corresponds to and add a new table to your database called `alembic_version` with one column called 'version_num'. Fill this table with one row with the alembic version number that corresponds to your schema version to tell alembic where to start trying to upgrade from. Then run `alembic upgrade head`.

# Running psql on qmaster

This runs under the HERA conda environment on qmaster.  

To check environments: `conda info --envs`

To change environments:  `source activate HERA`

To run psql:  `psql -U hera -h qmaster hera_mc`

# Restoring a database backup

We are now regularly backing up the database to the Librarian and copying it to NRAO. The database backup files can be found by searching for them on the librarian using `obsid-is-null`. The files are named like `maint.YYYYMMDD.karoo.mandc.dbbackup.pgdump`.

Once you've downloaded the files, you can create the database (using postgres) like this:

`pg_restore -cCOx  -d hera_mc  maint.20180213.karoo.mandc.dbbackup.pgdump`

# Adding new features and testing

`hera_mc` uses redis during testing to check that values read from redis in the live version can be correctly added to the databases and retrieved again. When adding new features which require data being read from redis, or through any hera correlator code, a new redis.rdb file must be created on `redishost` on site which contains an example of the new data and added to the repository by overwriting the existing redis.rdb in the `test_data` folder.
