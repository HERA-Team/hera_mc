#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

import os
from setuptools import setup

from hera_mc import version


data = [version.git_origin, version.git_hash, version.git_description, version.git_branch]
with open(os.path.join('hera_mc', 'GIT_INFO'), 'w') as outfile:
    json.dump(data, outfile)

with io.open('README.md', 'r', encoding='utf-8') as readme_file:
    readme = readme_file.read()

setup_args = {
    'name': "hera_mc",
    'description': "hera_mc: HERA monitor and control",
    'long_description': readme,
    'url': "https://github.com/HERA-Team/hera_mc",
    'license': "BSD",
    'author': "HERA Team",
    'author_email': "hera-sw@lists.berkeley.edu",
    'version': version.version,
    'packages': ['hera_mc', 'hera_mc.tests'],
    'scripts': glob.glob('scripts/*'),
    'include_package_data': True,
    'requires': ["six", "numpy", "astropy", "sqlalchemy", "psycopg2", "alembic", "dateutil",
                 "tabulate", "pandas", "psutil", "pyproj"],
    'classifiers': ["Development Status :: 4 - Beta",
                    "Environment :: Console",
                    "Intended Audience :: Science/Research",
                    "License :: OSI Approved :: MIT License",
                    "Operating System :: OS Independent",
                    "Programming Language :: Python",
                    "Topic :: Scientific/Engineering"]
}

if __name__ == '__main__':
    setup(**setup_args)
