HERA M&C Installation
=====================

Installation of the Python code is just done with a standard

```
python setup.py install
```


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

Database setup
--------------

Install PostgreSQL:
We run PostgreSQL in production and, while SQLAlchemy abstracts between
different database backends as best it can, it is very desirable that you run
PostgreSQL in your test environment as well. Use Google to learn how to do
this, or follow the OS-X-specific notes below.

_____________________________________
Configure hera_mc to talk to the db:

*OPTION 1:  Manually setup config file*
After setting up the database (see below), you need to fill in the configuration file
`~/.hera_mc/mc_config.json`, which tells the M&C system how to talk to the
database. An example file is:

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

Note that there is now an sqlite option.  To use it on your machine make the
second line in mc_config.json:
```
"default_db_name": "hera_mc_sqlite",
```

*OPTION 2:  Use the script*
After you get the repos:
 1 - hera_mc (and then python setup.py install it),
 2 - hera_cm_db_updates (no additional install)
go to the parent directory of hera_cm_db_updates and run the script
`mc_setup_home.py`

It defaults to the sqlite option

_____________________________________
Create the database schema by running `alembic upgrade head`
If desired, populate the configuration management tables by running the `cm_init.py` script.

Note the other line:  "cm_csv_path":.../hera_cm_db_updates, which is the full path to where you
have installed the local configuration management csv files, which are contained in the repo
hera_cm_db_updates.

To update your local database, (after you pull hera_cm_db_updates and add line to mc_config.json),
type `cm_init.py`

### Basic OS X PostgreSQL installation

NOTE:  If you are only running sqlite, you don't need to install PostgresSQL to use the cm stuff.

There are many options for installing postgres, several of which are described and
linked on this page: https://www.postgresql.org/download/macosx/. For the
instructions below, we are following the installation of the app version, found
here: https://postgresapp.com/. Follow steps 1 and 2 on that page, and optionally step 3.

The app will initialize three databases `postgres`, `template1`, and `<username>`, where username
is your username on your system. You can double click any of these dbs, or use the
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

If desired, populate the configuration management tables by running the `cm_init.py` script.

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
