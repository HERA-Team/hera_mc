#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

import os
from setuptools import setup, find_packages
PACKAGES = find_packages()

# Get version and release info, which is all stored in shablona/version.py
ver_file = os.path.join('hera_mc', 'version.py')
with open(ver_file) as f:
    exec(f.read())


setup_args = dict(name=NAME,
                  maintainer=MAINTAINER,
                  maintainer_email=MAINTAINER_EMAIL,
                  description=DESCRIPTION,
                  long_description=LONG_DESCRIPTION,
                  url=URL,
                  download_url=DOWNLOAD_URL,
                  license=LICENSE,
                  classifiers=CLASSIFIERS,
                  author=AUTHOR,
                  author_email=AUTHOR_EMAIL,
                  platforms=PLATFORMS,
                  version=VERSION,
                  packages=PACKAGES,
                  package_data=PACKAGE_DATA,
                  scripts=SCRIPTS,
                  requires=REQUIRES)


if __name__ == '__main__':
    setup(**setup_args)
