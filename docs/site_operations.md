Site operations
===============

## Updating the site after schema or code changes

**All of these steps must be followed for all schema changes**. A subset of them may be
required for other code changes.

- Pull and reinstall in **all** of the following machines & environments
(this is a critical step!) Use `pip install --no-deps .` to ensure enviroment stability:

  - qmaster machine
    - `HERA` conda environment
    - `RTP` conda environment
  - hera-corr-head machine (note: username is `hera`, non-standard pw)
    - `hera` conda environment
  - pot6 machine
    - `HERA` conda environment
  Note: other machines share the home drive of qmaster, so no need to install on those.

- Update the database schema with `alembic upgrade head`. This can be done anytime after
the `HERA` conda environment is updated on qmaster. After this step, the unit tests
should be run in that environment to ensure everything works as expected

- Restart the following daemons across the hera correletor computer cluster.
This is generally done with `systemctl restart <daemon_name>.service`. Some
machines use upstart instead of systemd, as marked below. In those cases, use
`sudo initctl restart <daemon_name>`. If on any of the upstart machines you get an error
with "Unknown instance", try re-running but with `start` instead of `restart` in case
the service wasn't running for some reason.

  - qmaster machine (note: to avoid having to type the password repeatedly you can run
  `sudo su root` before restarting all of these)
    - `hera-corr-status` daemon
    - `hera-node-status` daemon
    - `hera-server-status` daemon
    - `mc-listen-to-corr-logger` daemon
    - `mc-monitor-daemons` daemon
  - pot1 machine (upstart)
    - `hera-server-status` daemon
  - pot6 machine (requires `sudo` before command. Note: uses systemd not upstart like other pots)
    - `hera-server-status` daemon
  - pot7 machine (upstart)
    - `hera-server-status` daemon
  - pot8 machine (upstart)
    - `hera-server-status` daemon
  - pot9 machine (upstart)
    - `hera-server-status` daemon
  - still[1-4] machines (upstart)
    - `hera-server-status` daemon
  - gpu[1-8] machines (upstart)
    - `hera-server-status` daemon
  - bigmem[1-2] machines (upstart)
    - `hera-server-status` daemon

- Update heranow M&C installation.

    Heranow also uses M&C to ingest data for its own databases.
    Rebuilding the container for the website is required on any schema change.
    Please ping the hera_dashboards channel whenever a schema change occurs.

# Running psql on qmaster

This runs under the HERA conda environment on qmaster.

To check environments: `conda info --envs`

To change environments:  `source activate HERA`

To run psql:  `psql -U hera -h qmaster hera_mc`

# Running psql on NRAO

This runs under the HERA conda environment on herapost-master

To run psql: `psql -h herastore01 -U heramgr hera_mc`

# Restoring a database backup

We are now regularly backing up the database to the Librarian and copying it to NRAO.
The database backup files can be found by searching for them on the librarian using
`obsid-is-null`. The files are named like `maint.YYYYMMDD.karoo.mandc.dbbackup.pgdump`.

Once you've downloaded the files, you can create the database (using postgres) like this:

`pg_restore -cCOx  -d hera_mc  maint.20180213.karoo.mandc.dbbackup.pgdump`
