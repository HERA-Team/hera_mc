Developer instructions
======================

# Schema changes

To add a new table or make another schema change in the M&C database:

First, ensure that the database is configured correctly by running
`alembic upgrade head`. If this fails, refer to the directions in
[Database setup](../database_setup.md).

Be sure to do all your work on a branch off of main.

1. If appropriate, create a new module under `hera_mc`, basing on e.g.
`subsystem_error.py` or `observation.py`.
2. If you created a new module, add `from . import <my_new_module>` line in
`__init__.py`.
3. If appropriate, add methods to interact with new tables. This is most commonly done
in `mc_session.py`, and there are many examples there to refer to.
4. Add testing or update code to cover any new code. -- Be sure to `pip install .`
before the next step (unless you've done a developer install: `pip install -e .`).
5. Run `alembic revision --autogenerate -m 'version description'` to create a
new alembic revision file that will reflect the changes to the database schema
you just introduced. Inspect the resulting file carefully -- alembic's
autogeneration is very clever but it's certainly not perfect. It tends to make
more mistakes with table or column alterations than with table creations. **Also
be sure to remove any dropped tables in the upgrade section (and corresponding
table creation commands in the downgrade portion) -- we have some old tables
that we no longer use but don't want to drop on site.**
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
changes integrated into main.
11. Testing onsite (required for PRs): First clear it with the observing team. Then
checkout your branch onsite and run `alembic upgrade head`. Install the new branch with
`pip install --no-deps .`. Run the tests with `pytest`. Then put things back as they were
by first downgrading alembic with `alembic downgrade -1` (or whatever number of alembic
versions your branch differs from what was installed by). The downgrade **must be done**
while you are still on your branch so you have the alembic revision files. **Be careful
with alembic downgrades** -- if you downgrade too far you could drop tables or columns
with essential data in them. Then checkout the main branch and install it with
`pip install --no-deps .`. It's a good idea to re-run tests at this point to make sure
you didn't break anything.
11. Once the changes have been incorporated into main, you can log onto site,
pull the main branch and run `alembic upgrade head` to update the onsite
database to the new schema.
12. Follow **all** the steps detailed in [Site operations](./site_operations.md) under
"Updating the site after schema or code changes" to ensure that all the machines on
site are in a self-consistent state.

# Adding new features and testing
`hera_mc` uses redis during testing to check that values read from redis in the live
version can be correctly added to the databases and retrieved again. When adding new
features which require data being read from redis, or through any hera correlator code,
a new redis.rdb file must be created on `redishost` on site which contains an example
of the new data and added to the repository by overwriting the existing redis.rdb in
the `test_data` folder.

## Hosting a redis server for testing

Developers interested in running redis on their own development machines
have multiple options for hosting.
 - Using native platform redis-server programs. These can be installed from any package manager.
 - Docker can be used to run a redis server as well. But this requires mounting a volume
   on the docker container so the new dumps can be loaded into the server.

## Updating the redis dump

A redis backup can be initiated by calling `redis-cli bgsave` on the `hera-corr-head`
machine (reminder, `hera` is the user not `obs`, non-standard password).
The default dump location is `/var/lib/redis/dump.rdb`.
For safety, move this dump off of the production server and perform any remaining
manipulations in a controlled environment. If you have site access set up via an ssh
tunnel, you may first have to copy the file to another location on qmaster (which you
have an ssh alias to), then you can use rsync like this:
`rsync --rsh='ssh -p <port_number>' -vPaz <ssh_alias>:</path/to/file>/dump.rdb <path/on/local/machine>`

Next you need to load your new dump into a redis server.

When loading a dump into a redis server:
- stop the server from running.
- replace the `dump.rdb` for the running server with your new dump.
- restart the redis server.

With the growing size of redis, it is sometimes necessary to prune large keys to keep
the git repo reasonably sized.
If multiple FPGA bit files (`fpg:*` keys in redis) are present, it is recommended to
remove some or most of these first since they can be a few MB worth of data.

Additionally, some keys in redis are set to expire after a certain amount of time is
passed.

To remove the time to live (TTL) on all keys and to delete all but the latest fpg, the
following few lines in python can be used:

```python
import redis
import re
from astropy.time import Time

r = redis.Redis("redishost")

fpg_keys = []
fpg_times = []
for key in r.keys():
    r.persist(key)
    if "fpg" in key.decode("utf-8"):
        match = re.search(r'\d{4}-\d{2}-\d{2}', key.decode("utf-8"))
        if match is not None:
            fpg_keys.append(key)
            fpg_times.append(Time(match.group(0)))

fpg_key_keep = fpg_keys[fpg_times.index(max(fpg_times))]

for key in fpg_keys:
    if key != fpg_key_keep:
        r.delete(key)

r.save()
```

Once the save is complete, re-run hera_mc tests to ensure compatibility.
If all the tests pass and this dump is ready to be committed, copy this dump back to
overwrite `hera_mc/hera_mc/data/test_data/dump.rdb`.
Add and commit the file through git to finilize the update on your branch.


# Using alembic for the first time with an existing (non-empty) database
If you already have a database filled out with tables but have never run alembic before,
you have two choices to start using alembic:

Option 1) Drop all the tables (if you don't care about the data in the database this is
easiest, see the instructions below) and then run `alembic upgrade head`.

Option 2) identify which alembic version your database schema corresponds to and add a
new table to your database called `alembic_version` with one column called
'version_num'. Fill this table with one row with the alembic version number that
corresponds to your schema version to tell alembic where to start trying to upgrade
from. Then run `alembic upgrade head`.

# Deleting a database
This can be useful to do on your local machine if your database is in a weird state.
Never do this on site!!!
`dropdb hera_mc`

# Deleting all the tables in a database (in psql shell)
This can be useful to do on your local machine if your database is in a weird state.
Never do this on site!!!
```
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```
If you get an error like `no schema has been selected to create in...` it means that
you need to fix permissions like this:
```
grant usage on schema public to public;
grant create on schema public to public;
```
