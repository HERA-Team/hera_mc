# -*- mode: python; coding: utf-8 -*-
# Copyright 2019 the HERA Collaboration
# Licensed under the 2-clause BSD license.
import json
from collections import namedtuple

import pytest
import sqlalchemy
from sqlalchemy import Column, ForeignKey, Integer, String, text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, declared_attr, relationship, sessionmaker

from hera_mc import mc
from hera_mc.db_check import check_connection, is_valid_database

# Sometimes a connection is closed, which is handled and doesn't produce an error
# or even a warning under normal testing. But for the warnings test where we
# pass `-W error`, the warning causes an error so we filter it out here.
pytestmark = pytest.mark.filterwarnings("ignore:connection:ResourceWarning:psycopg")


def gen_test_model():
    Base = declarative_base()

    class ValidTestModel(Base):
        """A sample SQLAlchemy model to demostrate db conflicts."""

        __tablename__ = "validity_check_test"

        #: Running counter used in foreign key references
        id_ = Column(Integer, primary_key=True)

    return Base, ValidTestModel


def gen_relation_models():
    Base = declarative_base()

    class RelationTestModel(Base):
        __tablename__ = "validity_check_test_2"
        id_ = Column(Integer, primary_key=True)

    class RelationTestModel2(Base):
        __tablename__ = "validity_check_test_3"
        id_ = Column(Integer, primary_key=True)

        test_relationship_id = Column(ForeignKey("validity_check_test_2.id_"))
        test_relationship = relationship(
            RelationTestModel, primaryjoin=test_relationship_id == RelationTestModel.id_
        )

    return Base, RelationTestModel, RelationTestModel2


def gen_declarative():
    Base = declarative_base()

    class DeclarativeTestModel(Base):
        __tablename__ = "validity_check_test_4"
        id_ = Column(Integer, primary_key=True)

        @declared_attr
        def _password(self):
            return Column("password", String(256), nullable=False)

        @hybrid_property
        def password(self):
            return self._password

    return Base, DeclarativeTestModel


def test_argparser():
    ap = mc.get_mc_argument_parser()
    assert ap.description is None


def test_validity_pass():
    """
    See database validity check completes when tables and columns are created.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Base, ValidTestModel = gen_test_model()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        Base.metadata.drop_all(engine, tables=[ValidTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    base_is_none = is_valid_database(None, session)
    assert base_is_none

    Base.metadata.create_all(engine, tables=[ValidTestModel.__table__])

    try:
        assert is_valid_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)
        session.close()
        conn.close()


def test_validity_table_missing():
    """See check fails when there is a missing table"""
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Base, ValidTestModel = gen_test_model()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        Base.metadata.drop_all(engine, tables=[ValidTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    assert is_valid_database(Base, session) is False
    session.close()
    conn.close()


def test_validity_column_missing():
    """See check fails when there is a missing table"""
    engine = mc.connect_to_mc_testing_db().engine
    with engine.begin() as conn:
        Session = sessionmaker(bind=engine)
        session = Session()
        Base, ValidTestModel = gen_test_model()
        try:
            Base.metadata.drop_all(engine, tables=[ValidTestModel.__table__])
        except sqlalchemy.exc.NoSuchTableError:
            pass
        Base.metadata.create_all(engine, tables=[ValidTestModel.__table__])
        session.close()

        # Delete one of the columns
        conn.execute(text("ALTER TABLE validity_check_test DROP COLUMN id_"))

    # use a new context manager to make sure there are no open transactions
    # without this it hangs
    with engine.begin() as conn:
        Session = sessionmaker(bind=engine)
        session = Session()
        assert is_valid_database(Base, session) is False
        session.close()


def test_validity_pass_relationship():
    """
    See database validity check understands about relationships and don't
    deem them as missing column.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()

    Base, RelationTestModel, RelationTestModel2 = gen_relation_models()
    try:
        Base.metadata.drop_all(
            engine, tables=[RelationTestModel.__table__, RelationTestModel2.__table__]
        )
    except sqlalchemy.exc.NoSuchTableError:
        pass

    Base.metadata.create_all(
        engine, tables=[RelationTestModel.__table__, RelationTestModel2.__table__]
    )

    try:
        assert is_valid_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)
        session.close()
        conn.close()


def test_validity_pass_declarative():
    """
    See database validity check understands about relationships and don't deem
    them as missing column.
    """
    engine = mc.connect_to_mc_testing_db().engine
    conn = engine.connect()
    conn.begin()

    Session = sessionmaker(bind=engine)
    session = Session()

    Base, DeclarativeTestModel = gen_declarative()
    try:
        Base.metadata.drop_all(engine, tables=[DeclarativeTestModel.__table__])
    except sqlalchemy.exc.NoSuchTableError:
        pass

    Base.metadata.create_all(engine, tables=[DeclarativeTestModel.__table__])

    try:
        assert is_valid_database(Base, session) is True
    finally:
        Base.metadata.drop_all(engine)
        session.close()
        conn.close()


def test_check_connection(tmpdir):
    """Check that a missing database raises appropriate exception."""
    # Create database connection with fake url
    db = mc.DeclarativeDB("postgresql+psycopg://hera@localhost/foo")
    with db.sessionmaker() as s:
        assert check_connection(s) is False

    test_config = {
        "default_db_name": "hera_mc",
        "databases": {
            "hera_mc": {
                "url": "postgresql+psycopg://hera:hera@localhost/hera_mc",
                "mode": "testing",
            },
            "testing": {
                "url": "postgresql+psycopg://hera:hera@localhost/hera_mc_test",
                "mode": "testing",
            },
            "foo": {
                "url": "postgresql+psycopg://hera:hera@localhost/foo",
                "mode": "testing",
            },
        },
    }

    test_config_file = tmpdir + "test_config.json"
    with open(test_config_file, "w") as outfile:
        json.dump(test_config, outfile, indent=4)

    Args = namedtuple("Args", "mc_config_path mc_db_name")
    this_args = Args(test_config_file, "foo")

    with pytest.raises(
        RuntimeError, match="Could not establish valid connection to database."
    ):
        mc.connect_to_mc_db(this_args)
