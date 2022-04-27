hera_mc
=======

![](https://github.com/HERA-Team/hera_mc/workflows/Run%20Tests/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/HERA-Team/hera_mc/branch/master/graph/badge.svg)](https://codecov.io/gh/HERA-Team/hera_mc)

This is the main repository for HERA's monitor and control subsystems.

The HERA M&C system contains two primary types of tables and data:

- **Configuration Management**: This is the information about how all the hardware in
the telescope is connected together. This is a fairly small dataset and is only updated
when people change things. This data can be useful for users to have locally to be
able to identify how things are connected together. The actual data is stored in a
separate repository, `hera_cm_db_updates`. If you only need configuration management
data, you can do a relatively light-weight install of `hera_mc` and import the data
from that repo using SQLITE (which comes installed on many operating systems including
Macs).
- **Real-time monitoring**: This is the information about how the telescope is
operating. It includes information about commanded and actual settings of the various
systems as well as telemetry like temperatures. This is fairly large data and is
available onsite or at NRAO (based on a copy of the database that is refreshed weekly)
in an online PostgreSQL server. Much of this data can also be viewed in various
dashboards (including via grafana) linked from https://heranow.reionization.org.

# Documentation

A detailed description of the monitor and control system and the database schema can be
found in our [description document](docs/mc_definition.pdf).

# Installation

Simple installation via pip is available for users, developers should follow
the directions under [Developer Installation](#developer-installation) below.

For simple installation, the latest stable version is available via pip
(```pip install hera_mc```).

There are some optional dependencies that are required for specific functionality,
which will not be installed automatically by pip.
See [Dependencies](#dependencies) for details on installing optional dependencies.

If you want to use the configuration management information and connect to either an
SQLITE or PostgreSQL database, follow the detailed installation
instructions in [database_setup.md](./database_setup.md).


## Dependencies
The required dependencies are:
- alembic
- astropy
- numpy
- psycopg2
- pyyaml
- redis-py
- setuptools_scm
- sqlalchemy

the optional dependencies are:
- cartopy
- h5py
- pandas
- psutil
- python-dateutil
- pyuvdata
- tabulate
- tornado

We suggest using conda to install all the dependencies.

If you do not want to use conda, the packages are also available on PyPI. You can
install the optional dependencies via pip by specifying an option
when you install hera_mc, as in ```pip install hera_mc[sqlite]```
which will install all the required packages for using the lightweight configuration
management tools. The options that can be passed in this way are:
[`sqlite`, `all`, `dev`]. The `all` option will install all optional
dependencies, `dev` adds packages that may be useful for developers.

## Developer Installation

Clone the repository using
```git clone https://github.com/HERA-Team/hera_mc```

Navigate into the hera_mc directory and run `pip install .`
(note that `python setup.py install` does not work).
Note that this will attempt to automatically install any missing dependencies.
If you use conda or another package manager you might prefer to first install
the dependencies as described in [Dependencies](#dependencies).

To install without dependencies, run `pip install --no-deps .`

If you want to do development on hera_mc, in addition to the other dependencies
you will need the following packages:

* pytest
* pytest-cov
* coverage
* pre-commit

One way to ensure you have all the needed packages is to use the included
`environment.yaml` file to create a new environment that will contain all the optional
dependencies along with dependencies required development
(```conda env create -f environment.yaml```). Alternatively, you can specify `dev` when
installing hera_mc (as in `pip install hera_mc[dev]`) to install the packages needed
for development.

To use pre-commit to prevent committing code that does not follow our style, you'll
need to run `pre-commit install` in the top level `hera_mc` directory.

For more instructions for developers, especially related to working with the database
and schema changes, see the [Developer Instructions](./docs/developer.md).

# Tests

Uses the `pytest` package to execute test suite. From the source hera_mc directory run
``pytest``.
