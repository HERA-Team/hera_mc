HERA M&C Database setup
=======================

After installing the package and any desired dependencies
(see the [Installation Instructions](./README.md#Installation)), follow the steps below
to setup the database configuration and load the configuration management data.

The online databases (at site and NRAO) uses `PostgreSQL`, however users who just need
the configuration management information locally may wish to use `SQLITE` instead as it
is easier than installing `PostgreSQL` (SQLITE is pre-installed on Macs). Developers of
hera_mc should install `PostgreSQL` to enable testing against the same database
implementation that we run on site.

Use of PostgreSQL vs SQLITE is determined by the `"default_db_name"` set below in the
database configuration file described below.

# Configuration management data

First get the configuration management data by cloning the repository containing it:

``git clone https://github.com/HERA-Team/hera_cm_db_updates``

# Database configuration file

A configuration file, located at `~/.hera_mc/mc_config.json`, is needed to tell M&C how
to talk to the database.

We have a script you can call which will make one as a starting point, which will be
similar to the example shown below. To run that script, navigate to the the
hera_cm_db_updates directory on your machine and type `mc_setup_home.py`.

Except for `<<<path-to-repo>>>` (see below), it should look like this:

```
{
  "default_db_name": "hera_mc",
  "databases": {
    "hera_mc": {
      "url": "postgresql://hera@localhost/hera_mc",
      "mode": "production"
    },
    "testing": {
      "url": "postgresql://hera@localhost/hera_mc_test",
      "mode": "testing"
    },
    "hera_mc_sqlite": {
      "url": "sqlite:///<<<Path-to-repo>>>/hera_mc.db",
      "mode": "production"
    }
  }
}
```

Make sure to change the `<<<Path-to-repo>>>` to be the full path to where the
`hera_cm_db_updates` repo is located. It will likely be something like
`/Users/username/Documents/hera/hera_cm_db_updates` (i.e. in the json file, there will
be a total of 4 `/` after `sqlite:`).  Note that regardless of whether you are using
PostgreSQL or SQLITE, you should include the `"hera_mc_sqlite"` entry for CM updates.

If using the SQLITE version make the second line in `mc_config.json`:
```
"default_db_name": "hera_mc_sqlite",
```

Note that for backward compatibility (and if you are using PostgreSQL) then instead of
the `"hera_mc_sqlite"` entry under `"databases"`,
you may instead include a separate entry:
```
{
  "default_db_name": "hera_mc",
  "cm_csv_path": <<<path-to-repo>>>,
  "databases": {
    ........
  }
}
```
The order is to check for `hera_cm_sqlite` first, then the `cm_csv_path` if it is not
present.

If you are running PostgreSQL, this assumes that your database username is
`hera`, there is no password associated with that user, and that you have two
separate databases named `hera_mc` and `hera_mc_test` for "production"
deployment and testing. You must have a database named "testing", in "testing"
mode, for the M&C test suite to work.

**If using SQLITE, you don't need to install PostgreSQL and may stop here.**

# Install PostgreSQL

We run PostgreSQL in production and, while SQLAlchemy abstracts between
different database backends as best it can, it is very desirable that you run
PostgreSQL in your test environment as well.

Installing postgresql has three primary steps:  (1) install postgreSQL itself, (2) install an interface to it, and (3) setup
project databases.  Below are directions for the recommended method to install on macosx.

1. postgres:
Follow directions on https://www.postgresql.org/download/macosx/.  Just install postgres and command line tools (i.e. not pgadmin)

2. interface:
The recommended program and simple directions are found here:  https://postgresapp.com/.
(Note that step 3 below may differ if you install a different interface than used here.)

3. databases:
The app will initialize three databases `postgres`, `template1`, and `<username>`, where username
is your username on your system. Use the
command `psql` in the terminal to get a psql prompt. From there create the hera user:

`<username>=# CREATE ROLE hera;`

Next create the two databases hera_mc will use:

```
<username>=# CREATE DATABASE hera_mc;
<username>=# CREATE DATABASE hera_mc_test;
```

Back in the GUI, you should see that your two new databases have appeared.
To get out of the psql prompt, use `Ctrl-d` or the command `\q`.
Finally, run the alembic script to upgrade your databases to the current schema.
This is done from the shell, in the root hera_mc directory (where the `alembic.ini` file lives).

`$ alembic upgrade head`

Populate the configuration management tables by running the `cm_init.py` script  This is the same command you will use to
update your local CM database over time (after pulling `hera_cm_db_updates`).

If there is already an instance of the postgres server running, you may need to kill it:  `sudo pkill -u postgres`.
This reset is often needed after a computer restart.  If you can't access the database and it was working, try this then
restart the server with the PostgreSQL app.


## Installing on Mac OS X with homebrew (not particularly recommended)

Based on our experience getting Dave up and running (in the early days...)

```
$ brew tap homebrew/services
==> Tapping Homebrew/services
Cloning into '/usr/local/Library/Taps/homebrew/homebrew-services'...
remote: Counting objects: 10, done.
remote: Compressing objects: 100% (7/7), done.
remote: Total 10 (delta 0), reused 6 (delta 0), pack-reused 0
Unpacking objects: 100% (10/10), done.
Checking connectivity... done.
Tapped 0 formulae (36 files, 164K)
$ brew services start postgresql
==> Successfully started `postgresql` (label: homebrew.mxcl.postgresql)
$ createuser hera
$ createdb -Ohera -Eutf8 hera_mc
$ createdb -Ohera -Eutf8 hera_mc_test
$ psql -U hera hera_mc
```

If you get "socket not found" on createuser your install did not work. Possible solution:

```
$ cd /usr/local/var/postgres/
$ chmod 700 . # make sure the permissions are correct
$ ls -lad . # double check that you (not root) are owner of /usr/local/var/postgres/
$ sudo chown -R <yourusername>:admin /usr/local/var/postgres/ # fix if necessary
$ rm *  # get rid of broken files
$ initdb -D .  # remake the database files
```

If you get the following error:
psql: could not connect to server: No such file or directory
  Is the server running locally and accepting
  connections on Unix domain socket "/tmp/.s.PGSQL.5432"?

you can try the following:
    rm /usr/local/var/postgres/postmaster.pid
then try restarting
    brew services restart postgresql

## Installing on Mac OS X with macports (not particularly recommended)

The following commands will install `postgresql` and initialize the databases. Note that some of
these commands may initially fail. If this is the case, then try executing the commands from the
`/opt/local/lib/postgresql96/bin/` directory.

```
$ sudo port install postgresql96-server
$ sudo mkdir -p /opt/local/var/db/postgresql96/defaultdb
$ sudo chown postgres:postgres /opt/local/var/db/postgresql96/defaultdb
$ sudo su postgres -c "/opt/local/lib/postgresql96/bin/initdb -D /opt/local/var/db/postgresql96/defaultdb"
```

At this point, you can run the same commands as before, but because the `postgres` user owns the database
directory, you must `su` to ensure the commands are successfully executed:

```
$ sudo su postgres -c "createdb -Ohera -Eutf8 hera_mc"
```
etc.
