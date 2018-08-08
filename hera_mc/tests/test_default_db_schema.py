# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Test that default database matches code schema.
"""
from __future__ import absolute_import, division, print_function

from sqlalchemy.orm import sessionmaker

from .. import mc, MCDeclarativeBase
from ..db_check import is_valid_database


def test_default_db_schema():
    # this test will fail if the default database schema does not match the code schema

    default_db = mc.connect_to_mc_db(None)
    engine = default_db.engine
    conn = engine.connect()
    trans = conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()

    assert is_valid_database(MCDeclarativeBase, session) is True
