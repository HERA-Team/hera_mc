#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Module setup."""

import glob
import io
import sys

from setuptools import setup

# add hera_mc to our path in order to use the branch_scheme function
sys.path.append("hera_mc")
from branch_scheme import branch_scheme  # noqa

with io.open("README.md", "r", encoding="utf-8") as readme_file:
    readme = readme_file.read()

setup_args = {
    "name": "hera_mc",
    "description": "hera_mc: HERA monitor and control",
    "long_description": readme,
    "long_description_content_type": "text/markdown",
    "url": "https://github.com/HERA-Team/hera_mc",
    "license": "BSD",
    "author": "HERA Team",
    "author_email": "hera-sw@lists.berkeley.edu",
    "use_scm_version": {"local_scheme": branch_scheme},
    "packages": ["hera_mc", "hera_mc.tests"],
    "scripts": glob.glob("scripts/*"),
    "include_package_data": True,
    "install_requires": [
        "alembic>=1.8",
        "astropy>=5.0.4",
        "cartopy>=0.20",
        "numpy>=1.19",
        "psycopg>=3.2.2",
        "pyuvdata>=2.2.9",
        "pyyaml>=5.1",
        "redis>=4.3.4",  # Note that this gets redis-py, which is named "redis" on pypi
        "setuptools_scm!=7.0.0,!=7.0.1,!=7.0.2",
        "sqlalchemy>=1.4",
    ],
    "extras_require": {
        "sqlite": ["tabulate"],
        "all": [
            "h5py>=3.1",
            "katportalclient",
            "matplotlib>=3.6",
            "pandas>=1.4",
            "psutil>=5.9",
            "python-dateutil>=2.8.2",
            "tabulate>=0.8.10",
            "tornado>=6.2",
        ],
        "dev": [
            "h5py>=3.1",
            "pandas>=1.4",
            "psutil>=5.9",
            "python-dateutil>=2.8.2",
            "tabulate>=0.8.10",
            "tornado>=6.2",
            "pytest",
            "pre-commit",
        ],
    },
    "tests_require": ["pyyaml>=5.1", "pytest"],
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering",
    ],
}

if __name__ == "__main__":
    setup(**setup_args)
