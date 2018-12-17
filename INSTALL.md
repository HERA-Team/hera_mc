HERA M&C Installation
=====================

HERA M&C requires `hera_mc` and postgreSQL.  Note:  if you are only using it to view configuration management, you may instead use SQLITE.

Installation steps are:

[1.] Install hera_mc
[2.] Setup database configuration file
[3.] Install postgreSQL (if not using SQLITE)


[1.] Install hera_mc
---

Clone the following two repositories:
* https://github.com/HERA-Team/hera_mc
* https://github.com/HERA-Team/hera_cm_db_updates

Then install by:
1. within the hera_mc directory type `python setup.py install` (or `pip install .`)
2. in the hera_cm_db_updates directory type `mc_setup_home.py`

To run hera_mc, you will likely need to install some additional python modules (see Python Prerequisites below.)

Python Prerequisites
--------------
- sqlalchemy
- psycopg2
- alembic
- dateutil
- numpy
- astropy
- tabulate
- pandas
- psutil
- pyproj


[2.] Set up database configuration file
---
A configuration file `~/.hera_mc/mc_config.json` is needed to tell M&C how to talk to the database.  It should look like the example below,
making sure to change the `<<<Path-to-repo>>>` to be the full path to where hera_cm_db_updates is located.

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
      "url": "sqlite:////<<<Path-to-repo>>>/hera_cm_db_updates/hera_mc.db",
      "mode": "production"
    }
  },
  "cm_csv_path": "<<<Path-to-repo>>>/hera_cm_db_updates"
}
```

This example assumes that you’re running PostgreSQL, your database username is
`hera`, there is no password associated with that user, and that you have two
separate databases named `hera_mc` and `hera_mc_test` for "production"
deployment and testing. You must have a database named "testing", in "testing"
mode, for the M&C test suite to work.

If using the SQLITE version for viewing CM make the second line in mc_config.json:
```
"default_db_name": "hera_mc_sqlite",
```
If using SQLITE, you don't need to install PostgreSQL

[3.] Install PostgreSQL
---
We run PostgreSQL in production and, while SQLAlchemy abstracts between
different database backends as best it can, it is very desirable that you run
PostgreSQL in your test environment as well. Use Google to learn how to do
this, or follow the OS-X-specific notes below (recommended).

Installing postgresql has three primary steps:  (1) install postgres itself, (2) install an interface to it, and (3) setup
project databases.  Below are directions for the recommended method to install on macosx.

1. postgres:
Follow directions on https://www.postgresql.org/download/macosx/.  Just install postgres and command line tools (ie. not pgadmin)

2. interface:
The recommended program and simple directions are found here:  https://postgresapp.com/.

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
This is done from the shell, in the root hera_mc directory (where the .ini file lives).

`$ alembic upgrade head`

You will likely have to install packages as it fails, so keep doing `conda install <pkg>` until it completes successfully.

If desired, populate the configuration management tables by running the `cm_init.py` script.

If there is already an instance of the postgres server running, you may need to kill it:  `sudo pkill -u postgres`


### Installing on Mac OS X with homebrew (not particularly recommended)

Based on our experience getting Dave up and running.

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

### Installing on Mac OS X with macports (not particularly recommended)

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
