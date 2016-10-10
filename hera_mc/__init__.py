# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

from __future__ import absolute_import, division, print_function

# Before we can do anything else, we need to initialize some core, shared
# variables.

from sqlalchemy.ext.declarative import declarative_base
MCDeclarativeBase = declarative_base()

import logging
logger = logging.getLogger(__name__)

# Now we can pull in the rest of our definitions.

def NotNull (kind, **kwargs):
    from sqlalchemy import Column
    return Column (kind, nullable=False, **kwargs)

from .version import __version__
from . import host_status
from . import mc
