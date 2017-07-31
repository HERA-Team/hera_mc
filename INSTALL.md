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


Configure hera_mc to talk to the db:
After setting up the database, you need to fill in the configuration file
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
    }
  }
}
```

This example assumes that you’re running PostgreSQL, your database username is
`hera`, there is no password associated with that user, and that you have two
separate databases named `hera_mc` and `hera_mc_test` for "production"
deployment and testing. You must have a database named "testing", in "testing"
mode, for the M&C test suite to work.

Create the database schema by running `alembic upgrade head`
If desired, populate the configuration management tables by running the `cm_init.py` script.

### Basic OS X PostgreSQL installation

Follow the directions under `Interactive installer by EnterpriseDB` here: https://www.postgresql.org/download/macosx/

This will install the PostgreSQL app on your machine. Starting the app will start the postgres database and give an option to open a psql command line. Then you can create the hera_mc and hera_mc_test databases.

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

you can try the following:  rm /usr/local/var/postgres/postmaster.pid

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
