# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Test that default database matches code schema.
"""
from sqlalchemy.orm import sessionmaker
from hera_mc import mc, MCDeclarativeBase
from hera_mc.db_check import is_sane_database


def test_default_db_schema():

    default_db = mc.connect_to_mc_db(None)
    engine = default_db.engine
    conn = engine.connect()
    trans = conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()

    assert is_sane_database(MCDeclarativeBase, session) is True
