# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""
Test that default database matches code schema.
"""
import pytest
from sqlalchemy.orm import sessionmaker

from .. import MCDeclarativeBase, mc
from ..db_check import is_valid_database

# Sometimes a connection is closed, which is handled and doesn't produce an error
# or even a warning under normal testing. But for the warnings test where we
# pass `-W error`, the warning causes an error so we filter it out here.
pytestmark = pytest.mark.filterwarnings("ignore:connection:ResourceWarning:psycopg")


def test_default_db_schema():
    # this test will fail if the default database schema does not match the code schema

    default_db = mc.connect_to_mc_db(None)
    engine = default_db.engine

    with engine.connect() as conn:
        with conn.begin():
            Session = sessionmaker(bind=engine)
            with Session() as session:
                assert is_valid_database(MCDeclarativeBase, session) is True
