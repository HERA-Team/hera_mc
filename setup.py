#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2018 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Module setup."""

from setuptools import setup

# The only reason we currently need a setup.py is because we use a special
# branch scheme. See https://setuptools-scm.readthedocs.io/en/stable/customizing/


# define the branch scheme. Have to do it here so we don't have to modify the path
def branch_scheme(version):
    """
    Local version scheme that adds the branch name for absolute reproducibility.

    If and when this is added to setuptools_scm this function can be removed.
    """
    if version.exact or version.node is None:
        return version.format_choice("", "+d{time:{time_format}}", time_format="%Y%m%d")
    else:
        if version.branch == "main":
            return version.format_choice("+{node}", "+{node}.dirty")
        else:
            return version.format_choice("+{node}.{branch}", "+{node}.{branch}.dirty")


setup(use_scm_version={"local_scheme": branch_scheme})
